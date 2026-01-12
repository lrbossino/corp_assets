"""
Tool Definitions - Research Tools
Defines tools available for research tasks
These are sent to the batch API and executed client-side
"""

from typing import List, Dict, Any

# Tool definitions in OpenAI format
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for information about a company or facility",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'Apple data centers locations')"
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["general", "news", "academic", "images"],
                        "description": "Type of search to perform"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (1-10)",
                        "default": 5
                    },
                    "language": {
                        "type": "string",
                        "description": "Language for search (e.g., 'en', 'de', 'fr', 'ja')",
                        "default": "en"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "parse_document",
            "description": "Extract structured information from a document (PDF, webpage, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the document to parse"
                    },
                    "document_type": {
                        "type": "string",
                        "enum": ["annual_report", "sec_filing", "press_release", "webpage", "pdf"],
                        "description": "Type of document"
                    },
                    "extraction_focus": {
                        "type": "string",
                        "description": "What to focus on (e.g., 'facilities', 'offices', 'data centers', 'locations')"
                    }
                },
                "required": ["url", "extraction_focus"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_registry",
            "description": "Look up company information in business registries",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Company name to look up"
                    },
                    "registry_type": {
                        "type": "string",
                        "enum": ["companies_house", "sec_edgar", "eu_registry", "local_registry"],
                        "description": "Type of registry to search"
                    },
                    "country": {
                        "type": "string",
                        "description": "Country code (e.g., 'US', 'UK', 'DE')"
                    }
                },
                "required": ["company_name", "registry_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_asset",
            "description": "Validate and verify an asset location",
            "parameters": {
                "type": "object",
                "properties": {
                    "facility_name": {
                        "type": "string",
                        "description": "Name of the facility"
                    },
                    "address": {
                        "type": "string",
                        "description": "Address of the facility"
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Company name to verify ownership"
                    },
                    "validation_type": {
                        "type": "string",
                        "enum": ["ownership", "location", "activity"],
                        "description": "What to validate"
                    }
                },
                "required": ["facility_name", "address", "company_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_coordinates",
            "description": "Get latitude and longitude coordinates for an address",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Full address or facility name"
                    },
                    "city": {
                        "type": "string",
                        "description": "City name"
                    },
                    "country": {
                        "type": "string",
                        "description": "Country name or code"
                    }
                },
                "required": ["address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_job_postings",
            "description": "Search job posting sites for facility location clues",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Company name to search for"
                    },
                    "job_site": {
                        "type": "string",
                        "enum": ["linkedin", "indeed", "glassdoor", "all"],
                        "description": "Job site to search"
                    },
                    "keywords": {
                        "type": "string",
                        "description": "Additional keywords (e.g., 'office', 'data center', 'warehouse')"
                    }
                },
                "required": ["company_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_subsidiaries",
            "description": "Get list of company subsidiaries and their locations",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Parent company name"
                    },
                    "include_locations": {
                        "type": "boolean",
                        "description": "Whether to include location data for subsidiaries",
                        "default": True
                    }
                },
                "required": ["company_name"]
            }
        }
    }
]


def format_tool_definitions_for_prompt() -> str:
    """
    Format tool definitions as a readable prompt section.

    Returns:
        Formatted tool definitions string
    """
    formatted = "## Available Tools\n\n"

    for tool in TOOL_DEFINITIONS:
        func = tool["function"]
        formatted += f"### {func['name']}\n"
        formatted += f"{func['description']}\n\n"

        formatted += "**Parameters:**\n"
        for param_name, param_info in func["parameters"]["properties"].items():
            required = param_name in func["parameters"].get("required", [])
            param_type = param_info.get("type", "unknown")
            description = param_info.get("description", "")
            formatted += f"- `{param_name}` ({param_type}){' *required*' if required else ''}: {description}\n"

        formatted += "\n"

    return formatted


def get_tool_by_name(tool_name: str) -> Dict[str, Any]:
    """Get a tool definition by name"""
    for tool in TOOL_DEFINITIONS:
        if tool["function"]["name"] == tool_name:
            return tool
    raise ValueError(f"Tool not found: {tool_name}")


def get_tool_names() -> List[str]:
    """Get list of all available tool names"""
    return [tool["function"]["name"] for tool in TOOL_DEFINITIONS]


# Tool execution examples (for documentation)
TOOL_EXECUTION_EXAMPLES = {
    "search_web": {
        "example_call": {
            "query": "Apple data centers locations worldwide",
            "search_type": "general",
            "num_results": 5,
            "language": "en"
        },
        "example_result": {
            "results": [
                {
                    "title": "Apple Data Centers",
                    "url": "https://example.com/apple-data-centers",
                    "snippet": "Apple operates data centers in multiple locations...",
                    "source": "official"
                }
            ],
            "total_results": 1250000
        }
    },
    "parse_document": {
        "example_call": {
            "url": "https://investor.apple.com/annual-report-2023.pdf",
            "document_type": "annual_report",
            "extraction_focus": "facilities and data centers"
        },
        "example_result": {
            "extracted_data": {
                "facilities": [
                    {
                        "name": "Apple Park",
                        "location": "Cupertino, California",
                        "type": "headquarters"
                    }
                ]
            },
            "confidence": 0.95
        }
    },
    "lookup_registry": {
        "example_call": {
            "company_name": "Apple Inc.",
            "registry_type": "sec_edgar",
            "country": "US"
        },
        "example_result": {
            "company_id": "0000320193",
            "registered_address": "One Apple Park Way, Cupertino, CA 95014",
            "subsidiaries": ["Apple Sales International", "Apple Distribution International"]
        }
    }
}
