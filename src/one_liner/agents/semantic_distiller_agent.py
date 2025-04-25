import logging
from agents import Agent, Runner
from typing import Dict, Any, List
import json
from ...base_config import AGENT_INSTRUCTIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SemanticDistillerAgent:
    def __init__(self):
        self.agent = Agent(
            name="Semantic Distiller",
            instructions=AGENT_INSTRUCTIONS["semantic_distiller"]
        )
        logger.info("Initialized SemanticDistillerAgent")
    
    def _clean_response(self, response: str) -> str:
        """Clean the response by removing markdown code block markers."""
        # Remove ```json or ``` markers from start and end
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        return response.strip()
    
    async def generate_summaries(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate concise summaries for each scene while maintaining narrative continuity."""
        if not scene_data:
            logger.error("Empty scene data provided")
            raise ValueError("No scene data provided")
            
        logger.info(f"Generating summaries for {len(scene_data.get('scenes', []))} scenes")
        
        # Define the JSON format template separately
        json_format = '''
{
    "scenes": [
        {
            "scene_number": "1",
            "summary": "12-15 word summary of the scene",
            "story_thread": "Main plot thread this scene belongs to",
            "characters": {
                "Character Name": {
                    "arc_point": "Description of character's arc in this scene",
                    "emotional_state": "Character's emotional state"
                }
            }
        }
    ]
}'''
        
        # Construct the prompt using string concatenation
        prompt = (
            "Create concise 12-15 word summaries for each scene that:\n"
            "- Capture essential dramatic elements\n"
            "- Maintain story progression\n"
            "- Use consistent tone and style\n"
            "- Link related story elements\n\n"
            "For each scene, include:\n"
            "- Key story beats\n"
            "- Character arcs\n"
            "- Emotional transitions\n"
            "- Visual highlights\n\n"
            f"Expected JSON format:\n{json_format}\n\n"
            f"Scene Data:\n{json.dumps(scene_data, indent=2)}"
        )
        
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received response from agent")
            
            try:
                # Clean the response before parsing JSON
                cleaned_response = self._clean_response(result.final_output)
                logger.debug(f"Cleaned response: {cleaned_response[:200]}...")
                
                summaries = json.loads(cleaned_response)
                logger.info("Successfully parsed JSON response")
                
                # Validate and process summaries
                processed_summaries = self._process_summaries(summaries)
                logger.info("Successfully processed summaries")
                
                return processed_summaries
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.debug(f"Raw response: {result.final_output}")
                raise ValueError(f"Failed to generate valid summary data: {str(e)}\nRaw response: {result.final_output[:200]}...")
                
        except Exception as e:
            logger.error(f"Error generating summaries: {str(e)}")
            raise ValueError(f"Error generating summaries: {str(e)}")
    
    def _process_summaries(self, summaries: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate generated summaries."""
        logger.info("Processing summaries")
        processed = {
            "summaries": [],
            "story_threads": {},
            "character_arcs": {},
            "warnings": []
        }
        
        if "scenes" not in summaries:
            logger.error("Missing 'scenes' key in summaries")
            raise ValueError("Missing scene summaries in output")
        
        # Process each scene summary
        for scene in summaries["scenes"]:
            scene_num = scene.get("scene_number", "unknown")
            logger.debug(f"Processing scene {scene_num}")
            
            # Validate summary length
            if "summary" in scene:
                words = len(scene["summary"].split())
                if words < 12 or words > 15:
                    warning = f"Scene {scene_num}: Summary length ({words} words) outside 12-15 word range"
                    logger.warning(warning)
                    processed["warnings"].append(warning)
            else:
                warning = f"Scene {scene_num}: Missing summary"
                logger.warning(warning)
                processed["warnings"].append(warning)
            
            # Track story threads
            if "story_thread" in scene:
                thread = scene["story_thread"]
                if thread not in processed["story_threads"]:
                    processed["story_threads"][thread] = []
                processed["story_threads"][thread].append(scene["scene_number"])
            else:
                warning = f"Scene {scene_num}: Missing story thread"
                logger.warning(warning)
                processed["warnings"].append(warning)
            
            # Track character arcs
            if "characters" in scene:
                for char in scene["characters"]:
                    if char not in processed["character_arcs"]:
                        processed["character_arcs"][char] = []
                    processed["character_arcs"][char].append({
                        "scene": scene["scene_number"],
                        "arc_point": scene["characters"][char].get("arc_point", ""),
                        "emotional_state": scene["characters"][char].get("emotional_state", "")
                    })
            else:
                warning = f"Scene {scene_num}: Missing character data"
                logger.warning(warning)
                processed["warnings"].append(warning)
            
            # Add processed scene to summaries
            processed["summaries"].append(scene)
        
        logger.info(f"Processed {len(processed['summaries'])} scenes with {len(processed['warnings'])} warnings")
        return processed 