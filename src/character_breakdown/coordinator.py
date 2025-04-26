import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from .agents.attribute_mapper_agent import AttributeMapperAgent
from .agents.dialogue_profiler_agent import DialogueProfilerAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CharacterBreakdownCoordinator:
    def __init__(self, data_dir: str = "data"):
        """Initialize the coordinator with necessary agents and data paths."""
        self.data_dir = data_dir
        self.attribute_mapper = AttributeMapperAgent()
        self.dialogue_profiler = DialogueProfilerAgent()
        
        # Ensure required directories exist
        self.character_data_dir = os.path.join(data_dir, "character_profiles")
        self.relationship_data_dir = os.path.join(data_dir, "relationship_maps")
        self.scene_data_dir = os.path.join(data_dir, "scene_matrices")
        
        for directory in [self.character_data_dir, self.relationship_data_dir, self.scene_data_dir]:
            os.makedirs(directory, exist_ok=True)
        
        logger.info("Initialized CharacterBreakdownCoordinator")
    
    async def process_script(self, script_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process script data to generate comprehensive character breakdowns."""
        try:
            # Step 1: Initial dialogue and action analysis
            logger.info("Starting dialogue and action analysis")
            dialogue_analysis = await self.dialogue_profiler.analyze_characters(script_data)
            
            # Step 2: Map character attributes
            logger.info("Mapping character attributes")
            character_attributes = await self.attribute_mapper.map_attributes(
                script_data,
                dialogue_analysis["characters"]
            )
            
            # Step 3: Merge and process results
            logger.info("Merging analysis results")
            processed_data = self._merge_analysis_results(
                dialogue_analysis,
                character_attributes
            )
            
            # Step 4: Generate additional metrics
            logger.info("Generating additional metrics")
            processed_data = self._generate_metrics(processed_data)
            
            # Step 5: Save results
            logger.info("Saving analysis results")
            self._save_results(processed_data)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error in script processing: {str(e)}")
            raise ValueError(f"Failed to process script: {str(e)}")
    
    def _merge_analysis_results(
        self,
        dialogue_analysis: Dict[str, Any],
        character_attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge results from dialogue analysis and attribute mapping."""
        merged = {
            "characters": {},
            "relationships": dialogue_analysis.get("relationships", {}),
            "scene_matrix": dialogue_analysis.get("scene_matrix", {}),
            "statistics": {
                "dialogue_stats": dialogue_analysis.get("statistics", {}).get("dialogue_stats", {}),
                "emotional_stats": dialogue_analysis.get("statistics", {}).get("emotional_stats", {}),
                "relationship_stats": dialogue_analysis.get("statistics", {}).get("relationship_stats", {}),
                "scene_stats": dialogue_analysis.get("statistics", {}).get("scene_stats", {}),
                "technical_stats": {}
            }
        }
        
        # Merge character data
        for char_name in set(list(dialogue_analysis.get("characters", {}).keys()) +
                           list(character_attributes.get("characters", {}).keys())):
            dialogue_data = dialogue_analysis.get("characters", {}).get(char_name, {})
            attribute_data = character_attributes.get("characters", {}).get(char_name, {})
            
            merged["characters"][char_name] = {
                # Core analysis
                "dialogue_analysis": dialogue_data.get("dialogue_analysis", {}),
                "action_sequences": dialogue_data.get("action_sequences", []),
                "emotional_range": dialogue_data.get("emotional_range", {}),
                "scene_presence": dialogue_data.get("scene_presence", []),
                "objectives": dialogue_data.get("objectives", {}),
                
                # Technical aspects
                "costumes": attribute_data.get("costumes", []),
                "makeup": attribute_data.get("makeup", []),
                "props": attribute_data.get("props", []),
                
                # Casting
                "casting_requirements": attribute_data.get("casting_requirements", {}),
                "audition_notes": attribute_data.get("audition_notes", []),
                
                # Metrics
                "importance_score": attribute_data.get("importance_score", 0.0),
                "screen_time_percentage": attribute_data.get("screen_time_percentage", 0.0)
            }
        
        return merged
    
    def _generate_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate additional metrics from the merged analysis."""
        # Calculate technical statistics
        tech_stats = {
            "costume_changes": {},
            "prop_usage": {},
            "makeup_changes": {}
        }
        
        try:
            for char_name, char_data in data.get("characters", {}).items():
                # Initialize metrics for this character
                tech_stats["costume_changes"][char_name] = {"total_changes": 0, "unique_costumes": 0}
                tech_stats["prop_usage"][char_name] = {"total_props": 0, "unique_props": 0}
                tech_stats["makeup_changes"][char_name] = {"total_changes": 0, "unique_looks": 0}
                
                # Costume metrics
                costumes = char_data.get("costumes", [])
                if costumes and isinstance(costumes, list):
                    unique_costumes = set()
                    for costume in costumes:
                        if isinstance(costume, dict) and "description" in costume:
                            unique_costumes.add(costume["description"])
                    
                    tech_stats["costume_changes"][char_name] = {
                        "total_changes": len(costumes),
                        "unique_costumes": len(unique_costumes)
                    }
                
                # Prop metrics
                props = char_data.get("props", [])
                if props and isinstance(props, list):
                    unique_props = set()
                    for prop in props:
                        if isinstance(prop, dict) and "item" in prop:
                            unique_props.add(prop["item"])
                    
                    tech_stats["prop_usage"][char_name] = {
                        "total_props": len(props),
                        "unique_props": len(unique_props)
                    }
                
                # Makeup metrics
                makeup = char_data.get("makeup", [])
                if makeup and isinstance(makeup, list):
                    unique_looks = set()
                    for look in makeup:
                        if isinstance(look, dict) and "description" in look:
                            unique_looks.add(look["description"])
                    
                    tech_stats["makeup_changes"][char_name] = {
                        "total_changes": len(makeup),
                        "unique_looks": len(unique_looks)
                    }
            
            # Ensure statistics key exists
            if "statistics" not in data:
                data["statistics"] = {}
            
            data["statistics"]["technical_stats"] = tech_stats
            return data
            
        except Exception as e:
            logger.error(f"Error generating metrics: {str(e)}")
            # Return data without technical stats if there's an error
            if "statistics" not in data:
                data["statistics"] = {}
            data["statistics"]["technical_stats"] = {
                "costume_changes": {},
                "prop_usage": {},
                "makeup_changes": {},
                "error": str(e)
            }
            return data
    
    def _save_results(self, data: Dict[str, Any]) -> None:
        """Save analysis results to appropriate directories."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save character profiles
        for char_name, char_data in data["characters"].items():
            filename = f"{char_name.lower().replace(' ', '_')}_{timestamp}.json"
            filepath = os.path.join(self.character_data_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(char_data, f, indent=2)
        
        # Save relationship map
        relationship_file = os.path.join(
            self.relationship_data_dir,
            f"relationship_map_{timestamp}.json"
        )
        with open(relationship_file, 'w') as f:
            json.dump({
                "relationships": data["relationships"],
                "statistics": data["statistics"]["relationship_stats"]
            }, f, indent=2)
        
        # Save scene matrix
        scene_matrix_file = os.path.join(
            self.scene_data_dir,
            f"scene_matrix_{timestamp}.json"
        )
        with open(scene_matrix_file, 'w') as f:
            json.dump({
                "scene_matrix": data["scene_matrix"],
                "statistics": data["statistics"]["scene_stats"]
            }, f, indent=2)
        
        # Save overall statistics
        stats_file = os.path.join(self.data_dir, f"analysis_stats_{timestamp}.json")
        with open(stats_file, 'w') as f:
            json.dump(data["statistics"], f, indent=2)
        
        logger.info(f"Saved all analysis results with timestamp {timestamp}") 