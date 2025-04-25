from typing import Dict, Any, List
import json
import logging
import re
from agents import Agent, Runner
from ...base_config import AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)

class CostEstimatorAgent:
    def __init__(self):
        self.agent = Agent(
            name="Cost Estimator",
            instructions=AGENT_INSTRUCTIONS["cost_estimator"]
        )
    
    async def estimate_costs(
        self,
        production_data: Dict[str, Any],
        location_data: Dict[str, Any],
        crew_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate detailed cost estimates for all production elements."""
        prompt = (
            "You are a professional film production cost estimator. "
            "Analyze the provided data and generate a detailed cost estimate in valid JSON format.\n\n"
            "Required JSON structure:\n"
            "{\n"
            '    "locations": {\n'
            '        "location_name": {\n'
            '            "daily_rate": float,\n'
            '            "permits": float,\n'
            '            "additional_fees": [string],\n'
            '            "total_days": int,\n'
            '            "total_cost": float\n'
            "        }\n"
            "    },\n"
            '    "equipment": {\n'
            '        "category": {\n'
            '            "items": [string],\n'
            '            "rental_rates": {"item": float},\n'
            '            "purchase_costs": {"item": float},\n'
            '            "insurance": float,\n'
            '            "total_cost": float\n'
            "        }\n"
            "    },\n"
            '    "personnel": {\n'
            '        "role": {\n'
            '            "daily_rate": float,\n'
            '            "overtime_rate": float,\n'
            '            "total_days": int,\n'
            '            "benefits": float,\n'
            '            "total_cost": float\n'
            "        }\n"
            "    },\n"
            '    "logistics": {\n'
            '        "transportation": {"item": float},\n'
            '        "accommodation": {"item": float},\n'
            '        "catering": {"item": float},\n'
            '        "misc": [string]\n'
            "    },\n"
            '    "insurance": {"type": float},\n'
            '    "contingency": {\n'
            '        "percentage": float,\n'
            '        "amount": float\n'
            "    }\n"
            "}\n\n"
            f"Production Data:\n{json.dumps(production_data, indent=2)}\n\n"
            f"Location Data:\n{json.dumps(location_data, indent=2)}\n\n"
            f"Crew Data:\n{json.dumps(crew_data, indent=2)}\n\n"
            "IMPORTANT: Respond ONLY with valid JSON matching the structure above. "
            "Do not include any other text or explanations."
        )
        
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received cost estimation response")
            
            # Try to extract JSON from the response
            estimates = self._extract_json(result.final_output)
            if not estimates:
                logger.error("Failed to extract valid JSON from response")
                logger.debug(f"Raw response: {result.final_output}")
                # Create a basic fallback response
                return self._create_fallback_estimates(production_data, location_data, crew_data)
            
            processed = self._process_estimates(estimates)
            logger.info("Successfully processed cost estimates")
            return processed
        except Exception as e:
            logger.error(f"Error in cost estimation: {str(e)}", exc_info=True)
            return self._create_fallback_estimates(production_data, location_data, crew_data)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text response, handling various formats."""
        try:
            # First try direct JSON parsing
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON between triple backticks
            matches = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON between single backticks
            matches = re.search(r'`(\{.*?\})`', text, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find anything that looks like JSON
            matches = re.search(r'\{.*\}', text, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches.group(0))
                except json.JSONDecodeError:
                    pass
            
            return {}
    
    def _create_fallback_estimates(
        self,
        production_data: Dict[str, Any],
        location_data: Dict[str, Any],
        crew_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create basic fallback estimates when JSON parsing fails."""
        logger.info("Creating fallback cost estimates")
        
        # Calculate basic estimates based on available data
        num_locations = len(location_data.get("locations", []))
        num_days = production_data.get("schedule_days", 1)
        crew_size = crew_data.get("size", "Medium")
        
        # Basic cost multipliers
        multipliers = {
            "High": 1.5,
            "Medium": 1.0,
            "Low": 0.75
        }
        
        quality_multiplier = multipliers.get(production_data.get("quality_level", "Medium"), 1.0)
        
        # Generate basic estimates
        estimates = {
            "location_costs": {},
            "equipment_costs": {},
            "personnel_costs": {},
            "logistics_costs": {},
            "insurance_costs": {
                "general_liability": 5000.0,
                "equipment": 2500.0
            },
            "contingency": {
                "percentage": 10.0,
                "amount": 0.0  # Will be calculated below
            },
            "total_estimates": {}
        }
        
        # Add basic location costs
        base_location_cost = 1000.0 * quality_multiplier
        for loc in location_data.get("locations", ["Unknown Location"]):
            estimates["location_costs"][loc] = {
                "daily_rate": base_location_cost,
                "permit_costs": base_location_cost * 0.2,
                "additional_fees": [],
                "total_days": num_days // num_locations if num_locations > 0 else 1,
                "total_cost": base_location_cost * (num_days // num_locations if num_locations > 0 else 1)
            }
        
        # Add basic equipment costs
        equipment_categories = ["Camera", "Lighting", "Sound", "Grip"]
        base_equipment_cost = 2000.0 * quality_multiplier
        for category in equipment_categories:
            estimates["equipment_costs"][category] = {
                "items": [f"{category} Package"],
                "rental_rates": {f"{category} Package": base_equipment_cost},
                "purchase_costs": {},
                "insurance_costs": base_equipment_cost * 0.1,
                "total_cost": base_equipment_cost * num_days
            }
        
        # Add basic personnel costs
        crew_multipliers = {"Large": 1.5, "Medium": 1.0, "Small": 0.75}
        crew_multiplier = crew_multipliers.get(crew_size, 1.0)
        base_crew_cost = 500.0 * quality_multiplier * crew_multiplier
        
        for dept in crew_data.get("departments", ["Production"]):
            estimates["personnel_costs"][dept] = {
                "daily_rate": base_crew_cost,
                "overtime_rate": base_crew_cost * 1.5,
                "total_days": num_days,
                "benefits": base_crew_cost * 0.2,
                "total_cost": base_crew_cost * num_days
            }
        
        # Calculate totals
        total_location = sum(loc["total_cost"] for loc in estimates["location_costs"].values())
        total_equipment = sum(eq["total_cost"] for eq in estimates["equipment_costs"].values())
        total_personnel = sum(p["total_cost"] for p in estimates["personnel_costs"].values())
        total_insurance = sum(estimates["insurance_costs"].values())
        
        subtotal = total_location + total_equipment + total_personnel + total_insurance
        contingency_amount = subtotal * 0.1
        
        estimates["contingency"]["amount"] = contingency_amount
        estimates["total_estimates"] = {
            "total_location_costs": total_location,
            "total_equipment_costs": total_equipment,
            "total_personnel_costs": total_personnel,
            "total_insurance_costs": total_insurance,
            "contingency_amount": contingency_amount,
            "grand_total": subtotal + contingency_amount
        }
        
        return estimates
    
    def _process_estimates(self, estimates: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate cost estimates."""
        processed = {
            "location_costs": {},
            "equipment_costs": {},
            "personnel_costs": {},
            "logistics_costs": {},
            "insurance_costs": {},
            "contingency": {},
            "total_estimates": {}
        }
        
        # Process location costs
        if "locations" in estimates:
            for location, data in estimates["locations"].items():
                processed["location_costs"][location] = {
                    "daily_rate": data.get("daily_rate", 0),
                    "permit_costs": data.get("permits", 0),
                    "additional_fees": data.get("additional_fees", []),
                    "total_days": data.get("total_days", 0),
                    "total_cost": data.get("total_cost", 0)
                }
        
        # Process equipment costs
        if "equipment" in estimates:
            for category, items in estimates["equipment"].items():
                processed["equipment_costs"][category] = {
                    "items": items.get("items", []),
                    "rental_rates": items.get("rental_rates", {}),
                    "purchase_costs": items.get("purchase_costs", {}),
                    "insurance_costs": items.get("insurance", 0),
                    "total_cost": items.get("total_cost", 0)
                }
        
        # Process personnel costs
        if "personnel" in estimates:
            for role, costs in estimates["personnel"].items():
                processed["personnel_costs"][role] = {
                    "daily_rate": costs.get("daily_rate", 0),
                    "overtime_rate": costs.get("overtime_rate", 0),
                    "total_days": costs.get("total_days", 0),
                    "benefits": costs.get("benefits", 0),
                    "total_cost": costs.get("total_cost", 0)
                }
        
        # Process logistics costs
        if "logistics" in estimates:
            processed["logistics_costs"] = {
                "transportation": estimates["logistics"].get("transportation", {}),
                "accommodation": estimates["logistics"].get("accommodation", {}),
                "catering": estimates["logistics"].get("catering", {}),
                "misc_expenses": estimates["logistics"].get("misc", [])
            }
        
        # Process insurance costs
        if "insurance" in estimates:
            processed["insurance_costs"] = estimates["insurance"]
        
        # Process contingency
        if "contingency" in estimates:
            processed["contingency"] = {
                "percentage": estimates["contingency"].get("percentage", 10),
                "amount": estimates["contingency"].get("amount", 0)
            }
        
        # Calculate totals
        total_location = sum(loc["total_cost"] for loc in processed["location_costs"].values())
        total_equipment = sum(eq["total_cost"] for eq in processed["equipment_costs"].values())
        total_personnel = sum(p["total_cost"] for p in processed["personnel_costs"].values())
        total_logistics = sum(
            sum(category.values()) if isinstance(category, dict) else 0
            for category in processed["logistics_costs"].values()
        )
        total_insurance = sum(processed["insurance_costs"].values())
        
        processed["total_estimates"] = {
            "total_location_costs": total_location,
            "total_equipment_costs": total_equipment,
            "total_personnel_costs": total_personnel,
            "total_logistics_costs": total_logistics,
            "total_insurance_costs": total_insurance,
            "contingency_amount": processed["contingency"]["amount"],
            "grand_total": sum([
                total_location,
                total_equipment,
                total_personnel,
                total_logistics,
                total_insurance,
                processed["contingency"]["amount"]
            ])
        }
        
        return processed 