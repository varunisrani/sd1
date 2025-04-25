from typing import Dict, Any, List
import json
import logging
import re
from agents import Agent, Runner
from ...base_config import AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)

class BudgetOptimizerAgent:
    def __init__(self):
        self.agent = Agent(
            name="Budget Optimizer",
            instructions=AGENT_INSTRUCTIONS["budget_optimizer"]
        )
    
    async def optimize_budget(
        self,
        cost_estimates: Dict[str, Any],
        production_constraints: Dict[str, Any],
        target_budget: float = None
    ) -> Dict[str, Any]:
        """Optimize budget allocation and suggest cost-saving measures."""
        prompt = f"""You are a professional film production budget optimizer. Analyze the cost estimates and suggest optimizations in valid JSON format.

        Required JSON structure:
        {{
            "reductions": {{
                "category": {{
                    "current_cost": float,
                    "proposed_cost": float,
                    "savings": float,
                    "methods": [string],
                    "impact": string
                }}
            }},
            "reallocations": [
                {{
                    "from_category": string,
                    "to_category": string,
                    "amount": float,
                    "justification": string,
                    "risk": string
                }}
            ],
            "alternatives": {{
                "category": {{
                    "options": [string],
                    "savings": float,
                    "implementation_cost": float,
                    "net_benefit": float,
                    "timeline": string
                }}
            }},
            "impact": {{
                "quality": {{}},
                "timeline": {{}},
                "resources": {{}},
                "risks": [string]
            }},
            "recommendations": [
                {{
                    "action": string,
                    "priority": string,
                    "timeline": string,
                    "outcome": string,
                    "dependencies": [string]
                }}
            ]
        }}
        
        {f'Target budget: ${target_budget:,.2f}' if target_budget else 'Optimize for efficiency'}
        
        Cost Estimates:
        {json.dumps(cost_estimates, indent=2)}
        
        Production Constraints:
        {json.dumps(production_constraints, indent=2)}

        IMPORTANT: Respond ONLY with valid JSON matching the structure above. Do not include any other text or explanations.
        """
        
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received budget optimization response")
            
            # Try to extract JSON from the response
            optimization = self._extract_json(result.final_output)
            if not optimization:
                logger.error("Failed to extract valid JSON from response")
                logger.debug(f"Raw response: {result.final_output}")
                # Create a basic fallback response
                return self._create_fallback_optimization(cost_estimates, target_budget)
            
            processed = self._process_optimization(optimization, cost_estimates, target_budget)
            logger.info("Successfully processed budget optimization")
            return processed
        except Exception as e:
            logger.error(f"Error in budget optimization: {str(e)}", exc_info=True)
            return self._create_fallback_optimization(cost_estimates, target_budget)
    
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
    
    def _create_fallback_optimization(
        self,
        cost_estimates: Dict[str, Any],
        target_budget: float = None
    ) -> Dict[str, Any]:
        """Create basic fallback optimization when JSON parsing fails."""
        logger.info("Creating fallback budget optimization")
        
        total_current = cost_estimates["total_estimates"]["grand_total"]
        target_reduction = (
            (total_current - target_budget)
            if target_budget and target_budget < total_current
            else total_current * 0.1  # Default 10% reduction
        )
        
        # Calculate reduction per category
        categories = [
            "location_costs",
            "equipment_costs",
            "personnel_costs",
            "logistics_costs"
        ]
        
        optimization = {
            "cost_reductions": {},
            "reallocations": {},
            "alternatives": {},
            "impact_analysis": {
                "quality_impact": {"level": "minimal"},
                "timeline_impact": {"delay_days": 0},
                "resource_impact": {"efficiency": "maintained"},
                "risk_assessment": ["Standard budget optimization risks"]
            },
            "recommendations": [],
            "savings_summary": {}
        }
        
        # Generate basic reductions
        for category in categories:
            if category in cost_estimates:
                current = sum(
                    item.get("total_cost", 0)
                    for item in cost_estimates[category].values()
                )
                reduction = (current / total_current) * target_reduction
                
                optimization["cost_reductions"][category] = {
                    "current_cost": current,
                    "proposed_cost": current - reduction,
                    "savings": reduction,
                    "methods": [f"Standard {category} optimization"],
                    "impact_level": "low"
                }
        
        # Add basic recommendations
        optimization["recommendations"] = [
            {
                "action": "Implement standard cost reduction measures",
                "priority": "high",
                "timeline": "immediate",
                "expected_outcome": "Meet budget targets while maintaining quality",
                "dependencies": []
            }
        ]
        
        return optimization
    
    def _process_optimization(
        self,
        optimization: Dict[str, Any],
        original_estimates: Dict[str, Any],
        target_budget: float = None
    ) -> Dict[str, Any]:
        """Process and validate budget optimization suggestions."""
        processed = {
            "cost_reductions": {},
            "reallocations": {},
            "alternatives": {},
            "impact_analysis": {},
            "savings_summary": {},
            "recommendations": []
        }
        
        # Process cost reduction suggestions
        if "reductions" in optimization:
            for category, reductions in optimization["reductions"].items():
                processed["cost_reductions"][category] = {
                    "current_cost": reductions.get("current_cost", 0),
                    "proposed_cost": reductions.get("proposed_cost", 0),
                    "savings": reductions.get("savings", 0),
                    "methods": reductions.get("methods", []),
                    "impact_level": reductions.get("impact", "low")
                }
        
        # Process budget reallocation suggestions
        if "reallocations" in optimization:
            for item in optimization["reallocations"]:
                processed["reallocations"][item["from_category"]] = {
                    "to_category": item.get("to_category"),
                    "amount": item.get("amount", 0),
                    "justification": item.get("justification", ""),
                    "risk_level": item.get("risk", "low")
                }
        
        # Process alternative solutions
        if "alternatives" in optimization:
            for category, options in optimization["alternatives"].items():
                processed["alternatives"][category] = {
                    "options": options.get("options", []),
                    "potential_savings": options.get("savings", 0),
                    "implementation_cost": options.get("implementation_cost", 0),
                    "net_benefit": options.get("net_benefit", 0),
                    "timeline": options.get("timeline", "immediate")
                }
        
        # Process impact analysis
        if "impact" in optimization:
            processed["impact_analysis"] = {
                "quality_impact": optimization["impact"].get("quality", {}),
                "timeline_impact": optimization["impact"].get("timeline", {}),
                "resource_impact": optimization["impact"].get("resources", {}),
                "risk_assessment": optimization["impact"].get("risks", [])
            }
        
        # Calculate savings summary
        total_current = original_estimates["total_estimates"]["grand_total"]
        total_savings = sum(
            reduction["savings"]
            for reduction in processed["cost_reductions"].values()
        )
        total_reallocation = sum(
            realloc["amount"]
            for realloc in processed["reallocations"].values()
        )
        
        processed["savings_summary"] = {
            "original_total": total_current,
            "total_savings": total_savings,
            "total_reallocation": total_reallocation,
            "optimized_total": total_current - total_savings,
            "percentage_saved": (total_savings / total_current * 100) if total_current > 0 else 0,
            "target_met": (
                target_budget is None or
                (total_current - total_savings) <= target_budget
            )
        }
        
        # Process recommendations
        if "recommendations" in optimization:
            processed["recommendations"] = [
                {
                    "action": rec.get("action", ""),
                    "priority": rec.get("priority", "medium"),
                    "timeline": rec.get("timeline", "immediate"),
                    "expected_outcome": rec.get("outcome", ""),
                    "dependencies": rec.get("dependencies", [])
                }
                for rec in optimization["recommendations"]
            ]
        
        return processed 