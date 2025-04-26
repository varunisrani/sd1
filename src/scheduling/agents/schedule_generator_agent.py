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
            
            prompt = f"""You are a film production schedule generator. Your task is to create a detailed shooting schedule based on scene data, crew allocation, and location optimization.

IMPORTANT: You must respond with ONLY valid JSON data in the exact format specified below. Do not include any other text or explanations.

Required JSON format:
{{
    "schedule": [
        {{
            "day": number,
            "date": "YYYY-MM-DD",
            "scenes": [
                {{
                    "scene_id": "string",
                    "start_time": "HH:MM",
                    "end_time": "HH:MM",
                    "location_id": "string",
                    "crew_ids": ["crew1", "crew2"],
                    "equipment_ids": ["equip1", "equip2"],
                    "setup_time": "HH:MM",
                    "wrap_time": "HH:MM",
                    "breaks": [
                        {{
                            "type": "string",
                            "start_time": "HH:MM",
                            "end_time": "HH:MM"
                        }}
                    ]
                }}
            ]
        }}
    ],
    "calendar_data": {{
        "events": [
            {{
                "id": "string",
                "title": "string",
                "start": "YYYY-MM-DDTHH:MM:SS",
                "end": "YYYY-MM-DDTHH:MM:SS",
                "resourceId": "string",
                "color": "string",
                "textColor": "string",
                "description": "string",
                "location": "string",
                "crew": ["crew1", "crew2"],
                "equipment": ["equip1", "equip2"]
            }}
        ],
        "resources": [
            {{
                "id": "string",
                "title": "string",
                "type": "string"
            }}
        ]
    }},
    "gantt_data": {{
        "tasks": [
            {{
                "id": "string",
                "text": "string",
                "start_date": "YYYY-MM-DD HH:MM",
                "end_date": "YYYY-MM-DD HH:MM",
                "progress": number,
                "parent": "string",
                "dependencies": ["task1", "task2"],
                "resource_ids": ["resource1", "resource2"],
                "type": "string",
                "color": "string"
            }}
        ],
        "links": [
            {{
                "id": "string",
                "source": "string",
                "target": "string",
                "type": "string"
            }}
        ],
        "resources": [
            {{
                "id": "string",
                "name": "string",
                "type": "string",
                "calendar_id": "string"
            }}
        ]
    }},
    "summary": {{
        "total_days": number,
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "total_scenes": number,
        "total_pages": number,
        "total_runtime_minutes": number
    }},
    "optimization_notes": ["note1", "note2"]
}}

Consider these scheduling factors:
        - Scene complexity and estimated duration
        - Location availability and optimization
        - Crew availability and conflicts
        - Equipment availability
        - Weather dependencies
        - Daylight requirements
        - Meal breaks and union regulations
        
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
            schedule_result = json.loads(cleaned_response)
            
            # Validate the required fields
            required_fields = ['schedule', 'calendar_data', 'gantt_data', 'summary']
            for field in required_fields:
                if field not in schedule_result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate schedule data
            for day in schedule_result.get('schedule', []):
                required_day_fields = ['day', 'date', 'scenes']
                for field in required_day_fields:
                    if field not in day:
                        raise ValueError(f"Missing required day field: {field}")
                
                for scene in day.get('scenes', []):
                    required_scene_fields = ['scene_id', 'start_time', 'end_time', 'location_id']
                    for field in required_scene_fields:
                        if field not in scene:
                            raise ValueError(f"Missing required scene field: {field}")
            
            # Validate calendar data
            calendar_data = schedule_result.get('calendar_data', {})
            if not isinstance(calendar_data.get('events'), list):
                raise ValueError("Calendar data must contain events array")
            if not isinstance(calendar_data.get('resources'), list):
                raise ValueError("Calendar data must contain resources array")
            
            # Validate Gantt data
            gantt_data = schedule_result.get('gantt_data', {})
            if not isinstance(gantt_data.get('tasks'), list):
                raise ValueError("Gantt data must contain tasks array")
            if not isinstance(gantt_data.get('links'), list):
                raise ValueError("Gantt data must contain links array")
            if not isinstance(gantt_data.get('resources'), list):
                raise ValueError("Gantt data must contain resources array")
            
            # Validate summary data
            summary = schedule_result.get('summary', {})
            required_summary_fields = ['total_days', 'start_date', 'end_date', 'total_scenes']
            for field in required_summary_fields:
                if field not in summary:
                    raise ValueError(f"Missing required summary field: {field}")
            
            # Validate and adjust dates
            schedule_result = self._validate_and_adjust_dates(schedule_result, start_date)
            logger.info("Schedule dates validated and adjusted")
            
            return schedule_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse schedule result: {str(e)}")
            logger.debug(f"Raw response: {result.final_output}")
            
            # Try to create a basic valid response
            logger.info("Attempting to create fallback response")
            start_date = datetime.now()
            fallback_response = {
                "schedule": [
                    {
                        "day": 1,
                        "date": start_date.strftime("%Y-%m-%d"),
                        "scenes": []
                    }
                ],
                "calendar_data": {
                    "events": [],
                    "resources": []
                },
                "gantt_data": {
                    "tasks": [],
                    "links": [],
                    "resources": []
                },
                "summary": {
                    "total_days": 1,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": start_date.strftime("%Y-%m-%d"),
                    "total_scenes": len(scenes),
                    "total_pages": 0,
                    "total_runtime_minutes": 0
                },
                "optimization_notes": ["Generated fallback response due to API parsing error"]
            }
            return fallback_response
            
        except Exception as e:
            logger.error(f"Error in generate_schedule: {str(e)}")
            raise
    
    def _clean_and_extract_json(self, text: str) -> str:
        """Extract JSON from text response."""
        try:
            # Find the first '{' and last '}'
            start = text.find('{')
            end = text.rfind('}')
            
            if start == -1 or end == -1:
                return ""
            
            # Extract the JSON substring
            json_str = text[start:end + 1]
            
            # Validate it's parseable
            json.loads(json_str)
            
            return json_str
            
        except Exception as e:
            logger.error(f"Error cleaning JSON: {str(e)}")
            return ""
    
    def _validate_and_adjust_dates(self, schedule_result: Dict[str, Any], start_date: str) -> Dict[str, Any]:
        """Validate and adjust dates in the schedule to ensure they are sequential and start from the given date."""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            
            if "schedule" not in schedule_result:
                return schedule_result
            
            for i, day in enumerate(schedule_result["schedule"]):
                # Set the correct date
                current_date = start + timedelta(days=i)
                day["date"] = current_date.strftime("%Y-%m-%d")
                day["day"] = i + 1
                
                # Validate time formats
                for scene in day.get("scenes", []):
                    for time_field in ["start_time", "end_time", "setup_time", "wrap_time"]:
                        if time_field in scene:
                            try:
                                datetime.strptime(scene[time_field], "%H:%M")
                            except ValueError:
                                scene[time_field] = "00:00"  # Set default if invalid
                    
                    # Validate crew call times
                    for call in scene.get("breaks", []):
                        if "start_time" in call and "end_time" in call:
                            try:
                                datetime.strptime(call["start_time"], "%H:%M")
                                datetime.strptime(call["end_time"], "%H:%M")
                            except ValueError:
                                call["start_time"] = "07:00"  # Set default if invalid
                                call["end_time"] = "12:00"  # Set default if invalid
            
            return schedule_result
            
        except Exception as e:
            logger.error(f"Error validating schedule dates: {str(e)}", exc_info=True)
            return schedule_result  # Return original if validation fails