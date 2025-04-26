import logging
from agents import Agent, Runner
from typing import Dict, Any, List
import json
import networkx as nx
from geopy.distance import geodesic
from ...base_config import AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)

class LocationOptimizerAgent:
    def __init__(self):
        self.agent = Agent(
            name="Location Optimizer",
            instructions=AGENT_INSTRUCTIONS["location_optimizer"]
        )
        logger.info("LocationOptimizerAgent initialized")
    
    async def optimize_locations(self, scene_data: Dict[str, Any], location_constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        """Optimize shooting locations and sequence."""
        try:
            logger.info("Starting location optimization")
            
            # Extract scenes from the scene data
            scenes = []
            if isinstance(scene_data, dict):
                if 'scenes' in scene_data:
                    scenes = scene_data['scenes']
                elif 'parsed_data' in scene_data and isinstance(scene_data['parsed_data'], dict):
                    scenes = scene_data['parsed_data'].get('scenes', [])
            
            if not scenes:
                raise ValueError("No scenes provided in scene_data")
            
            logger.debug(f"Processing {len(scenes)} scenes")
            
            # Extract location information from scenes
            scene_locations = {}
            for scene in scenes:
                if isinstance(scene, dict):
                    location = scene.get('location', {})
                    if isinstance(location, str):
                        location = {'name': location}
                    
                    location_id = location.get('id') or scene.get('location_id') or location.get('name')
                    if location_id:
                        if location_id not in scene_locations:
                            scene_locations[location_id] = {
                                'id': location_id,
                                'name': location.get('name', location_id),
                                'address': location.get('address', ''),
                                'latitude': location.get('latitude'),
                                'longitude': location.get('longitude'),
                                'scenes': [],
                                'requirements': location.get('requirements', []),
                                'setup_time_minutes': location.get('setup_time', 60),
                                'wrap_time_minutes': location.get('wrap_time', 60)
                            }
                        scene_locations[location_id]['scenes'].append(scene.get('id') or scene.get('scene_id'))
            
            if not scene_locations:
                logger.warning("No location information found in scenes, will use scene IDs as location IDs")
                # Create default locations based on scene IDs
                for scene in scenes:
                    if isinstance(scene, dict):
                        scene_id = scene.get('id') or scene.get('scene_id')
                        if scene_id:
                            scene_locations[scene_id] = {
                                'id': scene_id,
                                'name': f"Location for scene {scene_id}",
                                'scenes': [scene_id]
                            }
            
            prompt = f"""You are a film production location optimizer. Your task is to analyze scenes and create an optimized shooting schedule based on locations.

IMPORTANT: You must respond with ONLY valid JSON data in the exact format specified below. Do not include any other text or explanations.

Required JSON format:
{{
    "locations": [
        {{
            "id": "string",
            "name": "string",
            "address": "string",
            "latitude": number or null,
            "longitude": number or null,
            "scenes": ["scene_id1", "scene_id2"],
            "requirements": ["requirement1", "requirement2"],
            "setup_time_minutes": number,
            "wrap_time_minutes": number
        }}
    ],
    "location_groups": [
        {{
            "group_id": "string",
            "locations": ["location_id1", "location_id2"],
            "reason": "string"
        }}
    ],
    "weather_dependencies": {{
        "location_id": {{
            "preferred_conditions": ["sunny", "overcast"],
            "avoid_conditions": ["rain", "snow"],
            "seasonal_notes": ["best in summer"]
        }}
    }},
    "daylight_requirements": {{
        "scene_id": {{
            "needs_daylight": boolean,
            "golden_hour": boolean,
            "time_window": {{"start": "HH:MM", "end": "HH:MM"}}
        }}
    }},
    "shooting_sequence": ["location_id1", "location_id2"],
    "optimization_notes": ["note1", "note2"]
}}

Consider these optimization factors:
        - Physical location proximity
        - Time of day requirements
        - Weather/seasonal dependencies
        - Set construction needs
        - Company move efficiency
        
        Scene Data:
{json.dumps(scenes, indent=2)}

Location Information:
{json.dumps(list(scene_locations.values()), indent=2)}
        
        Location Constraints:
        {json.dumps(location_constraints, indent=2) if location_constraints else "No specific constraints provided"}

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
                optimization_result = json.loads(cleaned_response)
                
                # Validate the required fields
                required_fields = ['locations', 'shooting_sequence', 'weather_dependencies', 'daylight_requirements']
                for field in required_fields:
                    if field not in optimization_result:
                        raise ValueError(f"Missing required field: {field}")
                
                # Validate location data
                for location in optimization_result.get('locations', []):
                    required_location_fields = ['id', 'name', 'scenes']
                    for field in required_location_fields:
                        if field not in location:
                            raise ValueError(f"Missing required location field: {field}")
                
                # Validate weather dependencies
                for location_id, weather in optimization_result.get('weather_dependencies', {}).items():
                    required_weather_fields = ['preferred_conditions', 'avoid_conditions']
                    for field in required_weather_fields:
                        if field not in weather:
                            raise ValueError(f"Missing required weather dependency field: {field}")
                
                # Validate daylight requirements
                for scene_id, daylight in optimization_result.get('daylight_requirements', {}).items():
                    required_daylight_fields = ['needs_daylight', 'time_window']
                    for field in required_daylight_fields:
                        if field not in daylight:
                            raise ValueError(f"Missing required daylight requirement field: {field}")
                
                logger.info("Successfully parsed and validated location optimization result")
                
                # Add traveling salesman optimization if coordinates are available
                if self._has_coordinates(optimization_result):
                    logger.info("Applying TSP optimization to location sequence")
                    optimization_result["route"] = self._optimize_travel_route(optimization_result["locations"])
                    logger.info("TSP optimization completed")
                else:
                    logger.warning("No coordinates available for TSP optimization")
                
                return optimization_result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse location optimization result: {str(e)}")
                logger.debug(f"Raw response: {result.final_output}")
                
                # Try to create a basic valid response from the scene locations
                logger.info("Attempting to create fallback response from scene locations")
                fallback_response = {
                    "locations": list(scene_locations.values()),
                    "shooting_sequence": [loc["id"] for loc in scene_locations.values()],
                    "location_groups": [],
                    "weather_dependencies": {},
                    "daylight_requirements": {},
                    "optimization_notes": ["Generated fallback response due to API parsing error"]
                }
                return fallback_response
                
        except Exception as e:
            logger.error(f"Error during location optimization: {str(e)}", exc_info=True)
            return {
                "locations": [],
                "shooting_sequence": [],
                "error": str(e)
            }
    
    def _clean_and_extract_json(self, text: str) -> str:
        """Clean and extract JSON from text response."""
        import re
        
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
    
    def _has_coordinates(self, data: Dict[str, Any]) -> bool:
        """Check if location data includes coordinates."""
        if "locations" not in data:
            logger.warning("No locations found in optimization result")
            return False
            
        has_coords = all(
            isinstance(loc.get("latitude"), (int, float)) and 
            isinstance(loc.get("longitude"), (int, float))
            for loc in data["locations"]
        )
        
        if not has_coords:
            logger.warning("Some locations missing valid coordinates")
        return has_coords
    
    def _optimize_travel_route(self, locations: List[Dict[str, Any]]) -> List[int]:
        """Apply traveling salesman optimization to location sequence."""
        try:
            if not locations:
                logger.warning("No locations provided for route optimization")
                return []
            
            logger.info(f"Optimizing route for {len(locations)} locations")
            
            # Create distance matrix
            n = len(locations)
            distances = [[0] * n for _ in range(n)]
            
            for i in range(n):
                for j in range(n):
                    if i != j:
                        coord1 = (locations[i]["latitude"], locations[i]["longitude"])
                        coord2 = (locations[j]["latitude"], locations[j]["longitude"])
                        distances[i][j] = geodesic(coord1, coord2).miles
            
            # Create graph
            G = nx.Graph()
            for i in range(n):
                for j in range(i + 1, n):
                    G.add_edge(i, j, weight=distances[i][j])
            
            # Find approximate TSP solution
            tour = nx.approximation.traveling_salesman_problem(G, cycle=True)
            logger.info("Route optimization completed successfully")
            
            return tour
        except Exception as e:
            logger.error(f"Error during route optimization: {str(e)}", exc_info=True)
            return [] 