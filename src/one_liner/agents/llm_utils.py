"""
Utility functions for interacting with LLM APIs (OpenAI and Google Gemini).
"""
import os
import json
import time
from typing import Dict, Any, List, Optional, Union

import openai
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# Import logging utilities
from .logging_utils import log_api_call

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure API keys
openai.api_key = os.getenv("OPENAI_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def call_openai_gpt(
    prompt: str,
    model: str = "gpt-4.1-mini",
    temperature: float = 0.7,
    max_tokens: int = 16000,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Call OpenAI GPT model with the given prompt.
    
    Args:
        prompt (str): The prompt to send to the model
        model (str): The model to use (default: gpt-4)
        temperature (float): Temperature setting (default: 0.7)
        max_tokens (int): Maximum tokens in response (default: 1000)
        api_key (Optional[str]): OpenAI API key. If None, uses environment variable
        
    Returns:
        Dict[str, Any]: The model's response
    """
    start_time = time.time()
    response_text = ""
    error = None
    status = "success"
    
    try:
        # Use provided API key or get from environment
        client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        
        if not client.api_key:
            raise ValueError("OpenAI API key not found")
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        response_text = response.choices[0].message.content
        return {
            "success": True,
            "content": response_text,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        error = str(e)
        status = "error"
        logger.error(f"Error calling OpenAI API: {error}")
        return {
            "success": False,
            "error": error
        }
    finally:
        duration = time.time() - start_time
        log_api_call(
            provider="openai",
            model=model,
            prompt_length=len(prompt),
            response_length=len(response_text),
            duration=duration,
            status=status,
            error=error,
            metadata={
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )

def call_gemini_pro(
    prompt: str,
    system_message: str = "You are a helpful assistant.",
    temperature: float = 0.7,
    max_tokens: int = 12000,
    json_mode: bool = False
) -> str:
    """Call the Google Gemini Pro API.
    
    Args:
        prompt: The user prompt to send to the API
        system_message: The system message to set the context
        temperature: The temperature parameter for generation
        max_tokens: The maximum number of tokens to generate
        json_mode: Whether to request structured JSON output
        
    Returns:
        The generated text response
    """
    model_name = "gemini-2.5-pro-preview-03-25"
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
    )
    
    # Combine system message and prompt
    full_prompt = f"{system_message}\n\n{prompt}"
    
    if json_mode:
        full_prompt += "\n\nPlease format your response as a valid JSON object."
    
    start_time = time.time()
    error = None
    response_text = ""
    status = "success"
    
    try:
        response = model.generate_content(full_prompt)
        response_text = response.text
    except Exception as e:
        error = str(e)
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        
        # Log the API call
        log_api_call(
            provider="gemini",
            model=model_name,
            prompt_length=len(full_prompt),
            response_length=len(response_text),
            duration=duration,
            status=status,
            error=error,
            metadata={
                "temperature": temperature,
                "max_tokens": max_tokens,
                "json_mode": json_mode
            }
        )
    
    return response_text

def parse_json_response(response: str) -> Dict[str, Any]:
    """
    Parse a JSON string from the model response.
    
    Args:
        response (str): The response string containing JSON
        
    Returns:
        Dict[str, Any]: Parsed JSON data
    """
    try:
        # Find JSON content between triple backticks if present
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            json_str = response[start:end].strip()
        else:
            json_str = response.strip()
            
        # Parse the JSON
        data = json.loads(json_str)
        return {
            "success": True,
            "data": data
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        return {
            "success": False,
            "error": f"JSON parsing error: {str(e)}",
            "raw_response": response
        }
    except Exception as e:
        logger.error(f"Unexpected error parsing response: {str(e)}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "raw_response": response
        }