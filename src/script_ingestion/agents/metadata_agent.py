from agents import Agent, Runner
from typing import Dict, Any
import json
import logging
import re
from ...base_config import AGENT_INSTRUCTIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetadataAgent:
    def __init__(self):
        self.agent = Agent(
            name="Metadata Extractor",
            instructions=AGENT_INSTRUCTIONS["metadata"]
        )
        logger.info("MetadataAgent initialized")
    
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
    
    def format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata into readable text."""
        if "error" in metadata:
            return f"Error: {metadata['error']}"
            
        output = []
        
        # Add timestamp
        output.append(f"Analysis Timestamp: {metadata.get('timestamp', 'Not specified')}\n")
        
        # Format scene metadata
        for scene in metadata.get("scene_metadata", []):
            output.extend([
                f"\n{'='*80}",
                f"SCENE {scene['scene_number']} - TECHNICAL BREAKDOWN",
                f"{'-'*80}\n"
            ])
            
            # Mood
            output.append(f"Mood: {scene.get('mood', 'Not specified')}\n")
            
            # Lighting
            lighting = scene.get('lighting', {})
            output.extend([
                "Lighting:",
                f"  Type: {lighting.get('type', 'Not specified')}",
                f"  Requirements: {', '.join(lighting.get('requirements', ['None']))}",
                f"  Special Effects: {', '.join(lighting.get('special_effects', ['None']))}\n"
            ])
            
            # Time details
            time_details = scene.get('time_details', {})
            output.extend([
                "Time Details:",
                f"  Time of Day: {time_details.get('time_of_day', 'Not specified')}",
                f"  Duration: {time_details.get('duration', 'Not specified')}\n"
            ])
            
            # Weather
            weather = scene.get('weather', {})
            output.extend([
                "Weather:",
                f"  Conditions: {', '.join(weather.get('conditions', ['None']))}",
                f"  Effects Needed: {', '.join(weather.get('effects_needed', ['None']))}\n"
            ])
            
            # Props
            props = scene.get('props', {})
            output.extend([
                "Props:",
                f"  Set Dressing: {', '.join(props.get('set_dressing', ['None']))}",
                f"  Hand Props: {', '.join(props.get('hand_props', ['None']))}",
                f"  Special Items: {', '.join(props.get('special_items', ['None']))}\n"
            ])
            
            # Technical
            technical = scene.get('technical', {})
            output.extend([
                "Technical Requirements:",
                f"  Camera: {', '.join(technical.get('camera', ['None']))}",
                f"  Sound: {', '.join(technical.get('sound', ['None']))}",
                f"  Special Equipment: {', '.join(technical.get('special_equipment', ['None']))}\n"
            ])
        
        # Global requirements
        global_reqs = metadata.get("global_requirements", {})
        output.extend([
            f"\n{'='*80}",
            "GLOBAL REQUIREMENTS",
            f"{'-'*80}\n",
            f"Equipment: {', '.join(global_reqs.get('equipment', ['None']))}",
            f"Props: {', '.join(global_reqs.get('props', ['None']))}",
            f"Special Effects: {', '.join(global_reqs.get('special_effects', ['None']))}"
        ])
        
        return "\n".join(output)
    
    async def extract_metadata(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed metadata from parsed scene data."""
        logger.info("Starting metadata extraction")
        
        if not scene_data or not isinstance(scene_data, dict):
            logger.error("Invalid scene data received")
            return {
                "error": "Invalid scene data format",
                "formatted_text": "Error: Invalid scene data format"
            }
        
        logger.info(f"Processing metadata for {len(scene_data.get('scenes', []))} scenes")
        
        prompt = f"""Analyze this scene data and extract detailed metadata including:
        - Mood and atmosphere
        - Lighting requirements
        - Time of day details
        - Weather conditions (if applicable)
        - Required props and set dressing
        - Technical requirements
        
        Return the data in this exact JSON format:
        {{
            "timestamp": "YYYY-MM-DD HH:MM:SS",
            "scene_metadata": [
                {{
                    "scene_number": "1",
                    "mood": "description of mood",
                    "lighting": {{
                        "type": "natural/artificial",
                        "requirements": ["specific lighting needs"],
                        "special_effects": ["any lighting effects"]
                    }},
                    "time_details": {{
                        "time_of_day": "specific time",
                        "duration": "estimated scene duration"
                    }},
                    "weather": {{
                        "conditions": ["weather details"],
                        "effects_needed": ["rain", "snow", etc]
                    }},
                    "props": {{
                        "set_dressing": ["required items"],
                        "hand_props": ["character props"],
                        "special_items": ["unique requirements"]
                    }},
                    "technical": {{
                        "camera": ["camera requirements"],
                        "sound": ["sound requirements"],
                        "special_equipment": ["any special needs"]
                    }}
                }}
            ],
            "global_requirements": {{
                "equipment": ["list of all unique equipment needed"],
                "props": ["list of all unique props needed"],
                "special_effects": ["list of all effects needed"]
            }}
        }}
        
        Scene data:
        {json.dumps(scene_data, indent=2)}
        """
        
        logger.info("Sending scene data to agent for metadata extraction")
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received metadata response from agent")
            
            try:
                # Clean the response first
                cleaned_response = self._clean_json_response(result.final_output)
                logger.info("Cleaned response for JSON parsing")
                
                # Try to parse the JSON response
                metadata = json.loads(cleaned_response)
                logger.info("Successfully parsed metadata JSON response")
                
                # Validate the metadata structure
                if not isinstance(metadata, dict):
                    raise ValueError("Metadata response is not a dictionary")
                if "scene_metadata" not in metadata:
                    raise ValueError("Metadata missing 'scene_metadata' key")
                if not isinstance(metadata["scene_metadata"], list):
                    raise ValueError("'scene_metadata' is not a list")
                
                logger.info(f"Successfully extracted metadata for {len(metadata['scene_metadata'])} scenes")
                
                # Add formatted text representation
                metadata["formatted_text"] = self.format_metadata(metadata)
                
                return metadata
                
            except json.JSONDecodeError as e:
                logger.error(f"Metadata JSON parsing error: {str(e)}")
                logger.error(f"Raw metadata response: {result.final_output}")
                return {
                    "error": "Failed to parse metadata into valid JSON format",
                    "details": str(e),
                    "raw_response": result.final_output[:500],
                    "formatted_text": "Error: Failed to parse metadata"
                }
            except ValueError as e:
                logger.error(f"Metadata validation error: {str(e)}")
                return {
                    "error": f"Invalid metadata structure: {str(e)}",
                    "raw_response": result.final_output[:500],
                    "formatted_text": f"Error: Invalid metadata structure - {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Metadata extraction error: {str(e)}")
            return {
                "error": f"Error extracting metadata: {str(e)}",
                "formatted_text": f"Error: Failed to extract metadata - {str(e)}"
            } 