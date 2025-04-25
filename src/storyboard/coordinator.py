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
        
        # Create data directory if it doesn't exist
        os.makedirs("data/storyboards", exist_ok=True)
        logger.info("Storyboard data directory ensured at data/storyboards")
    
    async def generate_storyboard(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate storyboard images for scenes through the storyboard pipeline."""
        try:
            logger.info("Starting storyboard generation pipeline")
            
            # Extract the relevant data from the script ingestion results
            processed_scene_data = self._extract_scene_data(scene_data)
            if not processed_scene_data["scenes"]:
                raise ValueError("No valid scenes found in scene data")
            
            # Add special handling for string scenes
            processed_scene_data = self._preprocess_scenes(processed_scene_data)
            
            logger.info(f"Found {len(processed_scene_data['scenes'])} scenes for storyboard generation")
            
            # Step 1: Generate prompts for each scene
            logger.info("Step 1: Generating image prompts for scenes")
            prompts = await self.prompt_generator.generate_prompts(processed_scene_data)
            if not prompts:
                raise ValueError("Failed to generate scene prompts")
            logger.info(f"Generated {len(prompts)} scene prompts")
            
            # Step 2: Generate images for each prompt
            logger.info("Step 2: Generating storyboard images")
            image_results = await self.image_generator.generate_images(prompts)
            if not image_results:
                raise ValueError("Failed to generate storyboard images")
            
            # Save images to disk in static directory for web access
            output_dir = os.path.join("static", "storage", "storyboards")
            image_results = await self.image_generator.save_images_to_disk(image_results, output_dir)
            logger.info(f"Generated and saved {len(image_results)} storyboard images")
            
            # Step 3: Format storyboard for display
            logger.info("Step 3: Formatting storyboard for display")
            formatted_storyboard = await self.storyboard_formatter.format_storyboard(
                processed_scene_data, 
                prompts, 
                image_results
            )
            
            # Add web-accessible paths to the formatted storyboard
            formatted_storyboard["web_root"] = "/storage/storyboards"
            for scene in formatted_storyboard["scenes"]:
                if "image_path" in scene and scene["image_path"]:
                    scene["web_path"] = scene["image_path"].replace(output_dir, "/storage/storyboards")
            
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
    
    def _preprocess_scenes(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess scenes to ensure they are in the correct format for prompt generation."""
        try:
            scenes = scene_data.get('scenes', [])
            processed_scenes = []
            
            for i, scene in enumerate(scenes):
                # If scene is a string, convert it to a dictionary
                if isinstance(scene, str):
                    processed_scenes.append({
                        "scene_id": str(i + 1),
                        "scene_heading": f"Scene {i + 1}",
                        "description": scene
                    })
                else:
                    # If scene is already a dictionary, just add it as is
                    processed_scenes.append(scene)
            
            # Return updated scene data
            scene_data['scenes'] = processed_scenes
            return scene_data
            
        except Exception as e:
            logger.error(f"Error preprocessing scenes: {str(e)}")
            # If preprocessing fails, return original data
            return scene_data
    
    def _extract_scene_data(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant scene data from the script ingestion results."""
        if not isinstance(scene_data, dict):
            raise ValueError("Scene data must be a dictionary")
        
        if 'parsed_data' not in scene_data and 'scenes' not in scene_data:
            raise ValueError("Scene data must contain either 'parsed_data' or 'scenes' key")
        
        # If we have parsed_data, extract scenes from it
        scenes = scene_data.get('scenes', [])
        if not scenes and 'parsed_data' in scene_data:
            parsed_data = scene_data['parsed_data']
            if isinstance(parsed_data, dict) and 'scenes' in parsed_data:
                scenes = parsed_data['scenes']
        
        # Return processed scene data
        return {
            'scenes': scenes,
            'metadata': scene_data.get('metadata', {}),
            'original_data': scene_data
        }
    
    def _save_to_disk(self, data: Dict[str, Any]) -> str:
        """Save storyboard data to disk.
        
        Args:
            data: Dictionary containing storyboard data to save
            
        Returns:
            str: Path to the saved file
            
        Raises:
            IOError: If file cannot be written
        """
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
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Successfully saved {os.path.getsize(filename)} bytes to {filename}")
            return filename 
            
        except IOError as e:
            logger.error(f"Failed to write file {filename}: {str(e)}", exc_info=True)
            raise IOError(f"Failed to write storyboard file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error saving storyboard data: {str(e)}", exc_info=True)
            raise 