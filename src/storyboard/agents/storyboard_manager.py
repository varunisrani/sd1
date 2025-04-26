import logging
import os
from typing import Dict, Any, List, Optional
import asyncio
import base64
from datetime import datetime
import json

from src.storyboard.agents.prompt_generator_agent import PromptGeneratorAgent
from src.storyboard.agents.image_generator_agent import ImageGeneratorAgent
from src.storyboard.agents.storyboard_formatter_agent import StoryboardFormatterAgent

logger = logging.getLogger(__name__)

class StoryboardManager:
    """Manager class responsible for coordinating the storyboard generation process."""
    
    def __init__(self):
        logger.info("Initializing StoryboardManager")
        self.prompt_generator = PromptGeneratorAgent()
        self.image_generator = ImageGeneratorAgent()
        self.formatter = StoryboardFormatterAgent()
        
        # Create storyboard output directory if it doesn't exist
        self.output_dir = os.path.join("static", "storage", "storyboards")
        os.makedirs(self.output_dir, exist_ok=True)

        # Shot type presets for quick access
        self.shot_presets = {
            "establishing": {"type": "WS", "description": "Wide establishing shot"},
            "action": {"type": "MS", "description": "Medium shot for action"},
            "emotion": {"type": "CU", "description": "Close-up for emotional moments"},
            "detail": {"type": "ECU", "description": "Extreme close-up for details"},
            "pov": {"type": "POV", "description": "Point of view shot"}
        }

        # Style presets
        self.style_presets = {
            "realistic": "Photorealistic style",
            "sketch": "Traditional storyboard sketch",
            "noir": "High contrast black and white",
            "anime": "Anime/manga style",
            "minimal": "Simple, minimal lines"
        }
        
    async def generate_storyboard(
        self, 
        script_data: Dict[str, Any],
        shot_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a complete storyboard for a script with enhanced parameters."""
        try:
            logger.info(f"Starting storyboard generation for script: {script_data.get('title', 'Untitled')}")
            
            # Extract and preprocess scenes
            processed_scene_data = self._preprocess_script_data(script_data, shot_settings)
            if not processed_scene_data["scenes"]:
                raise ValueError("No valid scenes found in script data")
            
            logger.info(f"Found {len(processed_scene_data['scenes'])} scenes for storyboard generation")
            
            # Generate prompts with technical parameters
            prompts = await self.prompt_generator.generate_prompts(processed_scene_data)
            if not prompts:
                raise ValueError("Failed to generate scene prompts")
            logger.info(f"Generated {len(prompts)} scene prompts")
            
            # Generate images with style and shot type parameters
            image_results = await self.image_generator.generate_images(prompts)
            if not image_results:
                raise ValueError("Failed to generate storyboard images")
            
            # Save images and organize storyboard
            image_results = await self.image_generator.save_images_to_disk(image_results, self.output_dir)
            logger.info(f"Generated and saved {len(image_results)} storyboard images")
            
            # Format storyboard with enhanced features
            formatted_storyboard = await self.formatter.format_storyboard(
                processed_scene_data, 
                prompts, 
                image_results
            )
            
            # Add web paths
            formatted_storyboard["web_root"] = "/storage/storyboards"
            for scene in formatted_storyboard["scenes"]:
                if "image_path" in scene and scene["image_path"]:
                    scene["web_path"] = scene["image_path"].replace(self.output_dir, "/storage/storyboards")
            
            # Save storyboard data
            saved_path = await self._save_storyboard_data(formatted_storyboard)
            formatted_storyboard["saved_path"] = saved_path
            
            logger.info("Storyboard generation pipeline completed successfully")
            return formatted_storyboard
            
        except Exception as e:
            logger.error(f"Failed to generate storyboard: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "status": "failed"
            }

    def _preprocess_script_data(
        self, 
        script_data: Dict[str, Any],
        shot_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Preprocess script data with shot and style settings."""
        if not isinstance(script_data, dict):
            raise ValueError("Script data must be a dictionary")
        
        scenes = script_data.get('scenes', [])
        if not scenes and 'parsed_data' in script_data:
            scenes = script_data['parsed_data'].get('scenes', [])
        
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
            
            # Apply shot settings if provided
            if shot_settings:
                scene_type = shot_settings.get("default_shot_type", "MS")
                if "shot_mapping" in shot_settings:
                    # Check for scene-specific shot type
                    for pattern, shot_type in shot_settings["shot_mapping"].items():
                        if pattern.lower() in scene_dict.get("description", "").lower():
                            scene_type = shot_type
                            break
                
                scene_dict["technical_params"] = {
                    "shot_type": scene_type,
                    "style": shot_settings.get("style", "realistic"),
                    "mood": shot_settings.get("mood", "neutral")
                }
            
            processed_scenes.append(scene_dict)
        
        return {
            'scenes': processed_scenes,
            'metadata': script_data.get('metadata', {}),
            'original_data': script_data
        }

    async def _save_storyboard_data(self, data: Dict[str, Any]) -> str:
        """Save storyboard data to disk with metadata."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/storyboards/storyboard_{timestamp}.json"
            
            logger.info(f"Saving storyboard data to {filename}")
            
            # Ensure data is JSON serializable
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
            logger.error(f"Error saving storyboard data: {str(e)}")
            raise

    async def export_storyboard(
        self,
        storyboard_data: Dict[str, Any],
        export_format: str = "pdf",
        output_path: Optional[str] = None
    ) -> str:
        """Export storyboard in specified format."""
        try:
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if export_format == "pdf":
                    output_path = f"data/exports/storyboard_{timestamp}.pdf"
                else:
                    output_path = f"data/exports/storyboard_{timestamp}"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            if export_format == "pdf":
                return await self.formatter.export_pdf(storyboard_data, output_path)
            elif export_format == "slideshow":
                return await self.formatter.export_slideshow(storyboard_data, output_path)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")
                
        except Exception as e:
            logger.error(f"Error exporting storyboard: {str(e)}")
            raise

    async def add_annotation(
        self,
        storyboard_data: Dict[str, Any],
        scene_id: str,
        annotation: str
    ) -> Dict[str, Any]:
        """Add annotation to a storyboard scene."""
        return await self.formatter.add_annotation(storyboard_data, scene_id, annotation)

    async def reorder_sequence(
        self,
        storyboard_data: Dict[str, Any],
        new_order: List[str]
    ) -> Dict[str, Any]:
        """Reorder the sequence of scenes in the storyboard."""
        return await self.formatter.reorder_sequence(storyboard_data, new_order) 