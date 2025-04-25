import logging
import os
from typing import Dict, Any, List, Optional
import asyncio
import base64
from datetime import datetime

from src.storyboard.agents.prompt_generator_agent import PromptGeneratorAgent
from src.storyboard.agents.image_generator_agent import ImageGeneratorAgent

logger = logging.getLogger(__name__)

class StoryboardManager:
    """Manager class responsible for coordinating the storyboard generation process."""
    
    def __init__(self):
        logger.info("Initializing StoryboardManager")
        self.prompt_generator = PromptGeneratorAgent()
        self.image_generator = ImageGeneratorAgent()
        
        # Create storyboard output directory if it doesn't exist
        self.output_dir = os.path.join("static", "storage", "storyboards")
        os.makedirs(self.output_dir, exist_ok=True)
        
    async def generate_storyboard(self, script_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a complete storyboard for a script.
        
        Args:
            script_data: Dictionary containing script information including scenes
            
        Returns:
            Dictionary containing storyboard metadata and image paths
        """
        try:
            logger.info(f"Starting storyboard generation for script: {script_data.get('title', 'Untitled')}")
            
            # Extract scenes from script data
            scenes = script_data.get("scenes", [])
            if not scenes:
                logger.warning("No scenes found in script data")
                return {"error": "No scenes found in script data"}
            
            # Generate prompts for each scene
            prompts = self.prompt_generator.generate_prompts(scenes)
            logger.info(f"Generated {len(prompts)} prompts for storyboard images")
            
            # Generate images from prompts
            storyboard_images = await self.image_generator.generate_images(prompts)
            
            # Save images to disk and organize storyboard metadata
            storyboard_data = await self._save_storyboard_images(
                script_data, storyboard_images
            )
            
            return storyboard_data
            
        except Exception as e:
            logger.error(f"Error during storyboard generation: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    async def _save_storyboard_images(
        self, script_data: Dict[str, Any], image_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Save generated images to disk and create storyboard metadata.
        
        Args:
            script_data: Dictionary containing script information
            image_data: List of dictionaries containing image data and metadata
            
        Returns:
            Dictionary containing storyboard metadata and image paths
        """
        # Create unique directory for this storyboard
        script_title = script_data.get("title", "untitled").lower().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        storyboard_dir = os.path.join(self.output_dir, f"{script_title}_{timestamp}")
        os.makedirs(storyboard_dir, exist_ok=True)
        
        # Create storyboard metadata
        storyboard_metadata = {
            "script_id": script_data.get("id"),
            "script_title": script_data.get("title", "Untitled"),
            "created_at": timestamp,
            "scenes": []
        }
        
        # Process each image
        for item in image_data:
            scene_id = item.get("scene_id")
            scene_heading = item.get("scene_heading", "")
            
            # Skip if there was an error or no image data
            if "error" in item or not item.get("image_data"):
                error_message = item.get("error", "Unknown error")
                logger.warning(f"No image generated for scene {scene_id}: {error_message}")
                
                # Add error information to metadata
                storyboard_metadata["scenes"].append({
                    "scene_id": scene_id,
                    "scene_heading": scene_heading,
                    "image_path": None,
                    "error": error_message
                })
                continue
            
            # Save image to file
            image_filename = f"scene_{scene_id}.png"
            image_path = os.path.join(storyboard_dir, image_filename)
            
            # Decode and save the base64 image data
            try:
                image_binary = base64.b64decode(item["image_data"])
                with open(image_path, "wb") as f:
                    f.write(image_binary)
                
                # Get relative path for web access
                relative_path = os.path.join("storage", "storyboards", 
                                            f"{script_title}_{timestamp}", 
                                            image_filename)
                
                # Add to metadata
                storyboard_metadata["scenes"].append({
                    "scene_id": scene_id,
                    "scene_heading": scene_heading,
                    "image_path": relative_path,
                    "prompt": item.get("prompt"),
                    "revised_prompt": item.get("revised_prompt")
                })
                
                logger.info(f"Saved storyboard image for scene {scene_id}")
                
            except Exception as e:
                logger.error(f"Error saving image for scene {scene_id}: {str(e)}")
                storyboard_metadata["scenes"].append({
                    "scene_id": scene_id,
                    "scene_heading": scene_heading,
                    "image_path": None,
                    "error": f"Error saving image: {str(e)}"
                })
        
        # Save metadata file
        metadata_path = os.path.join(storyboard_dir, "metadata.json")
        try:
            with open(metadata_path, "w") as f:
                import json
                json.dump(storyboard_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving storyboard metadata: {str(e)}")
        
        return storyboard_metadata 