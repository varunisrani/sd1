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
            },
            "scene_presence": [
                {
                    "scene": "scene_number",
                    "presence_type": "type",
                    "dialogue_count": 0,
                    "action_count": 0,
                    "importance_score": 0.0
                }
            ],
            "objectives": {
                "main_objective": "objective",
                "scene_objectives": [
                    {
                        "scene": "scene_number",
                        "objective": "objective",
                        "obstacles": ["obstacle1"],
                        "outcome": "outcome"
                    }
                ]
            }
        }
    },
    "relationships": {
        "Character1-Character2": {
            "relationship_type": "type",
            "dynamics": ["dynamic1"],
            "evolution": [
                {
                    "scene": "scene_number",
                    "dynamic_change": "change",
                    "trigger": "trigger"
                }
            ],
            "interactions": [
                {
                    "scene": "scene_number",
                    "type": "interaction_type",
                    "description": "description",
                    "emotional_impact": "impact"
                }
            ],
            "conflict_points": [
                {
                    "scene": "scene_number",
                    "conflict": "description",
                    "resolution": "resolution"
                }
            ]
        }
    },
    "scene_matrix": {
        "scene_number": {
            "present_characters": ["char1"],
            "interactions": [
                {
                    "characters": ["char1", "char2"],
                    "type": "interaction_type",
                    "significance": 0.0
                }
            ],
            "emotional_atmosphere": "atmosphere",
            "key_developments": ["development1"]
        }
    }
}'''
        
        prompt = f"""Perform deep analysis of character dialogues and interactions to:
        - Analyze dialogue patterns, style, and emotional markers
        - Map character actions and interactions
        - Track emotional journey and intensity
        - Identify scene presence and importance
        - Define character objectives and obstacles
        - Map relationship dynamics and evolution
        - Create detailed scene interaction matrix
        
        For each character, analyze:
        - Dialogue style and patterns
        - Action sequences and emotional context
        - Scene presence and importance
        - Objectives and obstacles
        - Relationship dynamics
        
        For relationships, track:
        - Dynamic changes over time
        - Interaction patterns
        - Conflict points and resolutions
        
        IMPORTANT: Return the data in this exact JSON format:
        {json_format}
        
        Scene Data:
        {json.dumps(scene_data, indent=2)}
        """
        
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received response from agent")
            
            try:
                cleaned_response = self._clean_response(result.final_output)
                logger.debug(f"Cleaned response: {cleaned_response[:200]}...")
                
                analysis = json.loads(cleaned_response)
                logger.info("Successfully parsed JSON response")
                
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