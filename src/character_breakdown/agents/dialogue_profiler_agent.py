from agents import Agent, Runner
from typing import Dict, Any, List
import json
import logging
from ...base_config import AGENT_INSTRUCTIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DialogueProfilerAgent:
    def __init__(self):
        self.agent = Agent(
            name="Dialogue Profiler",
            instructions=AGENT_INSTRUCTIONS["dialogue_profiler"]
        )
        logger.info("Initialized DialogueProfilerAgent")
    
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
    
    async def analyze_characters(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze character dialogues, relationships, and emotional arcs."""
        # Define expected JSON format
        json_format = '''
{
    "characters": {
        "Character Name": {
            "appearances": [
                {
                    "scene": "scene_number",
                    "dialogue_count": 0,
                    "word_count": 0,
                    "emotional_state": "state"
                }
            ],
            "objectives": ["objective1", "objective2"],
            "obstacles": ["obstacle1", "obstacle2"]
        }
    },
    "relationships": {
        "Character1-Character2": {
            "type": "relationship_type",
            "scenes": ["scene1", "scene2"],
            "dynamics": ["dynamic1", "dynamic2"]
        }
    }
}'''
        
        prompt = f"""Analyze character dialogues and interactions to:
        - Map emotional arcs and relationship dynamics
        - Calculate screen time and dialogue distribution
        - Identify character development patterns
        - Track relationships and conflicts
        
        For each character, provide:
        - Emotional journey through scenes
        - Key relationships and dynamics
        - Character objectives and obstacles
        - Dialogue patterns and style
        
        IMPORTANT: Return the data in this exact JSON format:
        {json_format}
        
        Scene Data:
        {json.dumps(scene_data, indent=2)}
        """
        
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received response from agent")
            
            try:
                # Clean the response before parsing JSON
                cleaned_response = self._clean_response(result.final_output)
                logger.debug(f"Cleaned response: {cleaned_response[:200]}...")
                
                analysis = json.loads(cleaned_response)
                logger.info("Successfully parsed JSON response")
                
                # Process and validate the analysis
                processed_analysis = self._process_analysis(analysis)
                logger.info("Successfully processed character analysis")
                
                return processed_analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.debug(f"Raw response: {result.final_output}")
                raise ValueError(f"Failed to generate valid character analysis: {str(e)}\nRaw response: {result.final_output[:200]}...")
                
        except Exception as e:
            logger.error(f"Error in character analysis: {str(e)}")
            raise ValueError(f"Failed to process character analysis: {str(e)}")
    
    def _process_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate character analysis data."""
        processed = {
            "characters": {},
            "relationships": {},
            "screen_time": {},
            "emotional_arcs": {},
            "statistics": {}
        }
        
        # Process character data
        if "characters" in analysis:
            for char_name, char_data in analysis["characters"].items():
                char_profile = {
                    "scenes": [],
                    "dialogue_count": 0,
                    "word_count": 0,
                    "emotional_states": [],
                    "objectives": [],
                    "obstacles": []
                }
                
                # Track scenes and dialogue
                if "appearances" in char_data:
                    for appearance in char_data["appearances"]:
                        scene_num = appearance["scene"]
                        char_profile["scenes"].append(scene_num)
                        char_profile["dialogue_count"] += appearance.get("dialogue_count", 0)
                        char_profile["word_count"] += appearance.get("word_count", 0)
                        
                        if "emotional_state" in appearance:
                            char_profile["emotional_states"].append({
                                "scene": scene_num,
                                "state": appearance["emotional_state"]
                            })
                
                # Track objectives and obstacles
                if "objectives" in char_data:
                    char_profile["objectives"] = char_data["objectives"]
                if "obstacles" in char_data:
                    char_profile["obstacles"] = char_data["obstacles"]
                
                processed["characters"][char_name] = char_profile
        
        # Process relationships
        if "relationships" in analysis:
            processed["relationships"] = analysis["relationships"]
        
        # Calculate screen time
        total_scenes = len(set(
            scene for char in processed["characters"].values()
            for scene in char["scenes"]
        ))
        
        for char_name, char_data in processed["characters"].items():
            processed["screen_time"][char_name] = {
                "scene_count": len(char_data["scenes"]),
                "scene_percentage": len(char_data["scenes"]) / total_scenes if total_scenes > 0 else 0,
                "dialogue_count": char_data["dialogue_count"],
                "word_count": char_data["word_count"]
            }
        
        # Generate statistics
        processed["statistics"] = {
            "total_scenes": total_scenes,
            "total_characters": len(processed["characters"]),
            "total_relationships": len(processed["relationships"]),
            "total_dialogue_count": sum(
                char["dialogue_count"] for char in processed["characters"].values()
            ),
            "total_word_count": sum(
                char["word_count"] for char in processed["characters"].values()
            )
        }
        
        return processed 