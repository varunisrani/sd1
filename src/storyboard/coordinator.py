from typing import Dict, Any, List
import json
import os
import logging
from datetime import datetime
import openai
from .agents.prompt_generator_agent import PromptGeneratorAgent
from .agents.image_generator_agent import ImageGeneratorAgent
from .agents.storyboard_formatter_agent import StoryboardFormatterAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StoryboardCoordinator:
    def __init__(self):
        logger.info("Initializing StoryboardCoordinator")
        self.prompt_generator = PromptGeneratorAgent()
        self.image_generator = ImageGeneratorAgent()
        self.storyboard_formatter = StoryboardFormatterAgent()
        
        # Create data directories
        os.makedirs("data/storyboards", exist_ok=True)
        os.makedirs("data/exports", exist_ok=True)
        logger.info("Storyboard directories ensured")

        # Shot type mappings for scene analysis
        self.shot_mappings = {
            "establishing": ["begin", "exterior", "wide", "establishing"],
            "action": ["fight", "chase", "run", "jump", "battle"],
            "emotion": ["close", "face", "cry", "smile", "emotional"],
            "detail": ["detail", "object", "specific", "focus"],
            "transition": ["fade", "dissolve", "montage"]
        }
    
    async def generate_storyboard(
        self,
        scene_data: Dict[str, Any],
        shot_settings: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate storyboard images for scenes through the enhanced pipeline."""
        try:
            logger.info("Starting storyboard generation pipeline")
            
            # Process scene data with shot type analysis
            processed_scene_data = self._analyze_and_process_scenes(scene_data)
            if not processed_scene_data["scenes"]:
                raise ValueError("No valid scenes found in scene data")
            
            logger.info(f"Found {len(processed_scene_data['scenes'])} scenes for storyboard generation")
            
            # Apply shot settings if provided, otherwise use analyzed settings
            if shot_settings:
                processed_scene_data = self._apply_shot_settings(processed_scene_data, shot_settings)
            
            # Generate prompts with technical parameters
            logger.info("Step 1: Generating image prompts for scenes")
            prompts = await self.prompt_generator.generate_prompts(processed_scene_data)
            if not prompts:
                raise ValueError("Failed to generate scene prompts")
            logger.info(f"Generated {len(prompts)} scene prompts")
            
            # Generate images with style parameters
            logger.info("Step 2: Generating storyboard images")
            image_results = await self.image_generator.generate_images(prompts)
            if not image_results:
                raise ValueError("Failed to generate storyboard images")
            
            # Save images to disk in static directory for web access
            output_dir = os.path.join("static", "storage", "storyboards")
            image_results = await self.image_generator.save_images_to_disk(image_results, output_dir)
            logger.info(f"Generated and saved {len(image_results)} storyboard images")
            
            # Format storyboard for display
            logger.info("Step 3: Formatting storyboard for display")
            formatted_storyboard = await self.storyboard_formatter.format_storyboard(
                processed_scene_data, 
                prompts, 
                image_results
            )
            
            # Convert absolute paths to web-accessible paths
            for scene in formatted_storyboard["scenes"]:
                if "image_path" in scene and scene["image_path"]:
                    # Get the relative path from the static directory
                    try:
                        relative_path = os.path.relpath(scene["image_path"], start="static")
                        scene["image_path"] = relative_path
                    except ValueError:
                        # If paths are on different drives, keep the original path
                        pass
            
            # Save storyboard data
            saved_path = self._save_to_disk(formatted_storyboard)
            formatted_storyboard["saved_path"] = saved_path
            
            logger.info("Storyboard generation pipeline completed successfully")
            return formatted_storyboard
            
        except Exception as e:
            logger.error(f"Failed to generate storyboard: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "status": "failed"
            }
    
    def _analyze_and_process_scenes(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze scenes and determine appropriate shot types."""
        if not isinstance(scene_data, dict):
            raise ValueError("Scene data must be a dictionary")
        
        scenes = scene_data.get('scenes', [])
        if not scenes and 'parsed_data' in scene_data:
            scenes = scene_data['parsed_data'].get('scenes', [])
        
        processed_scenes = []
        for i, scene in enumerate(scenes):
            # Convert string scenes to dictionary format
            if isinstance(scene, str):
                scene_dict = {
                    "scene_id": str(i + 1),
                    "scene_heading": f"Scene {i + 1}",
                    "description": scene
                }
            else:
                scene_dict = scene.copy()
                if "scene_id" not in scene_dict:
                    scene_dict["scene_id"] = str(i + 1)
            
            # Analyze scene content for shot type
            description = scene_dict.get("description", "").lower()
            shot_type = self._determine_shot_type(description)
            
            # Add technical parameters
            scene_dict["technical_params"] = {
                "shot_type": shot_type,
                "style": "realistic",  # Default style
                "mood": self._analyze_scene_mood(description)
            }
            
            processed_scenes.append(scene_dict)
        
        return {
            'scenes': processed_scenes,
            'metadata': scene_data.get('metadata', {}),
            'original_data': scene_data
        }
    
    def _determine_shot_type(self, description: str) -> str:
        """Analyze scene description to determine appropriate shot type."""
        description = description.lower()
        
        # Check each shot type mapping
        for shot_type, keywords in self.shot_mappings.items():
            if any(keyword in description for keyword in keywords):
                return shot_type.upper()
        
        # Default to medium shot if no specific type is determined
        return "MS"
    
    def _analyze_scene_mood(self, description: str) -> str:
        """Analyze scene description to determine mood."""
        # Simple mood analysis based on keywords
        mood_keywords = {
            "tense": ["fight", "danger", "fear", "dark", "threat"],
            "joyful": ["happy", "laugh", "smile", "celebration"],
            "mysterious": ["mystery", "shadow", "secret", "unknown"],
            "melancholic": ["sad", "lonely", "grief", "sorrow"]
        }
        
        description = description.lower()
        for mood, keywords in mood_keywords.items():
            if any(keyword in description for keyword in keywords):
                return mood
        
        return "neutral"
    
    def _apply_shot_settings(
        self,
        scene_data: Dict[str, Any],
        shot_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply manual shot settings to processed scene data."""
        for scene in scene_data["scenes"]:
            scene_id = scene["scene_id"]
            
            # Apply scene-specific settings if available
            if "scene_settings" in shot_settings and scene_id in shot_settings["scene_settings"]:
                specific_settings = shot_settings["scene_settings"][scene_id]
                scene["technical_params"].update(specific_settings)
            else:
                # Apply global settings
                scene["technical_params"].update({
                    "shot_type": shot_settings.get("default_shot_type", scene["technical_params"]["shot_type"]),
                    "style": shot_settings.get("style", scene["technical_params"]["style"]),
                    "mood": shot_settings.get("mood", scene["technical_params"]["mood"])
                })
        
        return scene_data
    
    def _save_to_disk(self, data: Dict[str, Any]) -> str:
        """Save storyboard data to disk."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/storyboards/storyboard_{timestamp}.json"
            
            logger.info(f"Saving storyboard data to {filename}")
            
            # Validate data is JSON serializable
            try:
                json.dumps(data)
            except TypeError as e:
                logger.error(f"Data is not JSON serializable: {str(e)}")
                raise TypeError(f"Data is not JSON serializable: {str(e)}")
            
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Successfully saved {os.path.getsize(filename)} bytes to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to write file {filename}: {str(e)}", exc_info=True)
            raise
    
    async def export_storyboard(
        self,
        storyboard_data: Dict[str, Any],
        export_format: str = "pdf",
        output_path: str = None
    ) -> str:
        """Export storyboard in specified format."""
        return await self.storyboard_formatter.export_pdf(storyboard_data, output_path)
    
    async def add_annotation(
        self,
        storyboard_data: Dict[str, Any],
        scene_id: str,
        annotation: str
    ) -> Dict[str, Any]:
        """Add annotation to a storyboard scene."""
        return await self.storyboard_formatter.add_annotation(storyboard_data, scene_id, annotation)
    
    async def reorder_sequence(
        self,
        storyboard_data: Dict[str, Any],
        new_order: List[str]
    ) -> Dict[str, Any]:
        """Reorder the sequence of scenes in the storyboard."""
        return await self.storyboard_formatter.reorder_sequence(storyboard_data, new_order) 