"""
Rules Engine - Deterministic Research Planning
Replaces the real-time orchestration agent with rule-based task decomposition
No API calls; purely deterministic based on company attributes
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ResearchPhase(Enum):
    """Research phases in deterministic order"""
    OFFICIAL_SOURCES = "OFFICIAL_SOURCES"
    LOCAL_REGISTRIES = "LOCAL_REGISTRIES"
    JOB_POSTINGS = "JOB_POSTINGS"
    ALTERNATIVE_SOURCES = "ALTERNATIVE_SOURCES"
    VALIDATION = "VALIDATION"


@dataclass
class ResearchSubtask:
    """Represents a single research subtask"""
    subtask_id: str
    company_id: str
    company_name: str
    phase: ResearchPhase
    objective: str
    tools_needed: List[str]
    expected_output: str
    phase_type: str  # "mandatory" or "optional"


class RulesEngine:
    """
    Deterministic rules-based orchestration engine.
    Generates research subtasks based on company attributes without API calls.
    """

    # Phase tool mappings - deterministic, no reasoning needed
    PHASE_TOOL_MAPPING = {
        "OFFICIAL_SOURCES": ["search_web", "parse_document"],
        "LOCAL_REGISTRIES": ["lookup_registry", "search_web"],
        "JOB_POSTINGS": ["search_web"],
        "ALTERNATIVE_SOURCES": ["search_web"],
        "VALIDATION": ["validate_asset", "search_web"]
    }

    # Phase objectives - templated, no reasoning needed
    PHASE_OBJECTIVES = {
        "OFFICIAL_SOURCES": "Search official company sources (annual reports, SEC filings, investor presentations, company websites) for {asset_types}",
        "LOCAL_REGISTRIES": "Search business registries, government records, and official filings for registered {asset_types}",
        "JOB_POSTINGS": "Search job posting sites (LinkedIn, Indeed, Glassdoor) for facility location clues related to {asset_types}",
        "ALTERNATIVE_SOURCES": "Search news articles, Wikipedia, industry reports, and press releases for {asset_types}",
        "VALIDATION": "Validate and consolidate all discovered {asset_types}, removing duplicates and verifying ownership"
    }

    # Expected outputs - templated, consistent format
    EXPECTED_OUTPUT_TEMPLATE = "JSON list of discovered {asset_type_name} with facility names, addresses, coordinates, source URLs, confidence scores"

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the rules engine.

        Args:
            config_file: Optional path to configuration file
        """
        self.config = self._load_config(config_file) if config_file else self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for research rules"""
        return {
            "capital_intensity_rules": {
                "High": {
                    "mandatory_phases": ["OFFICIAL_SOURCES", "LOCAL_REGISTRIES", "JOB_POSTINGS"],
                    "optional_phases": ["ALTERNATIVE_SOURCES", "VALIDATION"],
                    "min_assets_target": 100
                },
                "Low": {
                    "mandatory_phases": ["OFFICIAL_SOURCES", "LOCAL_REGISTRIES"],
                    "optional_phases": ["JOB_POSTINGS", "ALTERNATIVE_SOURCES", "VALIDATION"],
                    "min_assets_target": 40
                }
            },
            "sector_asset_type_mapping": {
                "Semiconductors & Semiconductor Equipment": "Data centers, offices, R&D centers, manufacturing facilities",
                "Technology Hardware & Equipment": "Data centers, offices, R&D centers, manufacturing facilities",
                "Software & Services": "Data centers, offices, R&D centers",
                "Media & Entertainment": "Telecom infrastructure, broadcasting facilities, data centers, offices",
                "Broadline Retail": "Retail stores, distribution centers, warehouses, manufacturing plants",
                "Automobiles & Components": "Manufacturing plants, distribution centers, retail locations, warehouses",
                "Banks": "Office buildings, data centers, ATM networks, branch locations",
                "Capital Goods": "Manufacturing plants, warehouses, equipment facilities",
                "Machinery": "Manufacturing plants, warehouses, equipment facilities",
                "Consumer Services": "Retail stores, distribution centers, warehouses",
                "Entertainment": "Offices, data centers, broadcasting facilities",
                "Materials": "Mines, mills, smelters, processing plants, quarries",
                "Chemicals": "Manufacturing plants, processing facilities, warehouses",
                "Metals & Mining": "Mines, mills, smelters, processing plants, quarries",
                "Transportation": "Manufacturing plants, warehouses, distribution centers, maintenance facilities"
            }
        }

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using defaults")
            return self._default_config()

    def plan_research(self, company: Dict[str, Any]) -> Tuple[List[ResearchSubtask], Dict[str, Any]]:
        """
        Plan research for a company using deterministic rules.
        No API calls; purely based on company attributes.

        Args:
            company: Company data dictionary with keys:
                - company_id: Unique identifier
                - org: Company name
                - CapitalIntensityBucket: "High" or "Low"
                - gicslv2: GICS sector classification
                - asset_type_guidelines: Asset types to focus on
                - asset_count_guidelines: Target number of assets

        Returns:
            Tuple of (subtasks, phase_info)
        """
        company_id = company.get("company_id") or company.get("orgid")
        company_name = company.get("org")
        capital_intensity = company.get("CapitalIntensityBucket", "High")
        sector = company.get("gicslv2", "Unknown")
        asset_types = company.get("asset_type_guidelines", "facilities")
        target_count = company.get("asset_count_guidelines", 100)

        logger.info(f"Planning research for {company_name} ({capital_intensity} intensity, target: {target_count} assets)")

        # Step 1: Determine research phases
        phase_info = self._get_research_phases(capital_intensity, target_count)

        # Step 2: Create subtasks for each phase
        subtasks = []
        all_phases = phase_info["mandatory_phases"] + phase_info["optional_phases"]

        for idx, phase_name in enumerate(all_phases):
            phase = ResearchPhase[phase_name]
            phase_type = "mandatory" if phase_name in phase_info["mandatory_phases"] else "optional"

            objective = self._get_phase_objective(phase_name, asset_types, sector)
            tools = self.PHASE_TOOL_MAPPING.get(phase_name, [])
            expected_output = self._get_expected_output(asset_types)

            subtask = ResearchSubtask(
                subtask_id=f"{company_id}_phase_{idx}_{phase_name}",
                company_id=str(company_id),
                company_name=company_name,
                phase=phase,
                objective=objective,
                tools_needed=tools,
                expected_output=expected_output,
                phase_type=phase_type
            )
            subtasks.append(subtask)

        logger.info(f"Planned {len(subtasks)} subtasks for {company_name} ({len(phase_info['mandatory_phases'])} mandatory, {len(phase_info['optional_phases'])} optional)")

        return subtasks, phase_info

    def _get_research_phases(self, capital_intensity: str, target_count: int) -> Dict[str, Any]:
        """
        Determine mandatory vs optional research phases based on capital intensity.
        Deterministic rule: High intensity = more phases, Low intensity = fewer phases
        """
        intensity_key = capital_intensity if capital_intensity in self.config["capital_intensity_rules"] else "High"
        rules = self.config["capital_intensity_rules"][intensity_key]

        return {
            "mandatory_phases": rules["mandatory_phases"],
            "optional_phases": rules["optional_phases"],
            "target_assets": target_count,
            "capital_intensity": capital_intensity
        }

    def _get_phase_objective(self, phase_name: str, asset_types: str, sector: str) -> str:
        """
        Get the objective for a specific phase.
        Deterministic: template substitution, no reasoning
        """
        template = self.PHASE_OBJECTIVES.get(phase_name, "Research {asset_types}")
        return template.format(asset_types=asset_types)

    def _get_expected_output(self, asset_types: str) -> str:
        """Get expected output format for a phase"""
        return self.EXPECTED_OUTPUT_TEMPLATE.format(asset_type_name=asset_types)

    def plan_batch_research(self, companies: List[Dict[str, Any]]) -> Tuple[List[ResearchSubtask], Dict[str, Any]]:
        """
        Plan research for multiple companies.

        Args:
            companies: List of company dictionaries

        Returns:
            Tuple of (all_subtasks, summary_stats)
        """
        all_subtasks = []
        summary_stats = {
            "total_companies": len(companies),
            "total_subtasks": 0,
            "mandatory_subtasks": 0,
            "optional_subtasks": 0,
            "by_capital_intensity": {"High": 0, "Low": 0},
            "planning_time_ms": 0
        }

        import time
        start_time = time.time()

        for company in companies:
            subtasks, phase_info = self.plan_research(company)
            all_subtasks.extend(subtasks)

            # Update stats
            summary_stats["total_subtasks"] += len(subtasks)
            summary_stats["mandatory_subtasks"] += len(phase_info["mandatory_phases"])
            summary_stats["optional_subtasks"] += len(phase_info["optional_phases"])
            intensity = company.get("CapitalIntensityBucket", "High")
            summary_stats["by_capital_intensity"][intensity] += len(subtasks)

        summary_stats["planning_time_ms"] = int((time.time() - start_time) * 1000)

        logger.info(f"Planned {summary_stats['total_subtasks']} total subtasks for {len(companies)} companies in {summary_stats['planning_time_ms']}ms")

        return all_subtasks, summary_stats

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config

    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration"""
        self._deep_update(self.config, updates)
        logger.info("Configuration updated")

    @staticmethod
    def _deep_update(d: Dict, u: Dict) -> None:
        """Deep update dictionary"""
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = d.get(k, {})
                RulesEngine._deep_update(d[k], v)
            else:
                d[k] = v

    def save_config(self, output_file: str) -> None:
        """Save configuration to file"""
        with open(output_file, "w") as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"Configuration saved to {output_file}")

    def validate_company_data(self, company: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate that company data has required fields.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        required_fields = ["company_id", "org", "CapitalIntensityBucket", "asset_count_guidelines"]
        errors = []

        for field in required_fields:
            if field not in company and field not in ["company_id", "orgid"]:
                errors.append(f"Missing required field: {field}")

        # Check capital intensity is valid
        if company.get("CapitalIntensityBucket") not in ["High", "Low"]:
            errors.append(f"Invalid CapitalIntensityBucket: {company.get('CapitalIntensityBucket')}")

        # Check asset count is positive
        if company.get("asset_count_guidelines", 0) <= 0:
            errors.append(f"Invalid asset_count_guidelines: {company.get('asset_count_guidelines')}")

        return len(errors) == 0, errors

    def get_phase_summary(self, subtasks: List[ResearchSubtask]) -> Dict[str, Any]:
        """Get summary of subtasks by phase"""
        summary = {}
        for phase in ResearchPhase:
            phase_tasks = [t for t in subtasks if t.phase == phase]
            if phase_tasks:
                summary[phase.value] = {
                    "count": len(phase_tasks),
                    "mandatory": len([t for t in phase_tasks if t.phase_type == "mandatory"]),
                    "optional": len([t for t in phase_tasks if t.phase_type == "optional"])
                }
        return summary
