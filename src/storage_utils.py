import os
import json
import logging
import streamlit as st
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Storage directory
STORAGE_DIR = "static/storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

def save_to_storage(data: dict, filename: str):
    """Save data to storage with timestamp."""
    filepath = os.path.join(STORAGE_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    return filepath

def load_from_storage(filename: str) -> dict:
    """Load data from storage."""
    filepath = os.path.join(STORAGE_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}

def clear_storage_data() -> bool:
    """Clear all stored data and reset the application state."""
    try:
        # Clear storage directory
        if os.path.exists(STORAGE_DIR):
            for filename in os.listdir(STORAGE_DIR):
                file_path = os.path.join(STORAGE_DIR, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"Removed file: {file_path}")
                except Exception as e:
                    logger.error(f"Error removing file {file_path}: {str(e)}")

        # Clear data directories
        data_dirs = [
            "data/storyboards",
            "data/exports",
            "data/scripts/metadata",
            "data/scripts/validation",
            "data/character_profiles",
            "data/relationship_maps",
            "data/scene_matrices",
            "data/schedules/calendar",
            "data/schedules/gantt",
            "static/storage/storyboards"
        ]

        for directory in data_dirs:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            logger.info(f"Removed file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error removing file {file_path}: {str(e)}")

        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]

        logger.info("Successfully cleared all storage data")
        return True
    except Exception as e:
        logger.error(f"Error clearing storage: {str(e)}")
        return False 