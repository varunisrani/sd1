from agents import Agent, Runner
from typing import Dict, Any, List
import json
import logging
from ...base_config import AGENT_INSTRUCTIONS
import re

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
        """Clean the response by removing markdown code block markers and extract JSON."""
        try:
            response = response.strip()
            
            # Try to find JSON between triple backticks
            json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
            matches = re.findall(json_pattern, response)
            if matches:
                return matches[0].strip()
            
            # Try to find JSON between single backticks
            single_tick_pattern = r"`([\s\S]*?)`"
            matches = re.findall(single_tick_pattern, response)
            if matches:
                return matches[0].strip()
            
            # Try to find anything that looks like a JSON object
            json_object_pattern = r"(\{[\s\S]*\})"
            matches = re.findall(json_object_pattern, response)
            if matches:
                return matches[0].strip()
            
            # If no JSON found, return the original response
            return response.strip()
        except Exception as e:
            logger.error(f"Error cleaning response: {str(e)}")
            return response.strip()

    def _create_fallback_analysis(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a basic valid analysis when JSON parsing fails."""
        logger.info("Creating fallback character analysis")
        
        # Extract characters from scene data
        characters = set()
        scenes = scene_data.get("scenes", [])
        if not scenes and "parsed_data" in scene_data:
            scenes = scene_data["parsed_data"].get("scenes", [])
        
        for scene in scenes:
            if isinstance(scene, dict):
                # Extract from dialogues
                for dialogue in scene.get("dialogues", []):
                    if isinstance(dialogue, dict):
                        char_name = dialogue.get("character")
                        if char_name:
                            characters.add(char_name)
        
        # Create basic analysis structure
        analysis = {
            "characters": {},
            "relationships": {},
            "scene_matrix": {},
            "statistics": {
                "total_characters": len(characters),
                "total_scenes": len(scenes)
            }
        }
        
        # Add basic character data
        for char_name in characters:
            analysis["characters"][char_name] = {
                "dialogue_analysis": {
                    "total_lines": 0,
                    "total_words": 0,
                    "patterns": {"common_phrases": [], "emotional_markers": []}
                },
                "action_sequences": [],
                "emotional_range": {
                    "primary_emotion": "neutral",
                    "emotional_spectrum": ["neutral"],
                    "emotional_journey": []
                },
                "scene_presence": [],
                "objectives": {"main_objective": "Unknown", "scene_objectives": []}
            }
        
        # Add basic scene matrix
        for i, scene in enumerate(scenes):
            scene_id = str(i + 1)
            analysis["scene_matrix"][scene_id] = {
                "present_characters": list(characters),
                "interactions": [],
                "emotional_atmosphere": "neutral",
                "key_developments": []
            }
        
        return analysis

    async def analyze_characters(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze character dialogues, relationships, and emotional arcs."""
        try:
            result = await Runner.run(self.agent, self._generate_analysis_prompt(scene_data))
            logger.info("Received response from agent")
            
            try:
                cleaned_response = self._clean_response(result.final_output)
                logger.debug(f"Cleaned response: {cleaned_response[:200]}...")
                
                try:
                    analysis = json.loads(cleaned_response)
                    logger.info("Successfully parsed JSON response")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response, using fallback: {str(e)}")
                    analysis = self._create_fallback_analysis(scene_data)
                
                processed_analysis = self._process_analysis(analysis)
                logger.info("Successfully processed character analysis")
                
                return processed_analysis
                
            except Exception as e:
                logger.error(f"Error processing response: {str(e)}")
                logger.debug(f"Raw response: {result.final_output}")
                return self._create_fallback_analysis(scene_data)
                
        except Exception as e:
            logger.error(f"Error in character analysis: {str(e)}")
            return self._create_fallback_analysis(scene_data)

    def _generate_analysis_prompt(self, scene_data: Dict[str, Any]) -> str:
        """Generate the analysis prompt with clear JSON format instructions."""
        json_format = '''
{
    "characters": {
        "Character Name": {
            "dialogue_analysis": {
                "total_lines": 0,
                "total_words": 0,
                "average_line_length": 0.0,
                "vocabulary_complexity": 0.0,
                "patterns": {
                    "common_phrases": ["phrase1"],
                    "speech_style": "description",
                    "emotional_markers": ["marker1"]
                }
            },
            "action_sequences": [
                {
                    "scene": "scene_number",
                    "sequence": "action_description",
                    "interaction_type": "type",
                    "emotional_context": "context"
                }
            ],
            "emotional_range": {
                "primary_emotion": "emotion",
                "emotional_spectrum": ["emotion1", "emotion2"],
                "emotional_journey": [
                    {
                        "scene": "scene_number",
                        "emotion": "emotion",
                        "intensity": 0.0,
                        "trigger": "trigger_description"
                    }
                ]
            }
        }
    },
    "relationships": {},
    "scene_matrix": {},
    "statistics": {}
}'''
        
        return f"""Analyze the provided scene data and generate a character analysis in the exact JSON format shown below.
        DO NOT include any explanatory text or markdown formatting.
        ONLY return the JSON object.
        
        Required JSON format:
        {json_format}
        
        Scene Data:
        {json.dumps(scene_data, indent=2)}"""
    
    def _process_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate character analysis data."""
        processed = {
            "characters": {},
            "relationships": {},
            "scene_matrix": {},
            "statistics": {
                "dialogue_stats": {},
                "emotional_stats": {},
                "relationship_stats": {},
                "scene_stats": {}
            }
        }
        
        # Process character data
        if "characters" in analysis:
            for char_name, char_data in analysis["characters"].items():
                char_profile = {
                    "dialogue_analysis": char_data.get("dialogue_analysis", {}),
                    "action_sequences": sorted(
                        char_data.get("action_sequences", []),
                        key=lambda x: int(x.get("scene", 0))
                    ),
                    "emotional_range": char_data.get("emotional_range", {}),
                    "scene_presence": sorted(
                        char_data.get("scene_presence", []),
                        key=lambda x: int(x.get("scene", 0))
                    ),
                    "objectives": char_data.get("objectives", {})
                }
                
                # Calculate dialogue statistics
                dialogue_stats = char_profile["dialogue_analysis"]
                if dialogue_stats:
                    processed["statistics"]["dialogue_stats"][char_name] = {
                        "total_lines": dialogue_stats.get("total_lines", 0),
                        "total_words": dialogue_stats.get("total_words", 0),
                        "average_line_length": dialogue_stats.get("average_line_length", 0),
                        "vocabulary_complexity": dialogue_stats.get("vocabulary_complexity", 0)
                    }
                
                # Calculate emotional statistics
                emotional_range = char_profile["emotional_range"]
                if emotional_range:
                    processed["statistics"]["emotional_stats"][char_name] = {
                        "primary_emotion": emotional_range.get("primary_emotion"),
                        "emotional_variety": len(emotional_range.get("emotional_spectrum", [])),
                        "average_intensity": sum(
                            point.get("intensity", 0)
                            for point in emotional_range.get("emotional_journey", [])
                        ) / len(emotional_range.get("emotional_journey", [])) if emotional_range.get("emotional_journey") else 0
                    }
                
                processed["characters"][char_name] = char_profile
        
        # Process relationships
        if "relationships" in analysis:
            for rel_key, rel_data in analysis["relationships"].items():
                processed["relationships"][rel_key] = {
                    "type": rel_data.get("relationship_type"),
                    "dynamics": rel_data.get("dynamics", []),
                    "evolution": sorted(
                        rel_data.get("evolution", []),
                        key=lambda x: int(x.get("scene", 0))
                    ),
                    "interactions": sorted(
                        rel_data.get("interactions", []),
                        key=lambda x: int(x.get("scene", 0))
                    ),
                    "conflicts": sorted(
                        rel_data.get("conflict_points", []),
                        key=lambda x: int(x.get("scene", 0))
                    )
                }
                
                # Calculate relationship statistics
                processed["statistics"]["relationship_stats"][rel_key] = {
                    "total_interactions": len(rel_data.get("interactions", [])),
                    "total_conflicts": len(rel_data.get("conflict_points", [])),
                    "dynamic_changes": len(rel_data.get("evolution", []))
                }
        
        # Process scene matrix
        if "scene_matrix" in analysis:
            processed["scene_matrix"] = {
                int(scene_num): scene_data
                for scene_num, scene_data in sorted(
                    analysis["scene_matrix"].items(),
                    key=lambda x: int(x[0])
                )
            }
            
            # Calculate scene statistics
            processed["statistics"]["scene_stats"] = {
                "total_scenes": len(processed["scene_matrix"]),
                "average_characters_per_scene": sum(
                    len(scene.get("present_characters", []))
                    for scene in processed["scene_matrix"].values()
                ) / len(processed["scene_matrix"]) if processed["scene_matrix"] else 0,
                "total_interactions": sum(
                    len(scene.get("interactions", []))
                    for scene in processed["scene_matrix"].values()
                )
            }
        
        return processed 