"""
Research Application V3 - Rules-Based Architecture
Uses deterministic rules engine instead of real-time API
Supports both OpenAI and Doubleword batch APIs
"""

import json
import logging
import argparse
import os
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

from rules_engine import RulesEngine, ResearchSubtask
from batch_executor import BatchExecutor, BatchSubtask
from tool_executor import ToolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResearchApplicationV3:
    """
    V3 Research Application using rules-based orchestration and multi-provider batch execution.
    No real-time API calls; purely deterministic planning.
    """

    def __init__(
        self,
        output_dir: str = "./research_output_v3",
        api_key: Optional[str] = None,
        provider: str = "doubleword",
        model: Optional[str] = None,
        config_file: Optional[str] = None
    ):
        """
        Initialize the research application.

        Args:
            output_dir: Directory for all outputs
            api_key: API key for batch provider
            provider: "openai" or "doubleword"
            model: Override default model
            config_file: Optional rules configuration file
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.rules_engine = RulesEngine(config_file=config_file)
        self.batch_executor = BatchExecutor(
            api_key=api_key,
            provider=provider,
            output_dir=str(self.output_dir / "batches"),
            model=model
        )
        self.tool_executor = ToolExecutor()

        self.research_results: Dict[str, Any] = {}

        logger.info(f"Initialized ResearchApplicationV3 with provider={provider}")

    def load_companies_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load company list from JSON or Excel file.

        Args:
            file_path: Path to companies file (JSON or Excel)

        Returns:
            List of company dictionaries
        """
        file_path = Path(file_path)

        if file_path.suffix.lower() == ".json":
            with open(file_path, "r") as f:
                companies = json.load(f)
        elif file_path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
            companies = df.to_dict("records")
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

        logger.info(f"Loaded {len(companies)} companies from {file_path}")
        return companies

    def plan_research(self, companies: List[Dict[str, Any]]) -> Dict[str, List[ResearchSubtask]]:
        """
        Plan research for all companies using rules engine.
        No API calls; purely deterministic.

        Args:
            companies: List of companies to research

        Returns:
            Dictionary mapping company_id to list of subtasks
        """
        logger.info(f"Planning research for {len(companies)} companies using rules engine")

        all_subtasks, summary_stats = self.rules_engine.plan_batch_research(companies)

        # Organize by company
        by_company = {}
        for subtask in all_subtasks:
            if subtask.company_id not in by_company:
                by_company[subtask.company_id] = []
            by_company[subtask.company_id].append(subtask)

        logger.info(f"Planning complete: {summary_stats['total_subtasks']} subtasks in {summary_stats['planning_time_ms']}ms")
        logger.info(f"  Mandatory: {summary_stats['mandatory_subtasks']}")
        logger.info(f"  Optional: {summary_stats['optional_subtasks']}")
        logger.info(f"  High intensity: {summary_stats['by_capital_intensity']['High']} subtasks")
        logger.info(f"  Low intensity: {summary_stats['by_capital_intensity']['Low']} subtasks")

        return by_company

    def prepare_batch_subtasks(
        self,
        research_subtasks: Dict[str, List[ResearchSubtask]],
        tool_definitions: List[Dict[str, Any]]
    ) -> List[BatchSubtask]:
        """
        Convert research subtasks to batch-ready subtasks with execution prompts.

        Args:
            research_subtasks: Dictionary of company_id -> research subtasks
            tool_definitions: List of tool definitions

        Returns:
            List of batch-ready subtasks
        """
        logger.info("Converting research subtasks to batch-ready format")

        batch_subtasks = []

        for company_id, subtasks in research_subtasks.items():
            for subtask in subtasks:
                # Create execution prompt
                execution_prompt = self._create_execution_prompt(subtask, tool_definitions)

                # Create batch subtask
                batch_subtask = BatchSubtask(
                    custom_id=subtask.subtask_id,
                    subtask_id=subtask.subtask_id,
                    company_id=subtask.company_id,
                    objective=subtask.objective,
                    tools_available=tool_definitions,
                    execution_instructions=execution_prompt
                )

                batch_subtasks.append(batch_subtask)

        logger.info(f"Prepared {len(batch_subtasks)} batch subtasks")
        return batch_subtasks

    def _create_execution_prompt(
        self,
        subtask: ResearchSubtask,
        tool_definitions: List[Dict[str, Any]]
    ) -> str:
        """
        Create execution prompt for a subtask.
        Includes tool definitions and specific instructions.
        """
        from tool_definitions import format_tool_definitions_for_prompt

        prompt = f"""You are a research agent tasked with discovering corporate assets.

Company: {subtask.company_name}
Research Phase: {subtask.phase.value}
Objective: {subtask.objective}
Expected Output: {subtask.expected_output}

# Available Tools

{format_tool_definitions_for_prompt()}

# Instructions

1. Use the available tools to research and discover assets
2. For each tool call, use this format:
   <tool_call name="tool_name">{{"param1": "value1", "param2": "value2"}}</tool_call>

3. Execute multiple tool calls as needed to complete the objective
4. After gathering information, compile your findings into a structured list

# Output Format

After using tools to research, provide your findings as JSON in this format:
{{
  "phase": "{subtask.phase.value}",
  "objective": "{subtask.objective}",
  "discovered_assets": [
    {{
      "facility_name": "Name of facility",
      "address": "Street address",
      "city": "City",
      "country": "Country",
      "latitude": 0.0,
      "longitude": 0.0,
      "asset_type": "office|data_center|warehouse|manufacturing|retail|other",
      "source_url": "https://source.url",
      "source_type": "company_website|annual_report|sec_filing|news_article|job_posting|registry|other",
      "confidence_score": 0.95,
      "notes": "Any additional notes"
    }}
  ],
  "search_summary": "Summary of what was searched and found",
  "next_steps": "Recommendations for next research phase"
}}

# Research Guidelines

- Search thoroughly using the tools available
- Verify assets belong to {subtask.company_name}, not subsidiaries or competitors
- Prioritize official sources (company websites, SEC filings, annual reports)
- Include multi-language searches for the company's home country
- For each asset, provide the most specific location data available (coordinates > address > city)
- Assign confidence scores based on source reliability
- Continue searching until you've exhausted the available tools or found sufficient assets

Begin your research now."""

        return prompt

    def prepare_batches(
        self,
        batch_subtasks: List[BatchSubtask],
        batch_size: int = 100
    ) -> List[List[BatchSubtask]]:
        """
        Group subtasks into batches.

        Args:
            batch_subtasks: List of batch-ready subtasks
            batch_size: Number of subtasks per batch

        Returns:
            List of batch lists
        """
        logger.info(f"Grouping {len(batch_subtasks)} subtasks into batches (size: {batch_size})")

        batches = []
        for i in range(0, len(batch_subtasks), batch_size):
            batch = batch_subtasks[i:i + batch_size]
            batches.append(batch)

        logger.info(f"Created {len(batches)} batches")
        return batches

    def submit_research_batches(
        self,
        batches: List[List[BatchSubtask]]
    ) -> List[str]:
        """
        Submit batches for execution.

        Args:
            batches: List of batch lists

        Returns:
            List of batch IDs
        """
        logger.info(f"Submitting {len(batches)} batches for execution")

        batch_ids = self.batch_executor.submit_multiple_batches(batches)

        logger.info(f"Submitted {len(batch_ids)} batches")
        return batch_ids

    def wait_for_batches(
        self,
        batch_ids: List[str],
        max_wait_hours: int = 24
    ) -> bool:
        """
        Wait for all batches to complete.

        Args:
            batch_ids: List of batch IDs
            max_wait_hours: Maximum hours to wait

        Returns:
            True if all completed, False if any failed
        """
        logger.info(f"Waiting for {len(batch_ids)} batches to complete")

        success = self.batch_executor.wait_for_multiple_batches(batch_ids, max_wait_hours=max_wait_hours)

        return success

    def process_batch_results(self, batch_ids: List[str]) -> Dict[str, Any]:
        """
        Process results from completed batches.

        Args:
            batch_ids: List of batch IDs

        Returns:
            Aggregated results
        """
        logger.info(f"Processing results from {len(batch_ids)} batches")

        all_results = self.batch_executor.retrieve_multiple_batch_results(batch_ids)

        # Flatten results
        flat_results = {}
        for batch_id, results in all_results.items():
            flat_results.update(results)

        logger.info(f"Processed {len(flat_results)} subtask results")

        self.research_results = {
            "total_results": len(flat_results),
            "batch_ids": batch_ids,
            "results": flat_results,
            "completion_time": pd.Timestamp.now().isoformat()
        }

        return self.research_results

    def export_results(self) -> Dict[str, str]:
        """
        Export research results to files.

        Returns:
            Dictionary mapping output type to file path
        """
        logger.info("Exporting research results")

        output_files = {}

        # Export raw results
        results_file = self.output_dir / "raw_results.json"
        with open(results_file, "w") as f:
            json.dump(self.research_results, f, indent=2, default=str)
        output_files["raw_results"] = str(results_file)

        logger.info(f"Exported results to {self.output_dir}")
        return output_files

    def run_complete_research(
        self,
        companies_file: str,
        batch_size: int = 100,
        wait_for_completion: bool = True,
        max_wait_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Run complete research workflow.

        Args:
            companies_file: Path to companies file
            batch_size: Subtasks per batch
            wait_for_completion: Whether to wait for batches
            max_wait_hours: Maximum hours to wait

        Returns:
            Research results
        """
        logger.info("Starting V3 research workflow (rules-based, no real-time API)")

        # Step 1: Load companies
        companies = self.load_companies_from_file(companies_file)

        # Step 2: Validate companies
        invalid_companies = []
        for company in companies:
            is_valid, errors = self.rules_engine.validate_company_data(company)
            if not is_valid:
                logger.warning(f"Invalid company {company.get('org')}: {errors}")
                invalid_companies.append(company)

        if invalid_companies:
            companies = [c for c in companies if c not in invalid_companies]
            logger.info(f"Filtered out {len(invalid_companies)} invalid companies, {len(companies)} remaining")

        # Step 3: Plan research using rules engine (NO API CALLS)
        research_subtasks = self.plan_research(companies)

        # Step 4: Prepare batch subtasks
        from tool_definitions import TOOL_DEFINITIONS
        batch_subtasks = self.prepare_batch_subtasks(research_subtasks, TOOL_DEFINITIONS)

        # Step 5: Prepare batches
        batches = self.prepare_batches(batch_subtasks, batch_size)

        # Step 6: Submit batches
        batch_ids = self.submit_research_batches(batches)

        if not wait_for_completion:
            logger.info(f"Batches submitted asynchronously. Batch IDs: {batch_ids}")
            return {
                "status": "submitted",
                "batch_ids": batch_ids,
                "provider": self.batch_executor.provider,
                "model": self.batch_executor.model
            }

        # Step 7: Wait for completion
        success = self.wait_for_batches(batch_ids, max_wait_hours)

        if not success:
            logger.error("Some batches failed to complete")
            return {"status": "failed", "batch_ids": batch_ids}

        # Step 8: Process results
        results = self.process_batch_results(batch_ids)

        # Step 9: Export results
        output_files = self.export_results()

        logger.info("Research workflow complete")

        return {
            "status": "completed",
            "results": results,
            "output_files": output_files,
            "provider": self.batch_executor.provider,
            "model": self.batch_executor.model
        }

    def check_batch_status(self):
        """Check status of all submitted batches"""
        logger.info("Checking batch statuses")

        self.batch_executor.load_batch_tracking()
        statuses = self.batch_executor.get_all_batch_statuses()

        for status in statuses:
            logger.info(
                f"Batch {status['batch_id']}: {status['status']} "
                f"({status['request_counts']['completed']}/{status['request_counts']['total']})"
            )

        return statuses

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current batch provider"""
        return self.batch_executor.get_provider_info()


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description="Corporate Asset Research Agent V3 - Rules-Based Architecture"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run complete research workflow")
    run_parser.add_argument("companies_file", help="Path to companies file (JSON or Excel)")
    run_parser.add_argument("--batch-size", type=int, default=100, help="Subtasks per batch")
    run_parser.add_argument("--output-dir", default="./research_output_v3", help="Output directory")
    run_parser.add_argument("--provider", default="doubleword", choices=["openai", "doubleword"], help="Batch provider")
    run_parser.add_argument("--model", help="Override default model")
    run_parser.add_argument("--no-wait", action="store_true", help="Don't wait for completion")
    run_parser.add_argument("--config", help="Path to rules configuration file")

    # Status command
    status_parser = subparsers.add_parser("status", help="Check batch status")
    status_parser.add_argument("--output-dir", default="./research_output_v3", help="Output directory")

    # Info command
    info_parser = subparsers.add_parser("info", help="Show provider information")
    info_parser.add_argument("--output-dir", default="./research_output_v3", help="Output directory")
    info_parser.add_argument("--provider", default="doubleword", choices=["openai", "doubleword"], help="Batch provider")

    args = parser.parse_args()

    if args.command == "run":
        api_key = os.getenv("BATCH_API_KEY")
        if not api_key:
            logger.error("BATCH_API_KEY environment variable not set")
            return

        app = ResearchApplicationV3(
            output_dir=args.output_dir,
            api_key=api_key,
            provider=args.provider,
            model=args.model,
            config_file=args.config
        )

        result = app.run_complete_research(
            args.companies_file,
            batch_size=args.batch_size,
            wait_for_completion=not args.no_wait
        )

        print(json.dumps(result, indent=2, default=str))

    elif args.command == "status":
        api_key = os.getenv("BATCH_API_KEY")
        app = ResearchApplicationV3(output_dir=args.output_dir, api_key=api_key)
        statuses = app.check_batch_status()
        print(json.dumps(statuses, indent=2, default=str))

    elif args.command == "info":
        api_key = os.getenv("BATCH_API_KEY")
        app = ResearchApplicationV3(output_dir=args.output_dir, api_key=api_key, provider=args.provider)
        info = app.get_provider_info()
        print(json.dumps(info, indent=2, default=str))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
