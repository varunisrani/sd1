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
            "physical": {
                "height": "height_description",
                "build": "build_description",
                "age": "age_description",
                "features": ["feature1", "feature2"]
            },
            "costume": {
                "base": {
                    "item": "description"
                }
            },
            "props": {
                "base": ["prop1", "prop2"]
            },
            "makeup": {
                "base": {
                    "item": "description"
                }
            },
            "scenes": [
                {
                    "scene": "scene_number",
                    "costume_changes": {},
                    "prop_changes": [],
                    "makeup_changes": {},
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
                "changes": ["change1", "change2"]
            }
        ]
    },
    "props": {
        "prop_name": {
            "quantity": 1,
            "scenes": ["scene1", "scene2"],
            "characters": ["char1", "char2"],
            "requirements": ["req1", "req2"]
        }
    },
    "makeup": {
        "character": {
            "base": {},
            "special_effects": []
        }
    },
    "continuity": [
        "note1",
        "note2"
    ]
}'''
        
        prompt = f"""Analyze character appearances and create detailed profiles including:
        - Physical attributes and descriptions
        - Costume and wardrobe requirements
        - Props and personal items
        - Character evolution timeline
        - Makeup and special effects needs
        
        Track changes and continuity across scenes.
        
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
                # Clean the response before parsing JSON
                cleaned_response = self._clean_response(result.final_output)
                logger.debug(f"Cleaned response: {cleaned_response[:200]}...")
                
                mapping = json.loads(cleaned_response)
                logger.info("Successfully parsed JSON response")
                
                # Process and validate the mapping
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
            "continuity_notes": []
        }
        
        if "characters" in mapping:
            for char_name, char_data in mapping["characters"].items():
                char_profile = {
                    "physical_attributes": {},
                    "costume_base": {},
                    "props_base": [],
                    "makeup_base": {},
                    "scene_specific_changes": []
                }
                
                # Process physical attributes
                if "physical" in char_data:
                    char_profile["physical_attributes"] = {
                        "height": char_data["physical"].get("height"),
                        "build": char_data["physical"].get("build"),
                        "age": char_data["physical"].get("age"),
                        "distinguishing_features": char_data["physical"].get("features", [])
                    }
                
                # Process base costume and props
                if "costume" in char_data:
                    char_profile["costume_base"] = char_data["costume"].get("base", {})
                if "props" in char_data:
                    char_profile["props_base"] = char_data["props"].get("base", [])
                if "makeup" in char_data:
                    char_profile["makeup_base"] = char_data["makeup"].get("base", {})
                
                # Process scene-specific changes
                if "scenes" in char_data:
                    for scene in char_data["scenes"]:
                        scene_changes = {
                            "scene_number": scene["scene"],
                            "costume_changes": scene.get("costume_changes", {}),
                            "prop_changes": scene.get("prop_changes", []),
                            "makeup_changes": scene.get("makeup_changes", {}),
                            "notes": scene.get("notes", [])
                        }
                        char_profile["scene_specific_changes"].append(scene_changes)
                
                processed["characters"][char_name] = char_profile
        
        # Process timelines
        if "timelines" in mapping:
            for char_name, timeline in mapping["timelines"].items():
                processed["timelines"][char_name] = sorted(
                    timeline,
                    key=lambda x: (x.get("scene_number", 0), x.get("sequence", 0))
                )
        
        # Generate props inventory
        if "props" in mapping:
            for prop, details in mapping["props"].items():
                processed["props_inventory"][prop] = {
                    "quantity": details.get("quantity", 1),
                    "scenes_needed": details.get("scenes", []),
                    "characters": details.get("characters", []),
                    "special_requirements": details.get("requirements", [])
                }
        
        # Process makeup requirements
        if "makeup" in mapping:
            processed["makeup_requirements"] = mapping["makeup"]
        
        # Process continuity notes
        if "continuity" in mapping:
            processed["continuity_notes"] = mapping["continuity"]
        
        return processed 