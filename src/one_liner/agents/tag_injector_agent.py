from agents import Agent, Runner
from typing import Dict, Any, List
import json
import logging
import re
from ...base_config import AGENT_INSTRUCTIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TagInjectorAgent:
    def __init__(self):
        self.agent = Agent(
            name="Tag Injector",
            instructions=AGENT_INSTRUCTIONS["tag_injector"]
        )
        logger.info("Initialized TagInjectorAgent")
    
    def _clean_response(self, response: str) -> str:
        """Clean the response by removing markdown code block markers."""
        # Remove ```json or ``` markers from start and end
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        return response.strip()
    
    def _parse_markdown_tags(self, markdown_text: str) -> Dict[str, Any]:
        """Parse markdown-formatted tags into a structured dictionary."""
        logger.info("Parsing markdown-formatted tags")
        
        # Initialize the structure
        parsed_data = {
            "scene_tags": {},
            "cross_references": {},
            "story_elements": {}
        }
        
        try:
            # Extract scene tags
            scene_pattern = r"Scene (\d+): ((?:#\w+\s*)+)"
            scene_matches = re.finditer(scene_pattern, markdown_text)
            
            for match in scene_matches:
                scene_num = match.group(1)
                tags = [tag.strip('#') for tag in match.group(2).split()]
                parsed_data["scene_tags"][scene_num] = tags
            
            logger.info(f"Successfully parsed {len(parsed_data['scene_tags'])} scenes")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing markdown tags: {str(e)}")
            raise ValueError(f"Failed to parse markdown tags: {str(e)}")
    
    async def inject_tags(
        self,
        summaries: Dict[str, Any],
        call_sheets: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Inject summaries into call sheets and generate searchable tags."""
        # Define the expected JSON format
        json_format = '''
{
    "scene_tags": {
        "1": ["tag1", "tag2", "tag3"],
        "2": ["tag4", "tag5", "tag6"]
    },
    "cross_references": {
        "scene1": ["scene2", "scene3"],
        "scene2": ["scene1", "scene4"]
    },
    "story_elements": {
        "themes": ["theme1", "theme2"],
        "motifs": ["motif1", "motif2"]
    }
}'''
        
        prompt = f"""Process these scene summaries to:
        1. Generate searchable metadata tags
        2. Create cross-references between related scenes
        3. Identify key story elements and themes
        4. Link character appearances and story threads
        
        If call sheets are provided, embed relevant summaries and tags.
        
        IMPORTANT: Return the data in this exact JSON format:
        {json_format}
        
        Summary Data:
        {json.dumps(summaries, indent=2)}
        
        Call Sheets:
        {json.dumps(call_sheets, indent=2) if call_sheets else "No call sheets provided"}
        """
        
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received response from agent")
            
            try:
                # First try to parse as JSON
                cleaned_response = self._clean_response(result.final_output)
                try:
                    tag_data = json.loads(cleaned_response)
                    logger.info("Successfully parsed JSON response")
                except json.JSONDecodeError:
                    # If JSON parsing fails, try parsing as markdown
                    logger.info("JSON parsing failed, attempting to parse markdown format")
                    tag_data = self._parse_markdown_tags(result.final_output)
                    logger.info("Successfully parsed markdown format")
                
                # Process and validate the tag data
                processed_data = self._process_tags(tag_data, call_sheets)
                logger.info("Successfully processed tag data")
                
                return processed_data
                
            except Exception as e:
                logger.error(f"Failed to parse response: {str(e)}")
                logger.debug(f"Raw response: {result.final_output}")
                raise ValueError(f"Failed to generate valid tag data: {str(e)}\nRaw response: {result.final_output[:200]}...")
                
        except Exception as e:
            logger.error(f"Error in tag injection: {str(e)}")
            raise ValueError(f"Failed to generate valid tag data: {str(e)}")
    
    def _process_tags(
        self,
        tag_data: Dict[str, Any],
        call_sheets: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process and validate generated tags."""
        processed = {
            "scene_tags": {},
            "cross_references": {},
            "story_elements": {},
            "enhanced_call_sheets": [],
            "search_index": {}
        }
        
        # Process scene tags
        if "scene_tags" in tag_data:
            for scene_num, tags in tag_data["scene_tags"].items():
                # Normalize tags
                normalized_tags = [tag.lower().strip() for tag in tags]
                processed["scene_tags"][scene_num] = normalized_tags
                
                # Build search index
                for tag in normalized_tags:
                    if tag not in processed["search_index"]:
                        processed["search_index"][tag] = []
                    processed["search_index"][tag].append(scene_num)
        
        # Process cross-references
        if "cross_references" in tag_data:
            processed["cross_references"] = tag_data["cross_references"]
        
        # Process story elements
        if "story_elements" in tag_data:
            processed["story_elements"] = tag_data["story_elements"]
        
        # Enhance call sheets if provided
        if call_sheets and "call_sheet_enhancements" in tag_data:
            for i, sheet in enumerate(call_sheets):
                if i < len(tag_data["call_sheet_enhancements"]):
                    enhanced_sheet = sheet.copy()
                    enhanced_sheet.update(tag_data["call_sheet_enhancements"][i])
                    processed["enhanced_call_sheets"].append(enhanced_sheet)
        
        return processed 