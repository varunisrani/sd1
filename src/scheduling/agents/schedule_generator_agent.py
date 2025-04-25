import logging
from agents import Agent, Runner
from typing import Dict, Any, List
import json
import re
from datetime import datetime, timedelta
from ...base_config import AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)

class ScheduleGeneratorAgent:
    def __init__(self):
        self.agent = Agent(
            name="Schedule Generator",
            instructions=AGENT_INSTRUCTIONS["schedule_generator"]
        )
        logger.info("ScheduleGeneratorAgent initialized")
    
    async def generate_schedule(
        self,
        scene_data: Dict[str, Any],
        crew_allocation: Dict[str, Any],
        location_optimization: Dict[str, Any],
        start_date: str,
        constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate a detailed shooting schedule."""
        try:
            logger.info(f"Starting schedule generation from {start_date}")
            
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
            
            prompt = f"""You are a film production schedule generator. Your task is to create a detailed shooting schedule.

IMPORTANT: You must respond with ONLY valid JSON data in the exact format specified below. Do not include any other text or explanations.

Required JSON format:
{{
    "schedule": [
        {{
            "date": "YYYY-MM-DD",
            "day_number": number,
            "scenes": [
                {{
                    "scene_id": "string",
                    "location": "string",
                    "start_time": "HH:MM",
                    "end_time": "HH:MM",
                    "setup_time": "HH:MM",
                    "wrap_time": "HH:MM",
                    "crew_calls": [
                        {{
                            "crew_member": "string",
                            "call_time": "HH:MM"
                        }}
                    ],
                    "equipment_requirements": ["string"],
                    "notes": ["string"]
                }}
            ],
            "day_start": "HH:MM",
            "day_wrap": "HH:MM",
            "total_pages": number,
            "company_moves": number,
            "notes": ["string"]
        }}
    ],
    "total_days": number,
    "schedule_notes": ["string"],
    "efficiency_metrics": {{
        "company_moves_per_day": number,
        "average_pages_per_day": number,
        "location_optimization_score": number
    }}
}}

Consider these requirements:
- Maximum shooting hours per day
- Required meal breaks and turnaround time
- Location grouping and company moves
- Actor availability and daylight requirements
- Weather considerations and seasonal factors

Scene Data:
{json.dumps(scenes, indent=2)}

Crew Allocation:
{json.dumps(crew_allocation, indent=2)}

Location Optimization:
{json.dumps(location_optimization, indent=2)}

Start Date: {start_date}

Additional Constraints:
{json.dumps(constraints, indent=2) if constraints else "No specific constraints provided"}

Remember: Return ONLY the JSON data structure. No other text."""

            result = await Runner.run(self.agent, prompt)
            
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
            schedule_data = json.loads(cleaned_response)
            logger.info("Successfully parsed schedule data")
            
            # Validate required fields
            required_fields = ['schedule', 'total_days']
            for field in required_fields:
                if field not in schedule_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate schedule entries
            for day in schedule_data.get('schedule', []):
                required_day_fields = ['date', 'day_number', 'scenes']
                for field in required_day_fields:
                    if field not in day:
                        raise ValueError(f"Missing required day field: {field}")
                
                # Validate scenes in each day
                for scene in day.get('scenes', []):
                    required_scene_fields = ['scene_id', 'start_time', 'end_time']
                    for field in required_scene_fields:
                        if field not in scene:
                            raise ValueError(f"Missing required scene field: {field}")
            
            # Validate and adjust dates
            schedule_data = self._validate_and_adjust_dates(schedule_data, start_date)
            logger.info("Schedule dates validated and adjusted")
            
            return schedule_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse schedule data: {str(e)}")
            logger.debug(f"Raw response: {result.final_output}")
            
            # Create a basic valid response
            logger.info("Generating fallback schedule")
            fallback_response = self._generate_fallback_schedule(scenes, start_date)
            return fallback_response
            
        except Exception as e:
            logger.error(f"Error during schedule generation: {str(e)}", exc_info=True)
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
    
    def _generate_fallback_schedule(self, scenes: List[Dict[str, Any]], start_date: str) -> Dict[str, Any]:
        """Generate a basic valid schedule when the API response fails."""
        logger.info("Generating fallback schedule")
        
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            schedule = []
            scenes_per_day = 3  # Conservative estimate
            
            # Group scenes into days
            for i in range(0, len(scenes), scenes_per_day):
                day_scenes = scenes[i:i + scenes_per_day]
                current_date = start + timedelta(days=len(schedule))
                
                day_schedule = {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "day_number": len(schedule) + 1,
                    "scenes": [],
                    "day_start": "08:00",
                    "day_wrap": "18:00",
                    "total_pages": len(day_scenes),
                    "company_moves": 0,
                    "notes": ["Fallback schedule - basic timing"]
                }
                
                # Schedule scenes throughout the day
                for idx, scene in enumerate(day_scenes):
                    scene_id = scene.get('id') or scene.get('scene_id', f"scene_{i+idx}")
                    start_hour = 8 + (idx * 3)  # 3 hours per scene
                    
                    scene_schedule = {
                        "scene_id": scene_id,
                        "location": scene.get('location', {}).get('name', 'Default Location'),
                        "start_time": f"{start_hour:02d}:00",
                        "end_time": f"{start_hour+2:02d}:30",
                        "setup_time": f"{start_hour-1:02d}:30",
                        "wrap_time": f"{start_hour+3:02d}:00",
                        "crew_calls": [
                            {"crew_member": "All Crew", "call_time": "07:30"}
                        ],
                        "equipment_requirements": ["Standard Package"],
                        "notes": ["Basic schedule - adjust as needed"]
                    }
                    
                    day_schedule["scenes"].append(scene_schedule)
                
                schedule.append(day_schedule)
            
            total_days = len(schedule)
            
            return {
                "schedule": schedule,
                "total_days": total_days,
                "schedule_notes": [
                    "Fallback schedule generated due to API error",
                    "Conservative estimate of 3 scenes per day",
                    "Standard 10-hour shooting days"
                ],
                "efficiency_metrics": {
                    "company_moves_per_day": 0,
                    "average_pages_per_day": scenes_per_day,
                    "location_optimization_score": 0.5
                },
                "is_fallback": True
            }
            
        except Exception as e:
            logger.error(f"Error generating fallback schedule: {str(e)}", exc_info=True)
            raise
    
    def _validate_and_adjust_dates(self, schedule_data: Dict[str, Any], start_date: str) -> Dict[str, Any]:
        """Validate and adjust dates in the schedule to ensure they are sequential and start from the given date."""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            
            if "schedule" not in schedule_data:
                return schedule_data
            
            for i, day in enumerate(schedule_data["schedule"]):
                # Set the correct date
                current_date = start + timedelta(days=i)
                day["date"] = current_date.strftime("%Y-%m-%d")
                day["day_number"] = i + 1
                
                # Validate time formats
                for scene in day.get("scenes", []):
                    for time_field in ["start_time", "end_time", "setup_time", "wrap_time"]:
                        if time_field in scene:
                            try:
                                datetime.strptime(scene[time_field], "%H:%M")
                            except ValueError:
                                scene[time_field] = "00:00"  # Set default if invalid
                    
                    # Validate crew call times
                    for call in scene.get("crew_calls", []):
                        if "call_time" in call:
                            try:
                                datetime.strptime(call["call_time"], "%H:%M")
                            except ValueError:
                                call["call_time"] = "07:00"  # Set default if invalid
            
            return schedule_data
            
        except Exception as e:
            logger.error(f"Error validating schedule dates: {str(e)}", exc_info=True)
            return schedule_data  # Return original if validation fails