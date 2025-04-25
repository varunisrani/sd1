from typing import Dict, Any
import json
import os
import logging
from .agents.parser_agent import ScriptParserAgent
from .agents.metadata_agent import MetadataAgent
from .agents.validator_agent import ValidatorAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScriptIngestionCoordinator:
    def __init__(self):
        logger.info("Initializing ScriptIngestionCoordinator")
        self.parser = ScriptParserAgent()
        self.metadata_extractor = MetadataAgent()
        self.validator = ValidatorAgent()
        
        # Create data directory if it doesn't exist
        os.makedirs("data/scripts", exist_ok=True)
        logger.info("Data directory ensured at data/scripts")
    
    async def process_script(self, script_text: str) -> Dict[str, Any]:
        """Process a script through the complete ingestion pipeline."""
        logger.info("Starting script processing pipeline")
        
        try:
            # Step 1: Parse the script
            logger.info("Step 1: Parsing script")
            parsed_data = await self.parser.parse_script(script_text)
            
            # Check for parsing errors
            if "error" in parsed_data:
                logger.error(f"Script parsing failed: {parsed_data['error']}")
                return parsed_data
            
            # Step 2: Extract metadata
            logger.info("Step 2: Extracting metadata")
            metadata = await self.metadata_extractor.extract_metadata(parsed_data)
            
            # Check for metadata errors
            if "error" in metadata:
                logger.error(f"Metadata extraction failed: {metadata['error']}")
                return metadata
            
            # Step 3: Validate the data
            logger.info("Step 3: Validating data")
            validation_result = await self.validator.validate_data(parsed_data, metadata)
            
            # Combine all results
            result = {
                "parsed_data": parsed_data,
                "metadata": metadata,
                "validation": validation_result,
                "processing_log": {
                    "steps_completed": ["parsing", "metadata", "validation"],
                    "scenes_processed": len(parsed_data.get("scenes", [])),
                    "status": "success"
                }
            }
            
            # Save to disk if valid
            if validation_result.get("is_valid", False):
                logger.info("Data validation passed, saving to disk")
                saved_path = self._save_to_disk(result)
                result["saved_path"] = saved_path
            else:
                logger.warning("Data validation failed, skipping save to disk")
            
            logger.info("Script processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Script processing failed with error: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "status": "failed",
                "processing_log": {
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                }
            }
    
    def _save_to_disk(self, data: Dict[str, Any]) -> str:
        """Save processed data to disk."""
        try:
            timestamp = data["metadata"].get("timestamp", "unknown")
            filename = f"data/scripts/script_{timestamp}.json"
            
            logger.info(f"Saving processed data to {filename}")
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info("Data saved successfully")
            return filename
        except Exception as e:
            logger.error(f"Failed to save data to disk: {str(e)}")
            raise 