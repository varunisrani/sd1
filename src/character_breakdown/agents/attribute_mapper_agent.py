from agents import Agent, Runner
from typing import Dict, Any, List
import json
import logging
from datetime import datetime
from ...base_config import AGENT_INSTRUCTIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AttributeMapperAgent:
    def __init__(self):
        self.agent = Agent(
            name="Attribute Mapper",
            instructions=AGENT_INSTRUCTIONS["attribute_mapper"]
        )
        logger.info("Initialized AttributeMapperAgent")
    
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
    
    async def map_attributes(
        self,
        character_analysis: Dict[str, Any],
        scene_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map physical attributes and track character evolution."""
        # Define expected JSON format
        json_format = '''
{
    "characters": {
        "Character Name": {
            "basic_info": {
                "name": "character_name",
                "role_type": "role_description",
                "significance_score": 0.0
            },
            "physical": {
                "height": "height_description",
                "build": "build_description",
                "age": "age_description",
                "features": ["feature1", "feature2"]
            },
            "costume": {
                "base": {
                    "item": "description"
                },
                "timeline": [
                    {
                        "scene": "scene_number",
                        "changes": {"item": "description"},
                        "notes": "costume_notes"
                    }
                ]
            },
            "props": {
                "base": ["prop1", "prop2"],
                "timeline": [
                    {
                        "scene": "scene_number",
                        "additions": ["prop1"],
                        "removals": ["prop2"]
                    }
                ]
            },
            "makeup": {
                "base": {
                    "item": "description"
                },
                "timeline": [
                    {
                        "scene": "scene_number",
                        "changes": {"item": "description"},
                        "special_effects": ["effect1"]
                    }
                ]
            },
            "casting": {
                "requirements": ["requirement1"],
                "notes": "casting_notes",
                "audition_sides": ["scene1", "scene2"]
            },
            "scenes": [
                {
                    "scene": "scene_number",
                    "sequence": 1,
                    "importance": 0.0,
                    "notes": []
                }
            ]
        }
    },
    "timelines": {
        "Character Name": [
            {
                "scene_number": "1",
                "sequence": 1,
                "changes": ["change1"],
                "significance": 0.0
            }
        ]
    },
    "props_inventory": {
        "prop_name": {
            "quantity": 1,
            "scenes": ["scene1"],
            "characters": ["char1"],
            "requirements": ["req1"]
        }
    },
    "makeup_requirements": {
        "character": {
            "base": {},
            "special_effects": [],
            "scene_specific": {}
        }
    },
    "continuity_notes": [
        {
            "scene": "scene_number",
            "note": "continuity_note",
            "affected_characters": ["char1"]
        }
    ]
}'''
        
        prompt = f"""Analyze character appearances and create detailed profiles including:
        - Basic information and role significance
        - Physical attributes and descriptions
        - Costume and wardrobe requirements with timeline
        - Props and personal items with usage timeline
        - Character evolution timeline
        - Makeup and special effects needs with timeline
        - Casting requirements and audition notes
        
        Track all changes and continuity across scenes.
        Calculate significance scores based on:
        - Number of scenes
        - Dialogue importance
        - Plot impact
        - Character relationships
        
        IMPORTANT: Return the data in this exact JSON format:
        {json_format}
        
        Character Analysis:
        {json.dumps(character_analysis, indent=2)}
        
        Scene Data:
        {json.dumps(scene_data, indent=2)}
        """
        
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received response from agent")
            
            try:
                cleaned_response = self._clean_response(result.final_output)
                logger.debug(f"Cleaned response: {cleaned_response[:200]}...")
                
                mapping = json.loads(cleaned_response)
                logger.info("Successfully parsed JSON response")
                
                processed_mapping = self._process_mapping(mapping)
                logger.info("Successfully processed attribute mapping")
                
                return processed_mapping
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.debug(f"Raw response: {result.final_output}")
                raise ValueError(f"Failed to generate valid attribute mapping: {str(e)}\nRaw response: {result.final_output[:200]}...")
                
        except Exception as e:
            logger.error(f"Error in attribute mapping: {str(e)}")
            raise ValueError(f"Failed to process attribute mapping: {str(e)}")
    
    def _process_mapping(self, mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate character attribute mapping."""
        processed = {
            "characters": {},
            "timelines": {},
            "costume_changes": {},
            "props_inventory": {},
            "makeup_requirements": {},
            "continuity_notes": [],
            "casting_requirements": {}
        }
        
        if "characters" in mapping:
            for char_name, char_data in mapping["characters"].items():
                char_profile = {
                    "basic_info": char_data.get("basic_info", {}),
                    "physical_attributes": char_data.get("physical", {}),
                    "costume_data": {
                        "base": char_data.get("costume", {}).get("base", {}),
                        "timeline": char_data.get("costume", {}).get("timeline", [])
                    },
                    "props": {
                        "base": char_data.get("props", {}).get("base", []),
                        "timeline": char_data.get("props", {}).get("timeline", [])
                    },
                    "makeup": {
                        "base": char_data.get("makeup", {}).get("base", {}),
                        "timeline": char_data.get("makeup", {}).get("timeline", [])
                    },
                    "casting": char_data.get("casting", {}),
                    "scene_appearances": sorted(
                        char_data.get("scenes", []),
                        key=lambda x: (int(x.get("scene", 0)), x.get("sequence", 0))
                    )
                }
                
                # Calculate additional metrics
                scenes = char_profile["scene_appearances"]
                char_profile["metrics"] = {
                    "total_scenes": len(scenes),
                    "importance_score": sum(scene.get("importance", 0) for scene in scenes) / len(scenes) if scenes else 0,
                    "costume_changes": len(char_profile["costume_data"]["timeline"]),
                    "prop_changes": len(char_profile["props"]["timeline"]),
                    "makeup_changes": len(char_profile["makeup"]["timeline"])
                }
                
                processed["characters"][char_name] = char_profile
        
        # Process timelines
        if "timelines" in mapping:
            processed["timelines"] = {
                char: sorted(timeline, key=lambda x: (int(x["scene_number"]), x.get("sequence", 0)))
                for char, timeline in mapping["timelines"].items()
            }
        
        # Process props inventory
        if "props_inventory" in mapping:
            processed["props_inventory"] = mapping["props_inventory"]
        
        # Process makeup requirements
        if "makeup_requirements" in mapping:
            processed["makeup_requirements"] = mapping["makeup_requirements"]
        
        # Process continuity notes
        if "continuity_notes" in mapping:
            processed["continuity_notes"] = sorted(
                mapping["continuity_notes"],
                key=lambda x: int(x.get("scene", 0))
            )
        
        return processed 