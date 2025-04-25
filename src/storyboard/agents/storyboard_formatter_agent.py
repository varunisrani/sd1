import logging
import os
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class StoryboardFormatterAgent:
    """Agent responsible for formatting storyboard data for display and export."""
    
    def __init__(self):
        """Initialize the StoryboardFormatterAgent."""
        logger.info("Initializing StoryboardFormatterAgent")
    
    async def format_storyboard(
        self,
        scene_data: Dict[str, Any],
        prompts: List[Dict[str, Any]],
        image_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format storyboard data for display and export.
        
        Args:
            scene_data: Processed scene data
            prompts: Generated image prompts
            image_results: Generated storyboard images
            
        Returns:
            Formatted storyboard data
        """
        logger.info("Formatting storyboard data")
        
        # Create formatted storyboard structure
        formatted = {
            "title": scene_data.get("metadata", {}).get("title", "Untitled Script"),
            "timestamp": datetime.now().isoformat(),
            "scenes": [],
            "status": "success"
        }
        
        # Process each scene
        for image_result in image_results:
            scene_id = image_result.get("scene_id")
            
            # Find corresponding prompt
            prompt_data = next((p for p in prompts if p.get("scene_id") == scene_id), {})
            
            # Create scene entry
            scene_entry = {
                "scene_id": scene_id,
                "scene_heading": prompt_data.get("scene_heading", ""),
                "description": prompt_data.get("scene_description", ""),
                "prompt": prompt_data.get("prompt", ""),
                "revised_prompt": image_result.get("revised_prompt"),
                "status": image_result.get("status", "error"),
                "image_path": None,
                "web_path": None,
                "image_url": None
            }
            
            # Handle image data and paths
            if image_result.get("status") == "success":
                scene_entry.update({
                    "image_path": image_result.get("local_file_path"),
                    "web_path": image_result.get("web_path"),
                    "image_url": image_result.get("image_url"),
                    "image_data": image_result.get("image_data")  # Keep base64 data if needed
                })
            else:
                scene_entry["error"] = image_result.get("error", "Unknown error")
            
            # Add to scenes list
            formatted["scenes"].append(scene_entry)
        
        # Add metadata
        formatted["metadata"] = {
            "scene_count": len(formatted["scenes"]),
            "source_data": scene_data.get("metadata", {}),
            "generation_config": {
                "image_model": "dall-e-3",
                "quality": "standard",
                "style": "natural",
                "size": "1024x1024"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate success rate
        successful_scenes = sum(1 for scene in formatted["scenes"] if scene.get("status") == "success")
        formatted["metadata"]["success_rate"] = f"{(successful_scenes / len(formatted['scenes'])) * 100:.1f}%"
        
        logger.info(f"Formatted storyboard with {len(formatted['scenes'])} scenes")
        return formatted 