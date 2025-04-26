import logging
from typing import Dict, Any, Optional
import json
import os
from datetime import datetime
from .agents.location_optimizer_agent import LocationOptimizerAgent
from .agents.crew_allocator_agent import CrewAllocatorAgent
from .agents.schedule_generator_agent import ScheduleGeneratorAgent

logger = logging.getLogger(__name__)

class SchedulingCoordinator:
    def __init__(self):
        logger.info("Initializing SchedulingCoordinator")
        self.location_optimizer = LocationOptimizerAgent()
        self.crew_allocator = CrewAllocatorAgent()
        self.schedule_generator = ScheduleGeneratorAgent()
        
        # Create necessary data directories
        os.makedirs("data/schedules", exist_ok=True)
        os.makedirs("data/schedules/calendar", exist_ok=True)
        os.makedirs("data/schedules/gantt", exist_ok=True)
        logger.info("Schedule data directories ensured")
    
    def _validate_scene_data(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate scene data structure and return processed scenes."""
        if not isinstance(scene_data, dict):
            raise ValueError("Scene data must be a dictionary")
        
        if 'parsed_data' not in scene_data and 'scenes' not in scene_data:
            raise ValueError("Scene data must contain either 'parsed_data' or 'scenes' key")
        
        # If we have parsed_data, extract scenes from it
        scenes = scene_data.get('scenes', [])
        if not scenes and 'parsed_data' in scene_data:
            parsed_data = scene_data['parsed_data']
            if isinstance(parsed_data, dict) and 'scenes' in parsed_data:
                scenes = parsed_data['scenes']
        
        if not scenes or not isinstance(scenes, list):
            raise ValueError("No valid scenes found in scene data")
        
        logger.info(f"Found {len(scenes)} scenes in input data")
        
        # Return processed scene data
        return {
            'scenes': scenes,
            'metadata': scene_data.get('metadata', {}),
            'original_data': scene_data
        }
    
    def _validate_crew_data(self, crew_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate crew data structure and return processed crew data."""
        if not isinstance(crew_data, dict):
            raise ValueError("Crew data must be a dictionary")
        
        # Check for either direct crew list or nested structure
        crew_list = crew_data.get('crew', [])
        if not crew_list and 'character_breakdown' in crew_data:
            crew_list = crew_data['character_breakdown'].get('crew', [])
        
        if not crew_list:
            logger.warning("No crew data found, will use default crew structure")
            crew_list = [
                {"name": "Director", "role": "Director"},
                {"name": "DP", "role": "Director of Photography"},
                {"name": "Sound Mixer", "role": "Sound"},
                {"name": "Gaffer", "role": "Lighting"},
                {"name": "Key Grip", "role": "Grip"}
            ]
        
        return {
            'crew': crew_list,
            'metadata': crew_data.get('metadata', {}),
            'original_data': crew_data
        }
    
    def _validate_start_date(self, start_date: str) -> str:
        """Validate and return the start date."""
        if not start_date:
            today = datetime.now()
            start_date = today.strftime("%Y-%m-%d")
            logger.warning(f"No start date provided, using today's date: {start_date}")
            return start_date
            
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            return start_date
        except ValueError:
            raise ValueError("Invalid start date format. Use YYYY-MM-DD")
    
    def _validate_schedule_data(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Validate schedule data structure including calendar and Gantt data."""
        try:
            logger.info("Validating schedule data structure")
            
            # Validate main schedule structure
            if not isinstance(schedule.get('schedule'), list):
                raise ValueError("Schedule must contain a list of shooting days")
            
            # Validate calendar data
            calendar_data = schedule.get('calendar_data', {})
            if not isinstance(calendar_data.get('events'), list):
                logger.warning("Missing or invalid calendar events")
                calendar_data['events'] = []
            if not isinstance(calendar_data.get('resources'), list):
                logger.warning("Missing or invalid calendar resources")
                calendar_data['resources'] = []
            
            # Validate Gantt data
            gantt_data = schedule.get('gantt_data', {})
            if not isinstance(gantt_data.get('tasks'), list):
                logger.warning("Missing or invalid Gantt tasks")
                gantt_data['tasks'] = []
            if not isinstance(gantt_data.get('links'), list):
                logger.warning("Missing or invalid Gantt links")
                gantt_data['links'] = []
            if not isinstance(gantt_data.get('resources'), list):
                logger.warning("Missing or invalid Gantt resources")
                gantt_data['resources'] = []
            
            # Validate summary data
            summary = schedule.get('summary', {})
            required_summary_fields = ['total_days', 'start_date', 'end_date', 'total_scenes']
            for field in required_summary_fields:
                if field not in summary:
                    logger.warning(f"Missing summary field: {field}")
                    if field in ['total_days', 'total_scenes']:
                        summary[field] = 0
                    elif field in ['start_date', 'end_date']:
                        summary[field] = datetime.now().strftime("%Y-%m-%d")
            
            return schedule
            
        except Exception as e:
            logger.error(f"Error validating schedule data: {str(e)}")
            raise
    
    async def generate_schedule(
        self,
        scene_data: Dict[str, Any],
        crew_data: Dict[str, Any],
        start_date: str,
        location_constraints: Optional[Dict[str, Any]] = None,
        equipment_inventory: Optional[Dict[str, Any]] = None,
        schedule_constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate complete shooting schedule through the scheduling pipeline."""
        try:
            logger.info("Starting schedule generation pipeline")
            
            # Validate and prepare input data
            try:
                logger.info("Validating input data")
                processed_scene_data = self._validate_scene_data(scene_data)
                processed_crew_data = self._validate_crew_data(crew_data)
                validated_start_date = self._validate_start_date(start_date)
                logger.info("Input data validated and prepared")
                
            except ValueError as e:
                logger.error(f"Input validation failed: {str(e)}")
                raise
            
            # Step 1: Optimize locations
            logger.info("Step 1: Optimizing locations")
            location_plan = await self.location_optimizer.optimize_locations(
                processed_scene_data,
                location_constraints
            )
            logger.info("Location optimization completed")
            
            # Step 2: Allocate crew and equipment
            logger.info("Step 2: Allocating crew and equipment")
            crew_allocation = await self.crew_allocator.allocate_crew(
                processed_scene_data,
                processed_crew_data,
                equipment_inventory
            )
            logger.info("Crew allocation completed")
            
            # Step 3: Generate detailed schedule
            logger.info("Step 3: Generating detailed schedule")
            schedule = await self.schedule_generator.generate_schedule(
                processed_scene_data,
                crew_allocation,
                location_plan,
                validated_start_date,
                schedule_constraints
            )
            
            # Validate the schedule data structure
            schedule = self._validate_schedule_data(schedule)
            logger.info("Schedule generation and validation completed")
            
            # Combine all results
            result = {
                "location_plan": location_plan,
                "crew_allocation": crew_allocation,
                "schedule": schedule.get('schedule', []),
                "calendar_data": schedule.get('calendar_data', {}),
                "gantt_data": schedule.get('gantt_data', {}),
                "summary": schedule.get('summary', {}),
                "optimization_notes": schedule.get('optimization_notes', []),
                "timestamp": datetime.now().isoformat()
            }
            
            # Save to disk
            logger.info("Saving schedule data to disk")
            saved_files = self._save_to_disk(result)
            result["saved_files"] = saved_files
            
            return result
            
        except Exception as e:
            logger.error(f"Error in schedule generation pipeline: {str(e)}", exc_info=True)
            raise
    
    def _save_to_disk(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Save schedule data to disk in multiple formats."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_files = {}
            
            # Save main schedule
            schedule_file = f"data/schedules/schedule_{timestamp}.json"
            with open(schedule_file, "w") as f:
                json.dump(data, f, indent=2)
            saved_files['main'] = schedule_file
            
            # Save calendar data separately
            if 'calendar_data' in data:
                calendar_file = f"data/schedules/calendar/calendar_{timestamp}.json"
                with open(calendar_file, "w") as f:
                    json.dump(data['calendar_data'], f, indent=2)
                saved_files['calendar'] = calendar_file
            
            # Save Gantt data separately
            if 'gantt_data' in data:
                gantt_file = f"data/schedules/gantt/gantt_{timestamp}.json"
                with open(gantt_file, "w") as f:
                    json.dump(data['gantt_data'], f, indent=2)
                saved_files['gantt'] = gantt_file
            
            logger.info(f"Schedule data saved to multiple files")
            return saved_files
            
        except Exception as e:
            logger.error(f"Error saving schedule data to disk: {str(e)}")
            raise 