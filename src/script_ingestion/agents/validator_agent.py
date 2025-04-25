from agents import Agent, Runner
from typing import Dict, Any, List
import json
import logging
import re
from ...base_config import AGENT_INSTRUCTIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidatorAgent:
    def __init__(self):
        self.agent = Agent(
            name="Format Validator",
            instructions=AGENT_INSTRUCTIONS["validator"]
        )
        logger.info("ValidatorAgent initialized")
    
    def _clean_json_response(self, response: str) -> str:
        """Clean the response text to extract JSON content from potential markdown wrapping."""
        # Try to extract JSON from markdown code blocks if present
        json_pattern = r"```(?:json)?\n([\s\S]*?)\n```"
        matches = re.findall(json_pattern, response)
        
        if matches:
            logger.info("Found JSON content wrapped in code blocks, extracting...")
            return matches[0].strip()
        
        # If no code blocks found, return the original response
        return response.strip()
    
    def format_validation_report(self, validation_result: Dict[str, Any]) -> str:
        """Format validation results into readable text."""
        if "error" in validation_result:
            return f"Error: {validation_result['error']}"
            
        output = []
        
        # Overall status
        status = "PASSED" if validation_result.get("is_valid", False) else "FAILED"
        output.extend([
            f"\n{'='*80}",
            f"VALIDATION REPORT - {status}",
            f"{'-'*80}\n"
        ])
        
        # Issues section
        issues = validation_result.get("issues", [])
        if issues:
            output.append("ISSUES FOUND:")
            for issue in issues:
                output.extend([
                    f"\nType: {issue.get('type', 'Unknown')}",
                    f"Category: {issue.get('category', 'Unknown')}",
                    f"Scene: {issue.get('scene_number', 'N/A')}",
                    f"Description: {issue.get('description', 'No description')}",
                    f"Suggestion: {issue.get('suggestion', 'No suggestion')}\n"
                ])
        else:
            output.append("No issues found.\n")
        
        # Scene validations
        output.extend([
            f"\n{'='*80}",
            "SCENE VALIDATIONS",
            f"{'-'*80}\n"
        ])
        
        for scene_validation in validation_result.get("scene_validations", []):
            output.extend([
                f"\nSCENE {scene_validation.get('scene_number', 'Unknown')}:"
            ])
            
            for check in scene_validation.get("checks", []):
                status = "✓" if check.get("status") == "pass" else "✗"
                output.append(f"  {status} {check.get('check_name', 'Unknown check')}: {check.get('details', 'No details')}")
        
        # Metadata validation
        metadata_validation = validation_result.get("metadata_validation", {})
        output.extend([
            f"\n{'='*80}",
            "METADATA VALIDATION",
            f"{'-'*80}\n",
            f"SMPTE Compliance: {'Yes' if metadata_validation.get('smpte_compliance', False) else 'No'}"
        ])
        
        if metadata_validation.get("missing_fields"):
            output.append("\nMissing Fields:")
            for field in metadata_validation["missing_fields"]:
                output.append(f"  - {field}")
        
        if metadata_validation.get("warnings"):
            output.append("\nWarnings:")
            for warning in metadata_validation["warnings"]:
                output.append(f"  - {warning}")
        
        # Summary
        summary = validation_result.get("summary", {})
        output.extend([
            f"\n{'='*80}",
            "VALIDATION SUMMARY",
            f"{'-'*80}",
            f"Total Scenes: {summary.get('total_scenes', 0)}",
            f"Valid Scenes: {summary.get('valid_scenes', 0)}",
            f"Scenes with Issues: {summary.get('scenes_with_issues', 0)}",
            f"Total Issues: {summary.get('total_issues', 0)}"
        ])
        
        return "\n".join(output)
    
    async def validate_data(self, parsed_data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the structural integrity of parsed data and metadata."""
        logger.info("Starting data validation")
        
        if not parsed_data or not isinstance(parsed_data, dict):
            logger.error("Invalid parsed data received")
            return {
                "is_valid": False,
                "error": "Invalid parsed data format",
                "validation_report": {"issues": ["Parsed data is invalid or empty"]},
                "formatted_text": "Error: Invalid parsed data format"
            }
        
        if not metadata or not isinstance(metadata, dict):
            logger.error("Invalid metadata received")
            return {
                "is_valid": False,
                "error": "Invalid metadata format",
                "validation_report": {"issues": ["Metadata is invalid or empty"]},
                "formatted_text": "Error: Invalid metadata format"
            }
        
        logger.info(f"Validating {len(parsed_data.get('scenes', []))} scenes")
        
        prompt = f"""Validate this script data and metadata for:
        - Scene numbering consistency
        - Continuity between scenes
        - Required field completeness
        - SMPTE metadata compliance
        - Technical specification accuracy
        
        Return the validation report in this exact JSON format:
        {{
            "is_valid": true/false,
            "issues": [
                {{
                    "type": "error/warning",
                    "category": "scene_numbering/continuity/fields/metadata/technical",
                    "scene_number": "scene number (if applicable)",
                    "description": "detailed description of the issue",
                    "suggestion": "suggested fix"
                }}
            ],
            "scene_validations": [
                {{
                    "scene_number": "1",
                    "checks": [
                        {{
                            "check_name": "name of check",
                            "status": "pass/fail",
                            "details": "details of the check"
                        }}
                    ]
                }}
            ],
            "metadata_validation": {{
                "smpte_compliance": true/false,
                "missing_fields": ["list of missing required fields"],
                "warnings": ["list of metadata warnings"]
            }},
            "summary": {{
                "total_scenes": 0,
                "valid_scenes": 0,
                "scenes_with_issues": 0,
                "total_issues": 0
            }}
        }}
        
        Parsed Data:
        {json.dumps(parsed_data, indent=2)}
        
        Metadata:
        {json.dumps(metadata, indent=2)}
        """
        
        logger.info("Sending data to agent for validation")
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received validation response from agent")
            
            try:
                # Clean the response first
                cleaned_response = self._clean_json_response(result.final_output)
                logger.info("Cleaned response for JSON parsing")
                
                # Try to parse the JSON response
                validation_result = json.loads(cleaned_response)
                logger.info("Successfully parsed validation JSON response")
                
                # Validate the validation result structure
                if not isinstance(validation_result, dict):
                    raise ValueError("Validation response is not a dictionary")
                if "is_valid" not in validation_result:
                    raise ValueError("Validation missing 'is_valid' key")
                if "issues" not in validation_result:
                    raise ValueError("Validation missing 'issues' key")
                
                # Log validation summary
                issues_count = len(validation_result.get("issues", []))
                logger.info(f"Validation complete: {'PASS' if validation_result['is_valid'] else 'FAIL'}")
                if issues_count > 0:
                    logger.warning(f"Found {issues_count} issues during validation")
                
                # Add formatted text representation
                validation_result["formatted_text"] = self.format_validation_report(validation_result)
                
                return {
                    "is_valid": validation_result["is_valid"],
                    "validation_report": validation_result,
                    "formatted_text": validation_result["formatted_text"]
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Validation JSON parsing error: {str(e)}")
                logger.error(f"Raw validation response: {result.final_output}")
                return {
                    "is_valid": False,
                    "error": "Failed to parse validation report into valid JSON format",
                    "details": str(e),
                    "raw_response": result.final_output[:500],
                    "formatted_text": "Error: Failed to parse validation report"
                }
            except ValueError as e:
                logger.error(f"Validation structure error: {str(e)}")
                return {
                    "is_valid": False,
                    "error": f"Invalid validation report structure: {str(e)}",
                    "raw_response": result.final_output[:500],
                    "formatted_text": f"Error: Invalid validation report structure - {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Validation processing error: {str(e)}")
            return {
                "is_valid": False,
                "error": f"Error during validation: {str(e)}",
                "formatted_text": f"Error: Validation process failed - {str(e)}"
            }