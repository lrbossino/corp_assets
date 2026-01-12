"""
Batch Executor - Multi-Provider Support
Supports both OpenAI and Doubleword AI batch APIs
Uses OpenAI client library which is compatible with both
"""

import json
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class BatchSubtask:
    """Represents a subtask ready for batch execution"""
    custom_id: str
    subtask_id: str
    company_id: str
    objective: str
    tools_available: List[Dict[str, Any]]
    execution_instructions: str

    def to_batch_request(self, model: str = "gpt-4-1-mini") -> Dict[str, Any]:
        """Convert to batch request format compatible with both OpenAI and Doubleword"""
        return {
            "custom_id": self.custom_id,
            "params": {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": self.execution_instructions
                    }
                ],
                "tools": self.tools_available,
                "tool_choice": "auto",
                "temperature": 0.3,
                "max_tokens": 4000
            }
        }


class BatchExecutor:
    """
    Executes subtasks in parallel using batch APIs.
    Supports both OpenAI and Doubleword AI through OpenAI-compatible API.
    """

    PROVIDER_CONFIGS = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4-1-mini",
            "completion_window": "24h"
        },
        "doubleword": {
            "base_url": "https://api.doubleword.ai/v1",
            "default_model": "Qwen/Qwen3-VL-30B-A3B-Instruct-FP8",
            "completion_window": "24h"
        }
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "doubleword",
        output_dir: str = "./batch_results",
        poll_interval: int = 30,
        model: Optional[str] = None,
        completion_window: Optional[str] = None
    ):
        """
        Initialize the batch executor.

        Args:
            api_key: API key for the provider
            provider: "openai" or "doubleword"
            output_dir: Directory to store batch results
            poll_interval: Seconds between status polls
            model: Override default model for provider
            completion_window: "24h" or "1h" (Doubleword only)
        """
        if provider not in self.PROVIDER_CONFIGS:
            raise ValueError(f"Unknown provider: {provider}. Must be one of {list(self.PROVIDER_CONFIGS.keys())}")

        self.provider = provider
        self.config = self.PROVIDER_CONFIGS[provider]
        self.model = model or self.config["default_model"]
        self.completion_window = completion_window or self.config["completion_window"]

        # Initialize OpenAI client (works for both OpenAI and Doubleword)
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.config["base_url"]
        )

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.poll_interval = poll_interval
        self.batch_jobs = {}

        logger.info(f"Initialized BatchExecutor with provider={provider}, model={self.model}")

    def submit_batch(
        self,
        batch_subtasks: List[BatchSubtask],
        batch_name: str = None
    ) -> str:
        """
        Submit a batch of subtasks for execution.

        Args:
            batch_subtasks: List of BatchSubtask objects
            batch_name: Optional name for the batch

        Returns:
            Batch ID
        """
        if not batch_name:
            batch_name = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Submitting batch '{batch_name}' with {len(batch_subtasks)} subtasks to {self.provider}")

        # Convert to batch request format
        requests = [st.to_batch_request(self.model) for st in batch_subtasks]

        # Create JSONL content
        jsonl_content = "\n".join(json.dumps(req) for req in requests)

        # Save JSONL file
        jsonl_file = self.output_dir / f"{batch_name}.jsonl"
        with open(jsonl_file, "w") as f:
            f.write(jsonl_content)

        logger.info(f"Saved batch JSONL to {jsonl_file} ({len(jsonl_content)} bytes)")

        # Upload file
        logger.info("Uploading batch file...")
        with open(jsonl_file, "rb") as f:
            response = self.client.beta.files.upload(
                file=(jsonl_file.name, f, "application/jsonl"),
            )
        file_id = response.id
        logger.info(f"File uploaded with ID: {file_id}")

        # Create batch job
        logger.info(f"Creating batch job with completion_window={self.completion_window}...")
        batch = self.client.beta.batches.create(
            input_file_id=file_id,
            endpoint="/v1/chat/completions",
            completion_window=self.completion_window,
        )

        batch_id = batch.id
        logger.info(f"Batch submitted with ID: {batch_id}")

        # Track batch
        self.batch_jobs[batch_id] = {
            "batch_name": batch_name,
            "provider": self.provider,
            "model": self.model,
            "submission_time": datetime.now().isoformat(),
            "status": "submitted",
            "subtask_count": len(batch_subtasks),
            "file_id": file_id,
            "jsonl_file": str(jsonl_file),
            "result_file_id": None,
            "output_file": None
        }

        self._save_batch_tracking()
        return batch_id

    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get status of a batch"""
        batch = self.client.beta.batches.retrieve(batch_id)

        return {
            "batch_id": batch_id,
            "status": batch.status,
            "request_counts": {
                "total": batch.request_counts.total,
                "completed": batch.request_counts.completed,
                "failed": batch.request_counts.failed,
                "processing": batch.request_counts.processing
            },
            "output_file_id": batch.output_file_id,
            "error_file_id": batch.error_file_id,
            "created_at": batch.created_at,
            "completed_at": batch.completed_at
        }

    def wait_for_batch(
        self,
        batch_id: str,
        max_wait_hours: int = 24
    ) -> bool:
        """
        Poll a batch until completion.

        Args:
            batch_id: Batch ID to wait for
            max_wait_hours: Maximum hours to wait

        Returns:
            True if completed, False if timeout or failed
        """
        start_time = time.time()
        max_wait_seconds = max_wait_hours * 3600

        logger.info(f"Waiting for batch {batch_id} to complete (max {max_wait_hours}h)...")

        while True:
            status = self.get_batch_status(batch_id)
            logger.info(
                f"Batch {batch_id} status: {status['status']} "
                f"({status['request_counts']['completed']}/{status['request_counts']['total']} completed)"
            )

            if status["status"] == "completed":
                logger.info(f"Batch {batch_id} completed!")
                self.batch_jobs[batch_id]["status"] = "completed"
                self.batch_jobs[batch_id]["result_file_id"] = status["output_file_id"]
                self._save_batch_tracking()
                return True

            if status["status"] == "failed":
                logger.error(f"Batch {batch_id} failed!")
                self.batch_jobs[batch_id]["status"] = "failed"
                self._save_batch_tracking()
                return False

            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                logger.warning(f"Batch {batch_id} timeout after {max_wait_hours} hours")
                return False

            time.sleep(self.poll_interval)

    def retrieve_batch_results(self, batch_id: str) -> Dict[str, str]:
        """
        Retrieve results from a completed batch.

        Args:
            batch_id: Batch ID

        Returns:
            Dictionary mapping subtask_id to result text
        """
        batch_job = self.batch_jobs.get(batch_id)
        if not batch_job or not batch_job.get("result_file_id"):
            logger.error(f"No results available for batch {batch_id}")
            return {}

        logger.info(f"Retrieving results for batch {batch_id}")

        result_file_id = batch_job["result_file_id"]
        file_content = self.client.beta.files.content(result_file_id)

        # Parse JSONL results
        results = {}
        for line in file_content.text.strip().split("\n"):
            if not line:
                continue

            try:
                result = json.loads(line)
                custom_id = result.get("custom_id")
                message_content = result.get("result", {}).get("message", {}).get("content", "")

                if custom_id and message_content:
                    results[custom_id] = message_content

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse result line: {e}")

        logger.info(f"Retrieved {len(results)} results from batch {batch_id}")
        return results

    def save_batch_results(
        self,
        batch_id: str,
        results: Dict[str, str]
    ) -> str:
        """
        Save batch results to file.

        Args:
            batch_id: Batch ID
            results: Dictionary of results

        Returns:
            Path to saved file
        """
        output_file = self.output_dir / f"results_{batch_id}.jsonl"

        logger.info(f"Saving {len(results)} results to {output_file}")

        with open(output_file, "w") as f:
            for subtask_id, result_text in results.items():
                result_entry = {
                    "subtask_id": subtask_id,
                    "result": result_text,
                    "timestamp": datetime.now().isoformat()
                }
                f.write(json.dumps(result_entry) + "\n")

        self.batch_jobs[batch_id]["output_file"] = str(output_file)
        self._save_batch_tracking()

        return str(output_file)

    def get_all_batch_statuses(self) -> List[Dict[str, Any]]:
        """Get status of all tracked batches"""
        statuses = []
        for batch_id in self.batch_jobs.keys():
            try:
                status = self.get_batch_status(batch_id)
                statuses.append(status)
            except Exception as e:
                logger.error(f"Error retrieving status for batch {batch_id}: {e}")

        return statuses

    def _save_batch_tracking(self):
        """Save batch tracking information"""
        tracking_file = self.output_dir / "batch_tracking.json"
        with open(tracking_file, "w") as f:
            json.dump(self.batch_jobs, f, indent=2)

    def load_batch_tracking(self):
        """Load batch tracking information"""
        tracking_file = self.output_dir / "batch_tracking.json"
        if tracking_file.exists():
            with open(tracking_file, "r") as f:
                self.batch_jobs = json.load(f)
            logger.info(f"Loaded tracking for {len(self.batch_jobs)} batches")

    def submit_multiple_batches(
        self,
        all_batch_subtasks: List[List[BatchSubtask]],
        batch_names: Optional[List[str]] = None
    ) -> List[str]:
        """
        Submit multiple batches.

        Args:
            all_batch_subtasks: List of lists of subtasks
            batch_names: Optional names for batches

        Returns:
            List of batch IDs
        """
        batch_ids = []

        for idx, batch_subtasks in enumerate(all_batch_subtasks):
            batch_name = batch_names[idx] if batch_names and idx < len(batch_names) else None
            batch_id = self.submit_batch(batch_subtasks, batch_name)
            batch_ids.append(batch_id)

        return batch_ids

    def wait_for_multiple_batches(
        self,
        batch_ids: List[str],
        max_wait_hours: int = 24
    ) -> bool:
        """
        Wait for multiple batches to complete.

        Args:
            batch_ids: List of batch IDs
            max_wait_hours: Maximum hours to wait

        Returns:
            True if all completed, False if any failed
        """
        logger.info(f"Waiting for {len(batch_ids)} batches to complete...")

        all_completed = True
        for batch_id in batch_ids:
            success = self.wait_for_batch(batch_id, max_wait_hours)
            if not success:
                all_completed = False

        return all_completed

    def retrieve_multiple_batch_results(
        self,
        batch_ids: List[str]
    ) -> Dict[str, Dict[str, str]]:
        """
        Retrieve results from multiple batches.

        Args:
            batch_ids: List of batch IDs

        Returns:
            Dictionary mapping batch_id to results
        """
        all_results = {}

        for batch_id in batch_ids:
            results = self.retrieve_batch_results(batch_id)
            all_results[batch_id] = results
            self.save_batch_results(batch_id, results)

        return all_results

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider"""
        return {
            "provider": self.provider,
            "base_url": self.config["base_url"],
            "model": self.model,
            "completion_window": self.completion_window
        }
