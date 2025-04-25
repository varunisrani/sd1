from typing import Dict, Any, List
import json
import os
from datetime import datetime
from .agents.semantic_distiller_agent import SemanticDistillerAgent
from .agents.tag_injector_agent import TagInjectorAgent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OneLinerCoordinator:
    def __init__(self):
        self.semantic_distiller = SemanticDistillerAgent()
        self.tag_injector = TagInjectorAgent()
        
        # Create data directory if it doesn't exist
        os.makedirs("data/summaries", exist_ok=True)
        logger.info("Initialized OneLinerCoordinator")
    
    async def generate_one_liner(self, script_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate one-liner summaries for the script.
        This is the main entry point called by the UI."""
        try:
            # Extract the parsed data from the script ingestion results
            scene_data = script_data.get("parsed_data", {})
            if not scene_data:
                logger.error("No parsed script data found in input")
                raise ValueError("No parsed script data found")
                
            logger.info(f"Processing script with {len(scene_data)} scenes")
            
            # Process the script through the one-liner pipeline
            result = await self.process_script(scene_data)
            
            # Add formatted text representation
            result["formatted_text"] = self._format_summaries(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate one-liner: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "status": "failed",
                "formatted_text": f"Error: Failed to generate one-liner - {str(e)}"
            }
    
    def _format_summaries(self, result: Dict[str, Any]) -> str:
        """Format the summaries into readable text."""
        output = []
        
        # Add timestamp
        output.append(f"Generated on: {result.get('timestamp', 'Not specified')}\n")
        
        # Format summaries
        summaries = result.get("summaries", {}).get("summaries", [])
        if summaries:
            output.append("SCENE SUMMARIES")
            output.append("=" * 80 + "\n")
            
            for scene in summaries:
                scene_num = scene.get("scene_number", "Unknown")
                summary = scene.get("summary", "No summary available")
                output.extend([
                    f"Scene {scene_num}:",
                    f"{summary}\n"
                ])
        
        # Format story threads
        threads = result.get("summaries", {}).get("story_threads", {})
        if threads:
            output.extend([
                "\nSTORY THREADS",
                "=" * 80 + "\n"
            ])
            
            for thread, scenes in threads.items():
                output.append(f"{thread}:")
                output.append(f"  Appears in scenes: {', '.join(str(s) for s in scenes)}\n")
        
        # Format character arcs
        arcs = result.get("summaries", {}).get("character_arcs", {})
        if arcs:
            output.extend([
                "\nCHARACTER ARCS",
                "=" * 80 + "\n"
            ])
            
            for char, appearances in arcs.items():
                output.append(f"{char}:")
                for app in appearances:
                    scene = app.get("scene", "Unknown")
                    arc = app.get("arc_point", "No arc point")
                    emotion = app.get("emotional_state", "No emotional state")
                    output.append(f"  Scene {scene}: {arc} - {emotion}")
                output.append("")
        
        # Format tags
        tags = result.get("tags", {}).get("scene_tags", {})
        if tags:
            output.extend([
                "\nSCENE TAGS",
                "=" * 80 + "\n"
            ])
            
            for scene, scene_tags in tags.items():
                output.append(f"Scene {scene}:")
                output.append(f"  {', '.join(scene_tags)}\n")
        
        return "\n".join(output)
    
    async def process_script(
        self,
        scene_data: Dict[str, Any],
        call_sheets: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process script through the one-liner summarization pipeline."""
        try:
            # Step 1: Generate scene summaries
            logger.info("Starting semantic distillation...")
            summaries = await self.semantic_distiller.generate_summaries(scene_data)
            
            if "error" in summaries:
                logger.error(f"Semantic distillation failed: {summaries['error']}")
                return {
                    "error": summaries["error"],
                    "status": "failed",
                    "raw_response": summaries.get("raw_response", "No raw response captured")
                }
            
            # Step 2: Generate tags and enhance call sheets
            logger.info("Starting tag injection...")
            tagged_data = await self.tag_injector.inject_tags(summaries, call_sheets)
            
            # Combine results
            result = {
                "summaries": summaries,
                "tags": tagged_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Log any warnings
            if warnings := summaries.get("warnings", []):
                logger.warning(f"Generated summaries with warnings: {warnings}")
            
            # Save to disk if no warnings
            if not warnings:
                saved_file = self._save_to_disk(result)
                logger.info(f"Saved summaries to {saved_file}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in process_script: {str(e)}", exc_info=True)
            return {
                "error": f"Failed to parse agent response: {str(e)}",
                "status": "failed",
                "raw_response": getattr(e, "doc", "No raw response captured")
            }
        except Exception as e:
            logger.error(f"Error in process_script: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "status": "failed"
            }
    
    def _save_to_disk(self, data: Dict[str, Any]) -> str:
        """Save summary data to disk.
        
        Args:
            data: Dictionary containing summary data to save
            
        Returns:
            str: Path to the saved file
            
        Raises:
            IOError: If file cannot be written
            TypeError: If data is not JSON serializable
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/summaries/summary_{timestamp}.json"
            
            logger.info(f"Saving summary data to {filename}")
            
            # Validate data is JSON serializable
            try:
                json.dumps(data)
            except TypeError as e:
                logger.error(f"Data is not JSON serializable: {str(e)}")
                raise TypeError(f"Data is not JSON serializable: {str(e)}")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Successfully saved {os.path.getsize(filename)} bytes to {filename}")
            return filename 
            
        except IOError as e:
            logger.error(f"Failed to write file {filename}: {str(e)}", exc_info=True)
            raise IOError(f"Failed to write summary file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error saving summary data: {str(e)}", exc_info=True)
            raise 