import logging
import os
import base64
import asyncio
from typing import Dict, Any, List, Optional, Union
import time
from urllib.parse import urljoin
from datetime import datetime

import httpx
from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

class ImageGeneratorAgent:
    """Agent responsible for generating storyboard images from text prompts.
    
    This agent uses OpenAI's DALL-E model to generate images based on detailed
    prompts created for storyboard purposes. It handles batch processing, retries
    on rate limits, and returns structured responses with image data.
    """
    
    def __init__(
        self,
        model: str = "dall-e-2",
        size: str = "1024x1024",
        response_format: str = "b64_json"
    ):
        """Initialize the ImageGeneratorAgent with OpenAI client and default parameters.
        
        Args:
            model: The model to use (default: dall-e-2)
            size: Image dimensions (256x256, 512x512, or 1024x1024)
            response_format: The format to return image data in (url or b64_json)
        """
        logger.info("Initializing ImageGeneratorAgent")
        
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=self.openai_api_key)
        self.http_client = httpx.AsyncClient()
        
        # Set default parameters
        self.model = model
        self.size = size
        self.response_format = response_format
        
        # Note: quality and style parameters are not available in DALL-E 2

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
        """Build an enhanced prompt incorporating shot type, style, and technical aspects.
        Ensures the final prompt stays within DALL-E 2's 1000 character limit."""
        
        # Start with technical aspects as they're most important
        prompt_elements = []
        
        # Add shot type first as it's crucial for storyboard composition
        if shot_type and shot_type in self.shot_presets:
            prompt_elements.append(self.shot_presets[shot_type])
            
        # Add base prompt next as it contains core scene description
        prompt_elements.append(base_prompt)
        
        remaining_chars = 1000 - len(". ".join(prompt_elements))
        
        # Add remaining elements if there's space, in order of importance
        if style_type and style_type in self.style_presets and remaining_chars > 0:
            style_text = self.style_presets[style_type]
            if len(style_text) < remaining_chars:
                prompt_elements.append(style_text)
                remaining_chars -= len(style_text) + 2  # +2 for ". "
                
        if camera_angle and camera_angle in self.camera_presets and remaining_chars > 0:
            camera_text = self.camera_presets[camera_angle]
            if len(camera_text) < remaining_chars:
                prompt_elements.append(camera_text)
                remaining_chars -= len(camera_text) + 2
                
        if lighting and lighting in self.lighting_presets and remaining_chars > 0:
            light_text = self.lighting_presets[lighting]
            if len(light_text) < remaining_chars:
                prompt_elements.append(light_text)
                remaining_chars -= len(light_text) + 2
                
        if mood and remaining_chars > 20:  # Ensure enough space for mood
            mood_text = f"The overall mood is {mood}"
            if len(mood_text) < remaining_chars:
                prompt_elements.append(mood_text)
        
        # Join all elements and ensure final length is under 1000
        final_prompt = ". ".join(prompt_elements)
        if len(final_prompt) > 1000:
            logger.warning("Prompt exceeded 1000 characters, truncating...")
            final_prompt = final_prompt[:997] + "..."
            
        return final_prompt

    async def generate_images(self, prompt_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate images based on a list of prompts with enhanced parameters."""
        if not prompt_data:
            logger.warning("No prompts provided for image generation")
            return []
        
        logger.info(f"Generating images for {len(prompt_data)} prompts")
        results = []
        
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
                tasks.append(self._generate_single_image(scene_id, enhanced_prompt))
            
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
    
    async def _generate_single_image(self, scene_id: str, prompt: str) -> Dict[str, Any]:
        """Generate a single image from a prompt.
        
        Args:
            scene_id: Identifier for the scene
            prompt: Detailed text prompt for image generation
            
        Returns:
            Dictionary containing image generation results
        """
        logger.info(f"Generating image for scene {scene_id}")
        
        if not prompt:
            logger.error(f"No prompt provided for scene {scene_id}")
            return {
                "scene_id": scene_id,
                "error": "No prompt provided"
            }
            
        # Log prompt length for debugging
        prompt_length = len(prompt)
        if prompt_length > 900:  # Warn if getting close to limit
            logger.warning(f"Scene {scene_id} prompt length ({prompt_length}) is close to 1000 char limit")
        else:
            logger.debug(f"Scene {scene_id} prompt length: {prompt_length} characters")
        
        # Initialize result dictionary
        result = {
            "scene_id": scene_id,
            "prompt": prompt,
            "revised_prompt": None,
            "image_data": None,
            "metadata": {
                "prompt_length": prompt_length  # Add length to metadata
            }
        }
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Make the API request
                response = await asyncio.to_thread(
                    self.client.images.generate,
                    model=self.model,
                    prompt=prompt,
                    size=self.size,
                    response_format=self.response_format,
                    n=1
                )
                
                # Extract image data
                if response.data and len(response.data) > 0:
                    image_data = response.data[0]
                    
                    # Store results
                    result["revised_prompt"] = image_data.revised_prompt
                    
                    if self.response_format == "b64_json":
                        result["image_data"] = image_data.b64_json
                    else:
                        result["image_data"] = image_data.url
                    
                    # Add metadata
                    result["metadata"] = {
                        "model": self.model,
                        "size": self.size
                    }
                    
                    logger.info(f"Successfully generated image for scene {scene_id}")
                else:
                    logger.warning(f"No image data returned for scene {scene_id}")
                    result["error"] = "No image data returned from API"
                
                break  # Success, exit the retry loop
                
            except RateLimitError as e:
                retry_count += 1
                logger.warning(f"Rate limit hit for scene {scene_id}, retry {retry_count}/{max_retries}")
                
                if retry_count < max_retries:
                    # Exponential backoff
                    wait_time = 2 ** retry_count
                    await asyncio.sleep(wait_time)
                else:
                    result["error"] = f"Rate limit exceeded after {max_retries} retries"
            
            except Exception as e:
                logger.error(f"Error generating image for scene {scene_id}: {str(e)}")
                result["error"] = str(e)
                break  # Don't retry on other errors
        
        return result
    
    async def save_images_to_disk(self, results: List[Dict[str, Any]], output_dir: str) -> List[Dict[str, Any]]:
        """Save generated images to disk with organized folder structure and web-accessible paths.
        
        Args:
            results: List of image generation results
            output_dir: Base directory to save images
            
        Returns:
            Updated results with local file paths and web URLs
        """
        # Create timestamp for unique folder
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Create base storyboard directory under static folder for web access
        static_dir = os.path.join("static", "storage", "storyboards")
        storyboard_dir = os.path.join(static_dir, f"storyboard_{timestamp}")
        images_dir = os.path.join(storyboard_dir, "images")
        metadata_dir = os.path.join(storyboard_dir, "metadata")
        
        # Create directory structure
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(metadata_dir, exist_ok=True)
        
        # Save metadata about the storyboard generation
        metadata = {
            "timestamp": timestamp,
            "total_scenes": len(results),
            "model": self.model,
            "size": self.size,
            "scenes": []
        }
        
        for i, result in enumerate(results):
            scene_id = result.get("scene_id", f"unknown_{i}")
            image_data = result.get("image_data")
            
            if not image_data:
                logger.warning(f"No image data for scene {scene_id}")
                metadata["scenes"].append({
                    "scene_id": scene_id,
                    "status": "error",
                    "error": "No image data available"
                })
                continue
            
            try:
                # Create scene-specific filename with padded numbers
                filename = f"scene_{str(scene_id).zfill(3)}.png"
                filepath = os.path.join(images_dir, filename)
                
                # Create web-accessible path
                web_path = f"/storage/storyboards/storyboard_{timestamp}/images/{filename}"
                
                if self.response_format == "b64_json" and image_data:
                    try:
                        # Decode base64 image data
                        image_bytes = base64.b64decode(image_data)
                        
                        # Save image file
                        with open(filepath, "wb") as f:
                            f.write(image_bytes)
                            
                    except Exception as e:
                        logger.error(f"Error decoding base64 data for scene {scene_id}: {str(e)}")
                        raise
                        
                elif self.response_format == "url" and image_data:
                    try:
                        # Download image from URL
                        response = await self.http_client.get(image_data)
                        response.raise_for_status()
                        
                        # Save image file
                        with open(filepath, "wb") as f:
                            f.write(response.content)
                            
                    except Exception as e:
                        logger.error(f"Error downloading image for scene {scene_id}: {str(e)}")
                        raise
                
                # Update result with file paths and web URL
                result.update({
                    "local_file_path": filepath,
                    "web_path": web_path,
                    "image_url": web_path,  # For backwards compatibility
                    "status": "success"
                })
                
                # Add scene metadata
                metadata["scenes"].append({
                    "scene_id": scene_id,
                    "filename": filename,
                    "web_path": web_path,
                    "prompt": result.get("prompt"),
                    "revised_prompt": result.get("revised_prompt"),
                    "status": "success"
                })
                
                logger.info(f"Saved image for scene {scene_id} to {filepath} (web: {web_path})")
                    
            except Exception as e:
                error_msg = f"Error saving image for scene {scene_id}: {str(e)}"
                logger.error(error_msg)
                result.update({
                    "error": error_msg,
                    "status": "error",
                    "image_url": None,
                    "web_path": None
                })
                metadata["scenes"].append({
                    "scene_id": scene_id,
                    "status": "error",
                    "error": error_msg
                })
        
        # Save metadata file
        try:
            metadata_file = os.path.join(metadata_dir, "generation_metadata.json")
            with open(metadata_file, "w") as f:
                import json
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved generation metadata to {metadata_file}")
        except Exception as e:
            logger.error(f"Error saving metadata file: {str(e)}")
        
        return results 

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
            
            # Generate image with OpenAI
            response = await self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=self.size,
                response_format=self.response_format,
                n=1
            )

            # Extract image data
            if self.response_format == "b64_json":
                image_data = response.data[0].b64_json
            else:
                image_data = response.data[0].url

            result = {
                "image_data": image_data,
                "metadata": {
                    "model": self.model,
                    "size": self.size
                }
            }

            # Add any additional metadata
            if metadata:
                result["metadata"].update(metadata)

            # Save image if requested
            if save_image and output_dir:
                if not filename:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"image_{timestamp}.png"
                
                filepath = os.path.join(output_dir, filename)
                os.makedirs(output_dir, exist_ok=True)
                
                if self.response_format == "b64_json":
                    # Decode and save base64 image
                    image_bytes = base64.b64decode(image_data)
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)
                else:
                    # Download and save image from URL
                    response = await self.http_client.get(image_data)
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                
                result["filepath"] = filepath
                logger.info(f"Saved image to {filepath}")

            return result

        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            raise 
