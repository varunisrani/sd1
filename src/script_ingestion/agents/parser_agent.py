from agents import Agent, Runner
from typing import Dict, Any
import json
import logging
import re
from ...base_config import AGENT_INSTRUCTIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScriptParserAgent:
    def __init__(self):
        self.agent = Agent(
            name="Script Parser",
            instructions=AGENT_INSTRUCTIONS["script_parser"]
        )
        logger.info("ScriptParserAgent initialized")
    
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
    
    def format_scene_data(self, parsed_data: Dict[str, Any]) -> str:
        """Format parsed scene data into readable text."""
        if "error" in parsed_data:
            return f"Error: {parsed_data['error']}"
            
        output = []
        scenes = parsed_data.get("scenes", [])
        
        for scene in scenes:
            # Scene header
            scene_text = [
                f"\n{'='*80}\n",
                f"SCENE {scene['scene_number']}",
                f"{scene['location']['type']}. {scene['location']['place']} - {scene['time']}",
                f"{'-'*80}\n"
            ]
            
            # Scene description
            scene_text.append(f"Description:\n{scene['description']}\n")
            
            # Dialogues
            if scene.get('dialogues'):
                scene_text.append("\nDialogue:")
                for dialogue in scene['dialogues']:
                    char_line = f"{dialogue['character']}"
                    if dialogue.get('parenthetical'):
                        char_line += f" {dialogue['parenthetical']}"
                    scene_text.append(char_line)
                    scene_text.append(f"    \"{dialogue['line']}\"\n")
            
            # Transitions
            if scene.get('transitions'):
                scene_text.append(f"\nTransitions: {', '.join(scene['transitions'])}")
            
            output.extend(scene_text)
        
        return "\n".join(output)
    
    async def parse_script(self, script_text: str) -> Dict[str, Any]:
        """Parse the script and return structured scene data."""
        logger.info("Starting script parsing")
        
        if not script_text:
            logger.error("Empty script text received")
            return {"error": "Script text cannot be empty"}
        
        logger.info(f"Processing script of length: {len(script_text)} characters")
        
        prompt = f"""Analyze this script and break it down into scenes. For each scene, identify:
        - Scene number
        - Location (INT/EXT)
        - Time of day
        - Description
        - Dialogues
        - Transitions
        
        Return the data in this exact JSON format:
        {{
            "scenes": [
                {{
                    "scene_number": "1",
                    "location": {{
                        "type": "INT/EXT",
                        "place": "location description"
                    }},
                    "time": "time of day",
                    "description": "scene description",
                    "dialogues": [
                        {{
                            "character": "CHARACTER NAME",
                            "line": "dialogue text",
                            "parenthetical": "(optional direction)"
                        }}
                    ],
                    "transitions": ["CUT TO", "FADE OUT", etc]
                }}
            ]
        }}
        
        Script to analyze:
        {script_text}
        """
        
        logger.info("Sending script to agent for processing")
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received response from agent")
            
            try:
                # Clean the response first
                cleaned_response = self._clean_json_response(result.final_output)
                logger.info("Cleaned response for JSON parsing")
                
                # Try to parse the JSON response
                parsed_data = json.loads(cleaned_response)
                logger.info("Successfully parsed JSON response")
                
                # Validate the structure
                if not isinstance(parsed_data, dict):
                    raise ValueError("Response is not a dictionary")
                if "scenes" not in parsed_data:
                    raise ValueError("Response missing 'scenes' key")
                if not isinstance(parsed_data["scenes"], list):
                    raise ValueError("'scenes' is not a list")
                
                logger.info(f"Successfully parsed {len(parsed_data['scenes'])} scenes")
                
                # Add formatted text representation
                parsed_data["formatted_text"] = self.format_scene_data(parsed_data)
                
                return parsed_data
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                logger.error(f"Raw response: {result.final_output}")
                return {
                    "error": "Failed to parse script into valid JSON format",
                    "details": str(e),
                    "raw_response": result.final_output[:500],
                    "formatted_text": "Error: Failed to parse script data"
                }
            except ValueError as e:
                logger.error(f"Validation error: {str(e)}")
                return {
                    "error": f"Invalid response structure: {str(e)}",
                    "raw_response": result.final_output[:500],
                    "formatted_text": f"Error: Invalid script data structure - {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            return {
                "error": f"Error processing script: {str(e)}",
                "formatted_text": f"Error: Failed to process script - {str(e)}"
            } 