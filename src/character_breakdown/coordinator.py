from typing import Dict, Any, List
import json
import asyncio
from .agents.dialogue_profiler_agent import DialogueProfilerAgent
from .agents.attribute_mapper_agent import AttributeMapperAgent

class CharacterBreakdownCoordinator:
    def __init__(self):
        self.dialogue_profiler = DialogueProfilerAgent()
        self.attribute_mapper = AttributeMapperAgent()
        
    async def process_script(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process script data to generate comprehensive character breakdowns."""
        try:
            # Step 1: Analyze character dialogues and relationships
            character_analysis = await self.dialogue_profiler.analyze_characters(scene_data)
            
            # Step 2: Map physical attributes and track evolution
            attribute_mapping = await self.attribute_mapper.map_attributes(
                character_analysis,
                scene_data
            )
            
            # Step 3: Combine and process results
            breakdown = self._combine_results(character_analysis, attribute_mapping)
            
            return breakdown
        except Exception as e:
            raise RuntimeError(f"Failed to process character breakdown: {str(e)}")
    
    def _combine_results(
        self,
        character_analysis: Dict[str, Any],
        attribute_mapping: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine and process results from both agents."""
        combined = {
            "characters": {},
            "relationships": character_analysis.get("relationships", {}),
            "statistics": character_analysis.get("statistics", {}),
            "props_inventory": attribute_mapping.get("props_inventory", {}),
            "makeup_requirements": attribute_mapping.get("makeup_requirements", {}),
            "continuity_notes": attribute_mapping.get("continuity_notes", [])
        }
        
        # Merge character data
        all_characters = set(character_analysis.get("characters", {}).keys()) | \
                        set(attribute_mapping.get("characters", {}).keys())
        
        for char_name in all_characters:
            char_profile = {
                # Dialogue and relationship data
                "dialogue_stats": character_analysis.get("screen_time", {}).get(char_name, {}),
                "emotional_journey": [],
                "objectives": [],
                "obstacles": [],
                
                # Physical and visual data
                "physical_attributes": {},
                "costume_data": {},
                "props": [],
                "makeup": {},
                "evolution_timeline": []
            }
            
            # Get character data from dialogue analysis
            if char_name in character_analysis.get("characters", {}):
                char_data = character_analysis["characters"][char_name]
                char_profile.update({
                    "emotional_journey": char_data.get("emotional_states", []),
                    "objectives": char_data.get("objectives", []),
                    "obstacles": char_data.get("obstacles", [])
                })
            
            # Get character data from attribute mapping
            if char_name in attribute_mapping.get("characters", {}):
                char_data = attribute_mapping["characters"][char_name]
                char_profile.update({
                    "physical_attributes": char_data.get("physical_attributes", {}),
                    "costume_data": {
                        "base": char_data.get("costume_base", {}),
                        "changes": char_data.get("scene_specific_changes", [])
                    },
                    "props": char_data.get("props_base", []),
                    "makeup": char_data.get("makeup_base", {})
                })
            
            # Get evolution timeline
            if char_name in attribute_mapping.get("timelines", {}):
                char_profile["evolution_timeline"] = attribute_mapping["timelines"][char_name]
            
            combined["characters"][char_name] = char_profile
        
        # Add metadata
        combined["metadata"] = {
            "total_characters": len(combined["characters"]),
            "total_relationships": len(combined["relationships"]),
            "total_props": len(combined["props_inventory"]),
            "total_costume_changes": sum(
                len(char["costume_data"]["changes"])
                for char in combined["characters"].values()
            ),
            "total_makeup_requirements": len(combined["makeup_requirements"])
        }
        
        return combined 