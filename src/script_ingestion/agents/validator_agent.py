from agents import Agent, Runner
from typing import Dict, Any, List
import json
import logging
import re
from datetime import datetime, timedelta
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
    
    def _validate_timeline(self, timeline: Dict[str, Any]) -> Dict[str, Any]:
        """Validate timeline data for consistency and pacing with improved duration checks."""
        validation = {
            "is_valid": True,
            "continuity_issues": [],
            "duration_issues": [],
            "pacing_analysis": {
                "scene_pacing": [],
                "suggestions": []
            }
        }
        
        if not timeline or "scene_breakdown" not in timeline:
            validation["is_valid"] = False
            validation["continuity_issues"].append("Timeline data is missing or invalid")
            return validation
        
        scenes = timeline["scene_breakdown"]
        prev_scene = None
        total_duration = 0
        
        for scene in scenes:
            scene_num = scene.get('scene_number', '?')
            
            # Validate duration consistency
            try:
                duration = int(scene.get('duration_minutes', 0))
            except (ValueError, TypeError):
                duration = 0
                
            if duration == 0:
                validation["duration_issues"].append(
                    f"Scene {scene_num} has no duration specified"
                )
            elif duration < 1:
                validation["duration_issues"].append(
                    f"Scene {scene_num} has invalid duration: {duration} minutes"
                )
            
            # Validate setup time vs duration
            try:
                setup_time = int(scene.get('setup_time', 0))
            except (ValueError, TypeError):
                setup_time = 0
                
            if setup_time > duration * 60:  # setup time in seconds
                validation["duration_issues"].append(
                    f"Scene {scene_num} setup time ({setup_time}s) exceeds scene duration ({duration}m)"
                )
            
            # Track total duration
            total_duration += duration
            
            # Analyze pacing based on content and duration
            tech_complexity = int(scene.get('technical_complexity', 0))
            if duration <= 2:
                if tech_complexity > 2:
                    validation["pacing_analysis"]["suggestions"].append(
                        f"Scene {scene_num} may need more time for {tech_complexity} technical requirements"
                    )
                validation["pacing_analysis"]["scene_pacing"].append("FAST")
            elif duration <= 5:
                validation["pacing_analysis"]["scene_pacing"].append("MEDIUM")
            else:
                if tech_complexity == 0:
                    validation["pacing_analysis"]["suggestions"].append(
                        f"Scene {scene_num} duration ({duration}m) may be too long for simple setup"
                    )
                validation["pacing_analysis"]["scene_pacing"].append("SLOW")
            
            # Check time continuity
            if prev_scene:
                try:
                    prev_end = datetime.strptime(prev_scene["end_time"], "%H:%M:%S")
                    curr_start = datetime.strptime(scene["start_time"], "%H:%M:%S")
                    if prev_end != curr_start:
                        validation["continuity_issues"].append(
                            f"Time gap between scenes {prev_scene['scene_number']} and {scene_num}"
                        )
                except (ValueError, TypeError):
                    validation["continuity_issues"].append(
                        f"Invalid time format in scene {scene_num} timeline"
                    )
            
            prev_scene = scene
        
        # Validate total duration consistency
        if "total_duration" in timeline:
            try:
                reported_total = datetime.strptime(timeline["total_duration"], "%H:%M:%S")
                calculated_total = timedelta(minutes=total_duration)
                if abs((reported_total - datetime.min).total_seconds() - calculated_total.total_seconds()) > 60:
                    validation["duration_issues"].append(
                        f"Total duration mismatch: reported {timeline['total_duration']} vs calculated {str(calculated_total)}"
                    )
            except (ValueError, TypeError):
                validation["duration_issues"].append("Invalid total duration format")
        
        # Analyze overall pacing
        pacing_counts = {
            "FAST": validation["pacing_analysis"]["scene_pacing"].count("FAST"),
            "MEDIUM": validation["pacing_analysis"]["scene_pacing"].count("MEDIUM"),
            "SLOW": validation["pacing_analysis"]["scene_pacing"].count("SLOW")
        }
        
        if pacing_counts["FAST"] > len(scenes) * 0.6:
            validation["pacing_analysis"]["suggestions"].append(
                "Script may be too fast-paced. Consider adding more character development scenes."
            )
        elif pacing_counts["SLOW"] > len(scenes) * 0.4:
            validation["pacing_analysis"]["suggestions"].append(
                "Script may be too slow-paced. Consider tightening some scenes."
            )
        
        # Update validation status
        validation["is_valid"] = (
            len(validation["continuity_issues"]) == 0
            and len(validation["duration_issues"]) == 0
        )
        
        return validation
    
    def _validate_technical_elements(self, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate technical elements and requirements."""
        validation = {
            "complex_elements": [],
            "department_conflicts": [],
            "resource_requirements": []
        }
        
        for scene in scenes:
            # Check for complex technical requirements
            technical_cues = scene.get("technical_cues", [])
            if len(technical_cues) > 3:
                validation["complex_elements"].append({
                    "scene_number": scene.get("scene_number", "?"),
                    "elements": technical_cues
                })
            
            # Check for department conflicts
            dept_notes = scene.get("department_notes", {})
            if len(dept_notes.get("props", [])) > 0 and len(dept_notes.get("camera", [])) > 0:
                validation["department_conflicts"].append({
                    "scene_number": scene.get("scene_number", "?"),
                    "conflict": "Props and camera movement may interfere"
                })
            
            # Track resource requirements
            for dept, notes in dept_notes.items():
                if notes:
                    validation["resource_requirements"].append({
                        "scene_number": scene.get("scene_number", "?"),
                        "department": dept,
                        "requirements": notes
                    })
        
        return validation
    
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
        
        # Timeline validation
        timeline_validation = validation_result.get("timeline_validation", {})
        if timeline_validation:
            output.extend([
                "\nTIMELINE VALIDATION:",
                f"Status: {'PASS' if timeline_validation.get('is_valid', False) else 'FAIL'}"
            ])
            
            if timeline_validation.get("continuity_issues"):
                output.append("\nContinuity Issues:")
                for issue in timeline_validation["continuity_issues"]:
                    output.append(f"  - {issue}")
            
            if timeline_validation.get("pacing_analysis", {}).get("suggestions"):
                output.append("\nPacing Analysis:")
                for suggestion in timeline_validation["pacing_analysis"]["suggestions"]:
                    output.append(f"  - {suggestion}")
        
        # Technical validation
        tech_validation = validation_result.get("technical_validation", {})
        if tech_validation:
            output.append("\nTECHNICAL VALIDATION:")
            
            if tech_validation.get("complex_elements"):
                output.append("\nComplex Technical Elements:")
                for element in tech_validation["complex_elements"]:
                    output.extend([
                        f"  Scene {element['scene_number']}:",
                        f"    {', '.join(element['elements'])}"
                    ])
            
            if tech_validation.get("department_conflicts"):
                output.append("\nDepartment Conflicts:")
                for conflict in tech_validation["department_conflicts"]:
                    output.extend([
                        f"  Scene {conflict['scene_number']}:",
                        f"    {conflict['conflict']}"
        ])
        
        # Issues section
        issues = validation_result.get("issues", [])
        if issues:
            output.append("\nISSUES FOUND:")
            for issue in issues:
                output.extend([
                    f"\nType: {issue.get('type', 'Unknown')}",
                    f"Category: {issue.get('category', 'Unknown')}",
                    f"Scene: {issue.get('scene_number', 'N/A')}",
                    f"Description: {issue.get('description', 'No description')}",
                    f"Suggestion: {issue.get('suggestion', 'No suggestion')}\n"
                ])
        else:
            output.append("\nNo general issues found.")
        
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
        - Timeline consistency
        - Technical requirements feasibility
        
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
            "timeline_validation": {{
                "is_valid": true/false,
                "continuity_issues": [],
                "pacing_analysis": {{
                    "scene_pacing": ["FAST", "MEDIUM", "SLOW"],
                    "suggestions": []
                }}
            }},
            "technical_validation": {{
                "complex_elements": [
                    {{
                        "scene_number": "1",
                        "elements": ["list of complex elements"]
                    }}
                ],
                "department_conflicts": [
                    {{
                        "scene_number": "1",
                        "conflict": "description of conflict"
                    }}
                ],
                "resource_requirements": [
                    {{
                        "scene_number": "1",
                        "department": "department name",
                        "requirements": ["list of requirements"]
                    }}
                ]
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
                
                # Add timeline validation
                if "timeline" in parsed_data:
                    validation_result["timeline_validation"] = self._validate_timeline(parsed_data["timeline"])
                
                # Add technical validation
                validation_result["technical_validation"] = self._validate_technical_elements(parsed_data.get("scenes", []))
                
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