"""
Utility functions for logging API calls and other operations.
"""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_api_call(
    provider: str,
    model: str,
    prompt_length: int,
    response_length: int,
    duration: float,
    status: str,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log details about an API call to an LLM service.
    
    Args:
        provider: The API provider (e.g., 'openai', 'gemini')
        model: The model name used
        prompt_length: Length of the prompt in characters
        response_length: Length of the response in characters
        duration: Time taken for the API call in seconds
        status: Status of the call ('success' or 'error')
        error: Error message if status is 'error'
        metadata: Additional metadata about the call
    """
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "prompt_length": prompt_length,
        "response_length": response_length,
        "duration_seconds": round(duration, 3),
        "status": status
    }
    
    if error:
        log_data["error"] = error
        
    if metadata:
        log_data["metadata"] = metadata
    
    # Log as JSON for easier parsing
    logger.info(f"API Call: {json.dumps(log_data)}")
    
    # Log to file if needed
    try:
        with open("api_calls.log", "a") as f:
            f.write(json.dumps(log_data) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write to log file: {str(e)}") 