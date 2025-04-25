import logging
import os
import re
from typing import Dict, Any, List, Optional, Union
import asyncio

from openai import OpenAI

logger = logging.getLogger(__name__)

class PromptGeneratorAgent:
    """Agent responsible for generating detailed image prompts from scene descriptions.
    
    This agent takes scene descriptions from a screenplay and converts them into
    detailed prompts suitable for AI image generation, capturing visual elements 
    like environment, lighting, framing, and mood.
    """
    
    def __init__(self):
        """Initialize the PromptGeneratorAgent with OpenAI client and prompt template."""
        logger.info("Initializing PromptGeneratorAgent")
        
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=self.openai_api_key)
        
        # Define the prompt template for consistent prompt generation
        self.prompt_template = """
        Create a detailed visual prompt for an AI image generator based on this scene description from a screenplay:
        
        SCENE: {scene_description}
        
        Your prompt should:
        1. Include the key visual elements (setting, characters, actions)
        2. Specify camera angle, framing, and perspective where appropriate
        3. Describe lighting, mood, and atmosphere
        4. Use specific, evocative, and concrete language
        5. Avoid dialogue or non-visual elements
        6. Keep the prompt under 200 words
        7. Format as a single paragraph without bullet points

        OUTPUT ONLY THE PROMPT, nothing else.
        """
    
    async def generate_prompts(self, scene_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate image prompts for a list of scenes.
        
        Args:
            scene_data: Dictionary containing scene data, with a 'scenes' key
                       containing a list of scene objects
        
        Returns:
            List of dictionaries containing scene IDs and generated prompts
        """
        # Extract scenes from scene_data
        scenes = scene_data.get('scenes', [])
        logger.info(f"Generating prompts for {len(scenes)} scenes")
        
        results = []
        for i, scene in enumerate(scenes):
            # Handle both dictionary and string scenes
            if isinstance(scene, str):
                # For string scenes, create a simple dictionary with index as ID
                scene_id = str(i + 1)
                scene_description = scene
                scene_heading = f"Scene {scene_id}"
            else:
                # For dictionary scenes, extract ID and description normally
                scene_id = scene.get("scene_id") or scene.get("id") or str(i + 1)
                scene_heading = scene.get("scene_heading", f"Scene {scene_id}")
                scene_description = await self._extract_scene_description(scene)
            
            if not scene_description:
                logger.warning(f"Scene {scene_id} has no description, skipping")
                continue
            
            try:
                # Generate the prompt for this scene
                prompt = await self._generate_single_prompt(scene_description)
                
                # Store the result
                result = {
                    "scene_id": scene_id,
                    "scene_heading": scene_heading,
                    "scene_description": scene_description,
                    "prompt": prompt
                }
                results.append(result)
                logger.info(f"Generated prompt for scene {scene_id}")
                
            except Exception as e:
                logger.error(f"Error generating prompt for scene {scene_id}: {str(e)}")
                results.append({
                    "scene_id": scene_id,
                    "scene_heading": scene_heading,
                    "error": str(e)
                })
        
        logger.info(f"Completed prompt generation for {len(results)} scenes")
        return results
    
    async def _generate_single_prompt(self, scene_description: str) -> str:
        """Generate a single image prompt from a scene description.
        
        Args:
            scene_description: The description of the scene
            
        Returns:
            A generated image prompt
        """
        try:
            # Format the prompt template with the scene description
            formatted_prompt = self.prompt_template.format(scene_description=scene_description)
            
            # Call the OpenAI API to generate the prompt
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",  # Use the best model for detailed visual interpretation
                messages=[
                    {"role": "system", "content": "You are a master cinematic storyboard artist."},
                    {"role": "user", "content": formatted_prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            # Extract the response
            generated_prompt = response.choices[0].message.content.strip()
            
            # Clean up the prompt - remove any prefixes like "Prompt:" or quotes
            generated_prompt = re.sub(r'^(prompt:\s*|"|\')', '', generated_prompt, flags=re.IGNORECASE)
            generated_prompt = re.sub(r'("|\')\s*$', '', generated_prompt)
            
            return generated_prompt
            
        except Exception as e:
            logger.error(f"Error in prompt generation: {str(e)}")
            raise
    
    async def _extract_scene_description(self, scene: Dict[str, Any]) -> str:
        """Extract the scene description from various possible field names.
        
        Args:
            scene: A dictionary containing scene information
            
        Returns:
            The scene description text
        """
        # If scene is not a dictionary, return it as is
        if not isinstance(scene, dict):
            return str(scene)
            
        # Check different possible field names for scene description
        description_fields = ["description", "scene_description", "action", "scene_action"]
        
        for field in description_fields:
            if field in scene and scene[field]:
                return scene[field]
        
        # If no description is found, try to extract from dialogue
        if "dialogue" in scene and scene["dialogue"]:
            dialogue_entries = scene["dialogue"]
            if isinstance(dialogue_entries, list) and dialogue_entries:
                # Compile dialogue descriptions/actions
                descriptions = []
                for entry in dialogue_entries:
                    if isinstance(entry, dict):
                        # Extract character action/description if available
                        action = entry.get("action", "")
                        if action:
                            descriptions.append(action)
                
                if descriptions:
                    return " ".join(descriptions)
        
        # If no description is found, use scene heading as a fallback
        if "scene_heading" in scene and scene["scene_heading"]:
            return f"A scene showing {scene['scene_heading']}"
            
        return "" 