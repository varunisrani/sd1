"""
Script Ingestion Module

This module handles the parsing and processing of film scripts,
extracting metadata, scenes, characters, and other relevant information.
"""

from sd1.src.script_ingestion.coordinator import ScriptIngestionCoordinator

# Expose key classes at the module level
__all__ = ['ScriptIngestionCoordinator'] 