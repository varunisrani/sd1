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
        
        # Define the JSON format template with new fields
        json_format = '''
{
    "scenes": [
        {
            "scene_number": "1",
            "summary": "12-15 word summary of the scene",
            "story_thread": "Main plot thread this scene belongs to",
            "emotional_tone": "Overall emotional tone of the scene",
            "key_elements": ["list", "of", "key", "elements"],
            "department_focus": {
                "camera": "Camera department notes",
                "lighting": "Lighting department notes",
                "sound": "Sound department notes",
                "art": "Art department notes"
            },
            "characters": {
                "Character Name": {
                    "arc_point": "Description of character's arc in this scene",
                    "emotional_state": "Character's emotional state",
                    "motivation": "Character's motivation in scene"
                }
            },
            "approval_status": "pending",
            "last_modified_by": null,
            "review_notes": []
        }
    ]
}'''
        
        # Construct the enhanced prompt
        prompt = (
            "Create concise 12-15 word summaries for each scene that:\n"
            "- Capture essential dramatic elements\n"
            "- Maintain story progression\n"
            "- Use consistent tone and style\n"
            "- Link related story elements\n"
            "- Include emotional tone analysis\n"
            "- Identify key technical elements\n"
            "- Specify department-specific focus areas\n\n"
            "For each scene, analyze and include:\n"
            "- Overall emotional tone\n"
            "- Key story elements and beats\n"
            "- Technical requirements per department\n"
            "- Character emotional states and motivations\n"
            "- Visual and technical highlights\n\n"
            f"Expected JSON format:\n{json_format}\n\n"
            f"Scene Data:\n{json.dumps(scene_data, indent=2)}"
        )
        
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received response from agent")
            
            try:
                cleaned_response = self._clean_response(result.final_output)
                logger.debug(f"Cleaned response: {cleaned_response[:200]}...")
                
                summaries = json.loads(cleaned_response)
                logger.info("Successfully parsed JSON response")
                
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
        """Process and validate generated summaries with enhanced fields."""
        logger.info("Processing summaries")
        processed = {
            "summaries": [],
            "story_threads": {},
            "character_arcs": {},
            "emotional_journey": {},
            "department_insights": {
                "camera": [],
                "lighting": [],
                "sound": [],
                "art": []
            },
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
            
            # Track emotional journey
            if "emotional_tone" in scene:
                processed["emotional_journey"][scene_num] = scene["emotional_tone"]
            
            # Track department insights
            if "department_focus" in scene:
                for dept, notes in scene["department_focus"].items():
                    if dept in processed["department_insights"]:
                        processed["department_insights"][dept].append({
                            "scene": scene_num,
                            "notes": notes
                        })
            
            # Track character arcs
            if "characters" in scene:
                for char, data in scene["characters"].items():
                    if char not in processed["character_arcs"]:
                        processed["character_arcs"][char] = []
                    processed["character_arcs"][char].append({
                        "scene": scene["scene_number"],
                        "arc_point": data.get("arc_point", ""),
                        "emotional_state": data.get("emotional_state", ""),
                        "motivation": data.get("motivation", "")
                    })
            
            # Add processed scene to summaries
            processed["summaries"].append(scene)
        
        logger.info(f"Processed {len(processed['summaries'])} scenes with {len(processed['warnings'])} warnings")
        return processed 