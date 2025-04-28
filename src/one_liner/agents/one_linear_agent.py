"""
One-Liner Agent using OpenAI GPT-4.
"""
import os
import json
from typing import Dict, Any, List, Optional
import logging
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime, timedelta

from .base_agent import BaseAgent
from .llm_utils import call_openai_gpt, parse_json_response

# Configure logging
logger = logging.getLogger(__name__)

class OneLinerAgent(BaseAgent):
    """Agent for generating concise scene summaries."""
    
    def __init__(self):
        """Initialize the one-liner agent."""
        super().__init__("One-Liner Agent")
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.cache_ttl = timedelta(days=7)  # Cache results for 7 days
    
    def _validate_cache_data(self, data: Dict[str, Any]) -> bool:
        """Validate cached data structure.
        
        Args:
            data: The cached data to validate
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            if not isinstance(data, dict):
                return False
                
            required_keys = {"production_title", "scenes"}
            if not all(key in data for key in required_keys):
                return False
                
            if not isinstance(data["scenes"], list):
                return False
                
            for scene in data["scenes"]:
                if not isinstance(scene, dict):
                    return False
                if not all(key in scene for key in ["scene_number", "one_liner"]):
                    return False
                if not isinstance(scene["scene_number"], (int, float)):
                    return False
                if not isinstance(scene["one_liner"], str):
                    return False
                    
            return True
            
        except Exception:
            return False
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load results from cache with TTL and validation.
        
        Args:
            cache_key: The cache key to load
            
        Returns:
            The cached data if valid and not expired, None otherwise
        """
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            if not os.path.exists(cache_file):
                return None
                
            # Check file modification time
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - mtime > self.cache_ttl:
                logger.info(f"Cache expired for key: {cache_key}")
                os.remove(cache_file)
                return None
                
            with open(cache_file, 'r') as f:
                data = json.load(f)
                
            if not self._validate_cache_data(data):
                logger.warning(f"Invalid cache data for key: {cache_key}")
                os.remove(cache_file)
                return None
                
            return data
            
        except Exception as e:
            logger.warning(f"Error loading cache: {str(e)}")
            return None
    
    def _cache_result(self, data: Dict[str, Any], cache_key: str) -> None:
        """Cache results with validation.
        
        Args:
            data: The data to cache
            cache_key: The cache key to use
        """
        if not self._validate_cache_data(data):
            logger.warning("Invalid data format, skipping cache")
            return
            
        try:
            super()._cache_result(data, cache_key)
        except Exception as e:
            logger.warning(f"Error caching result: {str(e)}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _call_api_with_retry(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API with retry logic.
        
        Args:
            prompt: The prompt to send to the API
            
        Returns:
            API response dictionary
            
        Raises:
            Exception: If all retries fail
        """
        return call_openai_gpt(
            prompt=prompt,
            model="gpt-4.1-mini",
            temperature=0.7,
            max_tokens=16000
        )
    
    def process(self, script_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate one-liner summaries for each scene.
        
        Args:
            script_analysis: The script analysis data from the script ingestion agent
            
        Returns:
            A dictionary containing one-liner summaries for each scene
            
        Raises:
            ValueError: If script_analysis is invalid
            RuntimeError: If API calls or parsing fails
        """
        if not script_analysis or not isinstance(script_analysis, dict):
            raise ValueError("Invalid script analysis data")

        # Check if we have a cached result
        cache_key = f"one_liners_{hash(json.dumps(script_analysis)) % 10000}"
        cached_result = self._load_from_cache(cache_key)
        if cached_result:
            logger.info("Returning cached one-liner results")
            return cached_result
        
        # Prepare the prompt for GPT
        prompt = f"""You are a professional script editor specializing in creating concise, impactful one-liner summaries 
        for film scenes. Your task is to create a single-sentence summary for each scene that captures its 
        essence, purpose, and emotional impact. These one-liners will be used in call sheets and production 
        documents for quick reference.
        
        A good one-liner should:
        1. Be 10-15 words maximum
        2. Capture the core action or emotional beat
        3. Include key characters and location context
        4. Convey the scene's purpose in the overall narrative
        5. Use active, vivid language
        
        Please create concise one-liner summaries for each scene in the following script analysis:
        
        {json.dumps(script_analysis, indent=2)}
        
        Format your response as a structured JSON object with the following schema:
        {{
            "production_title": "Title from script",
            "scenes": [
                {{
                    "scene_number": number,
                    "one_liner": "concise summary of the scene"
                }}
            ]
        }}
        """
        
        try:
            # Call OpenAI API with retry logic
            response = self._call_api_with_retry(prompt)
            
            if not response["success"]:
                raise RuntimeError(f"Failed to generate one-liners: {response.get('error')}")
            
            # Parse the response
            result = parse_json_response(response["content"])
            
            if not result["success"]:
                raise RuntimeError(f"Failed to parse one-liners: {result.get('error')}")
            
            # Validate response structure
            data = result["data"]
            if not self._validate_cache_data(data):
                raise RuntimeError("Invalid response format from API")
            
            # Cache the result
            self._cache_result(data, cache_key)
            logger.info("Successfully generated and cached one-liner summaries")
            
            return data
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise RuntimeError(f"Failed to generate one-liners: {str(e)}")