"""
Base Agent class that all specialized agents will inherit from.
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, name: str):
        """Initialize the base agent.
        
        Args:
            name: The name of the agent
        """
        self.name = name
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
    
    @abstractmethod
    def process(self, *args, **kwargs) -> Dict[str, Any]:
        """Process the input data and return the results.
        
        This method must be implemented by all subclasses.
        
        Returns:
            A dictionary containing the processed data
        """
        pass
    
    def _cache_result(self, data: Dict[str, Any], cache_key: str) -> None:
        """Cache the result to a JSON file.
        
        Args:
            data: The data to cache
            cache_key: The key to use for the cache file
        """
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load data from the cache if it exists.
        
        Args:
            cache_key: The key to use for the cache file
            
        Returns:
            The cached data if it exists, None otherwise
        """
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                return json.load(f)
        return None