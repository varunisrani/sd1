import logging
import os
import base64
import asyncio
from typing import Dict, Any, List, Optional, Union
import time
from urllib.parse import urljoin
from datetime import datetime
import replicate
import httpx

logger = logging.getLogger(__name__)

class ImageGeneratorAgent:
    """Agent responsible for generating storyboard images from text prompts.
    
    This agent uses Replicate's Flux Schnell model to generate images based on detailed
    prompts created for storyboard purposes. It handles batch processing and returns 
    structured responses with image data.
    """
    
    def __init__(self):
        """Initialize the ImageGeneratorAgent with Replicate client."""
        logger.info("Initializing ImageGeneratorAgent")
        
        self.replicate_api_token = os.environ.get("REPLICATE_API_TOKEN")
        if not self.replicate_api_token:
            logger.warning("REPLICATE_API_TOKEN not found in environment variables")
        
        # Initialize Replicate client
        os.environ["REPLICATE_API_TOKEN"] = self.replicate_api_token
        
        # Shot type presets
        self.shot_presets = {
            "WS": "wide shot showing the full scene and environment",
            "MS": "medium shot from waist up",
            "CU": "close-up shot focusing on face/details",
            "ECU": "extreme close-up showing fine details",
            "OTS": "over-the-shoulder shot",
            "POV": "point-of-view shot from character perspective"
        }

        # Style presets
        self.style_presets = {
            "realistic": "photorealistic style with natural lighting",
            "scribble": "rough sketch style with pencil lines",
            "noir": "high contrast black and white style",
            "anime": "anime/manga inspired style",
            "watercolor": "soft watercolor artistic style",
            "storyboard": "traditional storyboard sketch style"
        }

        # Camera and lighting presets
        self.camera_presets = {
            "low_angle": "shot from below looking up, emphasizing power/dominance",
            "high_angle": "shot from above looking down, emphasizing vulnerability",
            "dutch_angle": "tilted camera angle creating tension/unease",
            "eye_level": "neutral camera angle at eye level"
        }

        self.lighting_presets = {
            "dramatic": "high contrast lighting with strong shadows",
            "soft": "diffused, even lighting with soft shadows",
            "backlit": "strong light source behind subject creating silhouette",
            "natural": "realistic ambient lighting matching scene time of day"
        }

    def _build_enhanced_prompt(self, base_prompt: str, shot_type: str = None, 
                             style_type: str = None, camera_angle: str = None,
                             lighting: str = None, mood: str = None) -> str:
        """Build an enhanced prompt incorporating shot type, style, and technical aspects."""
        prompt_elements = []
        
        # Add shot type first as it's crucial for storyboard composition
        if shot_type and shot_type in self.shot_presets:
            prompt_elements.append(self.shot_presets[shot_type])
            
        # Add base prompt next as it contains core scene description
        prompt_elements.append(base_prompt)
        
        # Add style
        if style_type and style_type in self.style_presets:
            prompt_elements.append(self.style_presets[style_type])
                
        # Add camera angle
        if camera_angle and camera_angle in self.camera_presets:
            prompt_elements.append(self.camera_presets[camera_angle])
                
        # Add lighting
        if lighting and lighting in self.lighting_presets:
            prompt_elements.append(self.lighting_presets[lighting])
                
        # Add mood
        if mood:
            prompt_elements.append(f"The overall mood is {mood}")
        
        # Join all elements
        return ", ".join(prompt_elements)

    async def generate_images(self, prompt_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate images based on a list of prompts with enhanced parameters."""
        if not prompt_data:
            logger.warning("No prompts provided for image generation")
            return []
        
        logger.info(f"Generating images for {len(prompt_data)} prompts")
        results = []
        
        # Create a single HTTP client for all requests
        async with httpx.AsyncClient() as client:
            batch_size = 5
            for i in range(0, len(prompt_data), batch_size):
                batch = prompt_data[i:i + batch_size]
                
                tasks = []
                for item in batch:
                    scene_id = item.get("scene_id")
                    base_prompt = item.get("prompt")
                    
                    if not scene_id or not base_prompt:
                        logger.warning(f"Missing scene_id or prompt in item: {item}")
                        results.append({
                            "scene_id": scene_id or "unknown",
                            "error": "Missing scene_id or prompt"
                        })
                        continue

                    # Enhanced prompt building with technical parameters
                    enhanced_prompt = self._build_enhanced_prompt(
                        base_prompt=base_prompt,
                        shot_type=item.get("shot_type"),
                        style_type=item.get("style_type"),
                        camera_angle=item.get("camera_angle"),
                        lighting=item.get("lighting"),
                        mood=item.get("mood")
                    )
                    
                    item["enhanced_prompt"] = enhanced_prompt
                    tasks.append(self._generate_single_image(scene_id, enhanced_prompt, client))
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Error in batch processing: {str(result)}")
                        results.append({
                            "scene_id": "unknown",
                            "error": f"Batch processing error: {str(result)}"
                        })
                    else:
                        results.append(result)
                
                if i + batch_size < len(prompt_data):
                    await asyncio.sleep(2)
        
        logger.info(f"Completed image generation for {len(results)} prompts")
        return results
    
    async def _generate_single_image(self, scene_id: str, prompt: str, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Generate a single image from a prompt using Replicate's Flux Schnell model."""
        logger.info(f"Generating image for scene {scene_id}")
        
        if not prompt:
            logger.error(f"No prompt provided for scene {scene_id}")
            return {
                "scene_id": scene_id,
                "error": "No prompt provided"
            }
        
        # Initialize result dictionary
        result = {
            "scene_id": scene_id,
            "prompt": prompt,
            "image_data": None,
            "metadata": {}
        }
        
        try:
            # Run the Flux Schnell model
            prediction = await asyncio.to_thread(
                replicate.run,
                "black-forest-labs/flux-schnell",
                input={"prompt": prompt}
            )
            
            # Get the first image from the output
            if prediction and len(prediction) > 0:
                # Get the image URL from the prediction
                image_output = prediction[0]
                
                # If it's a FileOutput object, get the URL
                image_url = image_output.url if hasattr(image_output, 'url') else str(image_output)
                
                # Download the image data
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
                
                result["image_data"] = image_data
                result["metadata"]["model"] = "flux-schnell"
                result["metadata"]["timestamp"] = datetime.now().isoformat()
                result["metadata"]["image_url"] = image_url
            else:
                raise ValueError("No image generated")
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating image for scene {scene_id}: {str(e)}")
            return {
                "scene_id": scene_id,
                "error": str(e)
            }

    async def save_images_to_disk(self, results: List[Dict[str, Any]], output_dir: str) -> List[Dict[str, Any]]:
        """Save generated images to disk."""
        logger.info(f"Saving {len(results)} images to {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        
        saved_results = []
        for result in results:
            scene_id = result.get("scene_id", "unknown")
            
            try:
                if "error" in result:
                    logger.warning(f"Skipping scene {scene_id} due to error: {result['error']}")
                    saved_results.append(result)
                    continue
                
                if not result.get("image_data"):
                    logger.warning(f"No image data for scene {scene_id}")
                    result["error"] = "No image data"
                    saved_results.append(result)
                    continue
                
                # Save image to disk
                filename = f"scene_{scene_id}.webp"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, "wb") as f:
                    f.write(result["image_data"])
                
                # Update result with file path
                saved_result = result.copy()
                saved_result["image_path"] = filepath
                saved_result.pop("image_data", None)  # Remove binary data
                
                # Add web-accessible path
                try:
                    web_path = os.path.join("storage", "storyboards", filename)
                    saved_result["web_path"] = web_path.replace(os.sep, "/")  # Ensure forward slashes for web paths
                except Exception as e:
                    logger.warning(f"Error creating web path for scene {scene_id}: {str(e)}")
                
                saved_results.append(saved_result)
                
                logger.info(f"Saved image for scene {scene_id} to {filepath}")
                
            except Exception as e:
                logger.error(f"Error saving image for scene {scene_id}: {str(e)}")
                result["error"] = f"Error saving image: {str(e)}"
                saved_results.append(result)
        
        return saved_results

    async def generate_image(
        self,
        prompt: str,
        output_dir: str = None,
        save_image: bool = True,
        filename: str = None,
        metadata: dict = None
    ) -> dict:
        """Generate a single image from a prompt.
        
        Args:
            prompt: The text prompt to generate the image from
            output_dir: Directory to save the image (if save_image is True)
            save_image: Whether to save the image to disk
            filename: Custom filename for saved image
            metadata: Additional metadata to include in result
            
        Returns:
            dict containing:
            - image_data: Base64 encoded image or URL
            - metadata: Generation parameters and additional info
            - filepath: Path to saved image if applicable
        """
        try:
            logger.info(f"Generating image with prompt: {prompt}")
            
            # Generate image with Replicate
            response = await replicate.run(
                "black-forest-labs/flux-schnell",
                input={"prompt": prompt}
            )

            # Extract image data
            if response and len(response) > 0:
                image_output = response[0]
                # If it's a FileOutput object, get the URL and download
                image_url = image_output.url if hasattr(image_output, 'url') else str(image_output)
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url)
                    response.raise_for_status()
                    image_data = response.content
            else:
                raise ValueError("No image generated")

            result = {
                "image_data": image_data,
                "metadata": {
                    "model": "flux-schnell",
                    "timestamp": datetime.now().isoformat(),
                    "image_url": image_url
                }
            }

            # Add any additional metadata
            if metadata:
                result["metadata"].update(metadata)

            # Save image if requested
            if save_image and output_dir:
                if not filename:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"image_{timestamp}.webp"
                
                filepath = os.path.join(output_dir, filename)
                os.makedirs(output_dir, exist_ok=True)
                
                with open(filepath, "wb") as f:
                    f.write(image_data)
                
                result["filepath"] = filepath
                logger.info(f"Saved image to {filepath}")

            return result

        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            raise 
