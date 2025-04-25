import logging
from agents import Agent, Runner
from typing import Dict, Any, List
import json
import re
from ...base_config import AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)

class CrewAllocatorAgent:
    def __init__(self):
        self.agent = Agent(
            name="Crew Allocator",
            instructions=AGENT_INSTRUCTIONS["crew_allocator"]
        )
        logger.info("CrewAllocatorAgent initialized")
    
    async def allocate_crew(
        self, 
        scene_data: Dict[str, Any], 
        crew_availability: Dict[str, Any],
        equipment_inventory: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Allocate crew and equipment to scenes based on availability and requirements."""
        try:
            logger.info("Starting crew allocation")
            
            # Extract scenes and validate input
            scenes = []
            if isinstance(scene_data, dict):
                if 'scenes' in scene_data:
                    scenes = scene_data['scenes']
                elif 'parsed_data' in scene_data and isinstance(scene_data['parsed_data'], dict):
                    scenes = scene_data['parsed_data'].get('scenes', [])
            
            if not scenes:
                raise ValueError("No scenes provided in scene_data")
            
            logger.debug(f"Processing {len(scenes)} scenes")
            
            prompt = f"""You are a film production crew allocator. Your task is to create a detailed crew and equipment allocation plan.

IMPORTANT: You must respond with ONLY valid JSON data in the exact format specified below. Do not include any other text or explanations.

Required JSON format:
{{
    "crew_assignments": [
        {{
            "crew_member": "string",
            "role": "string",
            "assigned_scenes": ["scene_id1", "scene_id2"],
            "work_hours": number,
            "turnaround_hours": number,
            "meal_break_interval": number,
            "equipment_assigned": ["equipment1", "equipment2"]
        }}
    ],
    "equipment_assignments": [
        {{
            "equipment_id": "string",
            "type": "string",
            "assigned_scenes": ["scene_id1", "scene_id2"],
            "setup_time_minutes": number,
            "assigned_crew": ["crew_member1", "crew_member2"]
        }}
    ],
    "department_schedules": {{
        "camera": {{
            "crew": ["crew_member1", "crew_member2"],
            "equipment": ["equipment1", "equipment2"],
            "notes": ["note1", "note2"]
        }},
        "sound": {{
            "crew": ["crew_member1", "crew_member2"],
            "equipment": ["equipment1", "equipment2"],
            "notes": ["note1", "note2"]
        }}
    }},
    "allocation_notes": ["note1", "note2"]
}}

Consider these requirements:
        - Actor availability windows
        - Crew work hour restrictions and union rules
        - Equipment sharing optimization
        - Department-specific requirements
        - Setup and wrap time requirements
        
        Scene Data:
{json.dumps(scenes, indent=2)}
        
        Crew Availability:
        {json.dumps(crew_availability, indent=2)}
        
        Equipment Inventory:
        {json.dumps(equipment_inventory, indent=2) if equipment_inventory else "Using standard equipment package"}

Remember: Return ONLY the JSON data structure. No other text."""
            
            result = await Runner.run(self.agent, prompt)
            try:
                # Log the raw response for debugging
                logger.debug(f"Raw API response: {result.final_output}")
                
                # First, validate that we have a response
                if not result.final_output or not result.final_output.strip():
                    raise ValueError("Empty response from API")
                
                # Clean the response - try to extract JSON
                cleaned_response = self._clean_and_extract_json(result.final_output)
                if not cleaned_response:
                    raise ValueError("Could not find valid JSON in response")
                
                # Try to parse the JSON
                allocation_result = json.loads(cleaned_response)
                logger.info("Successfully parsed crew allocation result")
                
                # Validate required fields
                required_fields = ['crew_assignments', 'equipment_assignments']
                for field in required_fields:
                    if field not in allocation_result:
                        raise ValueError(f"Missing required field: {field}")
            
                # Validate crew assignments
                for assignment in allocation_result.get('crew_assignments', []):
                    required_fields = ['crew_member', 'role', 'assigned_scenes']
                    for field in required_fields:
                        if field not in assignment:
                            raise ValueError(f"Missing required crew assignment field: {field}")
                
                # Validate the crew assignments against union rules
                self._validate_crew_assignments(allocation_result)
                logger.info("Crew assignments validated")
            
                return allocation_result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse crew allocation result: {str(e)}")
                logger.debug(f"Raw response: {result.final_output}")
                
                # Create a basic valid response
                logger.info("Generating fallback crew allocation")
                fallback_response = self._generate_fallback_allocation(scenes, crew_availability)
                return fallback_response
                
        except Exception as e:
            logger.error(f"Error during crew allocation: {str(e)}", exc_info=True)
            raise
    
    def _clean_and_extract_json(self, text: str) -> str:
        """Clean and extract JSON from text response."""
        # First, try to find JSON between triple backticks
        matches = re.findall(r'```(?:json)?\s*({\s*.*?\s*})\s*```', text, re.DOTALL)
        if matches:
            return matches[0]
        
        # Then try to find JSON between single backticks
        matches = re.findall(r'`({\s*.*?\s*})`', text, re.DOTALL)
        if matches:
            return matches[0]
        
        # Then try to find any JSON object
        matches = re.findall(r'({\s*"[^"]+"\s*:[\s\S]*})', text)
        if matches:
            return matches[0]
        
        # Try to find anything that looks like JSON
        matches = re.findall(r'({[\s\S]*})', text)
        if matches:
            return matches[0]
        
        # If we can't find JSON, return the original text
        return text.strip()
    
    def _generate_fallback_allocation(self, scenes: List[Dict[str, Any]], crew_availability: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a basic valid crew allocation when the API response fails."""
        logger.info("Generating fallback crew allocation")
        
        # Extract available crew members
        crew_members = []
        if isinstance(crew_availability, dict):
            crew_members = crew_availability.get('crew', [])
            if not crew_members and 'character_breakdown' in crew_availability:
                crew_members = crew_availability['character_breakdown'].get('crew', [])
        
        if not crew_members:
            # Create basic crew structure
            crew_members = [
                {"name": "Director", "role": "Director"},
                {"name": "DP", "role": "Director of Photography"},
                {"name": "Sound Mixer", "role": "Sound"},
                {"name": "Gaffer", "role": "Lighting"},
                {"name": "Key Grip", "role": "Grip"}
            ]
        
        # Create basic allocation
        crew_assignments = []
        for crew in crew_members:
            crew_name = crew.get('name', crew) if isinstance(crew, dict) else crew
            crew_role = crew.get('role', 'Crew') if isinstance(crew, dict) else 'Crew'
            
            crew_assignments.append({
                "crew_member": crew_name,
                "role": crew_role,
                "assigned_scenes": [scene.get('id', 'unknown') for scene in scenes],
                "work_hours": 12,
                "turnaround_hours": 12,
                "meal_break_interval": 6,
                "equipment_assigned": []
            })
        
        return {
            "crew_assignments": crew_assignments,
            "equipment_assignments": [],
            "department_schedules": {
                "camera": {"crew": [], "equipment": [], "notes": ["Fallback schedule"]},
                "sound": {"crew": [], "equipment": [], "notes": ["Fallback schedule"]},
                "lighting": {"crew": [], "equipment": [], "notes": ["Fallback schedule"]}
            },
            "allocation_notes": ["Generated fallback allocation due to API parsing error"],
            "is_fallback": True
        }
    
    def _validate_crew_assignments(self, allocation: Dict[str, Any]) -> None:
        """Validate crew assignments against common union rules."""
        try:
            logger.info("Starting crew assignment validation")
            violations = []
            
            if "crew_assignments" not in allocation:
                logger.warning("No crew assignments found in allocation data")
                return
            
            for assignment in allocation["crew_assignments"]:
                crew_member = assignment.get('crew_member', 'Unknown crew member')
                
                # Check for minimum turnaround time (typically 10 hours)
                if assignment.get("turnaround_hours", 10) < 10:
                    msg = f"Insufficient turnaround time for {crew_member}"
                    logger.warning(msg)
                    violations.append(msg)
                
                # Check for maximum work hours (typically 12 hours)
                if assignment.get("work_hours", 0) > 12:
                    msg = f"Excessive work hours for {crew_member}"
                    logger.warning(msg)
                    violations.append(msg)
                
                # Check for meal breaks (every 6 hours)
                if assignment.get("meal_break_interval", 6) > 6:
                    msg = f"Missing meal break for {crew_member}"
                    logger.warning(msg)
                    violations.append(msg)
            
            if violations:
                logger.warning(f"Found {len(violations)} union rule violations")
                allocation["union_rule_violations"] = violations 
            else:
                logger.info("No union rule violations found")
        except Exception as e:
            logger.error(f"Error during crew assignment validation: {str(e)}", exc_info=True)
            raise 