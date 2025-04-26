from typing import Dict, Any, List
import json
import logging
import re
from datetime import datetime
from agents import Agent, Runner
from ...base_config import AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)

class BudgetOptimizerAgent:
    def __init__(self):
        self.agent = Agent(
            name="Budget Optimizer",
            instructions=AGENT_INSTRUCTIONS["budget_optimizer"]
        )
        # Initialize optimization templates for Indian market
        self.optimization_templates = {
            "cost_reduction": {
                "equipment": {
                    "local_rental": {"savings": 0.2, "impact": "low"},
                    "package_deals": {"savings": 0.15, "impact": "low"},
                    "off_peak_rental": {"savings": 0.25, "impact": "medium"}
                },
                "location": {
                    "bulk_booking": {"savings": 0.1, "impact": "low"},
                    "off_season": {"savings": 0.3, "impact": "medium"},
                    "alternative_locations": {"savings": 0.4, "impact": "high"}
                },
                "crew": {
                    "local_hiring": {"savings": 0.2, "impact": "medium"},
                    "package_deals": {"savings": 0.15, "impact": "low"},
                    "flexible_scheduling": {"savings": 0.1, "impact": "low"}
                }
            },
            "regional_factors": {
                "mumbai": {"cost_multiplier": 1.2, "risk_factor": 1.1},
                "delhi": {"cost_multiplier": 1.0, "risk_factor": 1.0},
                "bangalore": {"cost_multiplier": 0.9, "risk_factor": 0.9}
            }
        }
    
    async def optimize_budget(
        self,
        cost_estimates: Dict[str, Any],
        production_constraints: Dict[str, Any],
        target_budget: float = None,
        scenario: str = "base"
    ) -> Dict[str, Any]:
        """Optimize budget allocation with scenario analysis."""
        # Apply scenario adjustments
        adjusted_estimates = self._apply_scenario_adjustments(
            cost_estimates,
            scenario,
            production_constraints
        )
        
        prompt = self._generate_optimization_prompt(
            adjusted_estimates,
            production_constraints,
            target_budget,
            scenario
        )
        
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info(f"Received budget optimization response for scenario: {scenario}")
            
            optimization = self._extract_json(result.final_output)
            if not optimization:
                logger.error("Failed to extract valid JSON from response")
                return self._create_fallback_optimization(
                    adjusted_estimates,
                    target_budget,
                    scenario
                )
            
            processed = self._process_optimization(
                optimization,
                adjusted_estimates,
                target_budget,
                scenario
            )
            logger.info(f"Successfully processed budget optimization for scenario: {scenario}")
            return processed
            
        except Exception as e:
            logger.error(f"Error in budget optimization: {str(e)}", exc_info=True)
            return self._create_fallback_optimization(
                adjusted_estimates,
                target_budget,
                scenario
            )
    
    async def generate_scenarios(
        self,
        base_estimates: Dict[str, Any],
        production_constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate multiple budget scenarios for comparison."""
        scenarios = {
            "base": await self.optimize_budget(
                base_estimates,
                production_constraints,
                scenario="base"
            ),
            "optimistic": await self.optimize_budget(
                base_estimates,
                production_constraints,
                scenario="optimistic"
            ),
            "conservative": await self.optimize_budget(
                base_estimates,
                production_constraints,
                scenario="conservative"
            )
        }
        
        # Add scenario comparison metrics
        comparison = self._compare_scenarios(scenarios)
        
        return {
            "scenarios": scenarios,
            "comparison": comparison
        }
    
    def _apply_scenario_adjustments(
        self,
        estimates: Dict[str, Any],
        scenario: str,
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply scenario-specific adjustments to cost estimates."""
        adjusted = json.loads(json.dumps(estimates))  # Deep copy
        
        # Get regional factors
        region = constraints.get("region", "mumbai").lower()
        factors = self.optimization_templates["regional_factors"].get(
            region,
            self.optimization_templates["regional_factors"]["mumbai"]
        )
        
        # Apply scenario multipliers
        multipliers = {
            "base": 1.0,
            "optimistic": 0.9,
            "conservative": 1.2
        }
        
        scenario_multiplier = multipliers.get(scenario, 1.0)
        regional_multiplier = factors["cost_multiplier"]
        risk_multiplier = factors["risk_factor"]
        
        # Apply multipliers to all cost categories
        for category in ["location_costs", "equipment_costs", "personnel_costs"]:
            if category in adjusted:
                for item in adjusted[category].values():
                    if isinstance(item, dict) and "total_cost" in item:
                        item["total_cost"] *= (
                            scenario_multiplier *
                            regional_multiplier *
                            risk_multiplier
                        )
        
        return adjusted
    
    def _generate_optimization_prompt(
        self,
        estimates: Dict[str, Any],
        constraints: Dict[str, Any],
        target_budget: float,
        scenario: str
    ) -> str:
        """Generate optimization prompt with scenario context."""
        return f"""You are a professional Indian film production budget optimizer. Analyze the estimates and suggest optimizations for the {scenario} scenario in valid JSON format.

        Required JSON structure:
        {{
            "scenario_info": {{
                "name": string,
                "description": string,
                "risk_level": string
            }},
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
            "regional_strategies": {{
                "local_resources": [string],
                "cost_advantages": [string],
                "risk_mitigations": [string]
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
        
        {f'Target budget: ₹{target_budget:,.2f}' if target_budget else 'Optimize for efficiency'}
        
        Cost Estimates:
        {json.dumps(estimates, indent=2)}
        
        Production Constraints:
        {json.dumps(constraints, indent=2)}
        
        Scenario: {scenario}

        IMPORTANT: Respond ONLY with valid JSON matching the structure above. Do not include any other text or explanations."""
    
    def _compare_scenarios(self, scenarios: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comparison metrics between different scenarios."""
        comparison = {
            "total_costs": {},
            "savings_potential": {},
            "risk_levels": {},
            "timeline_impact": {},
            "quality_impact": {},
            "recommended_scenario": None,
            "scenario_rankings": {}
        }
        
        # Calculate metrics for each scenario
        for name, scenario in scenarios.items():
            if "savings_summary" in scenario:
                comparison["total_costs"][name] = scenario["savings_summary"]["optimized_total"]
                comparison["savings_potential"][name] = scenario["savings_summary"]["total_savings"]
            
            if "impact_analysis" in scenario:
                comparison["risk_levels"][name] = len(scenario["impact_analysis"]["risk_assessment"])
                comparison["timeline_impact"][name] = scenario["impact_analysis"]["timeline_impact"]
                comparison["quality_impact"][name] = scenario["impact_analysis"]["quality_impact"]
        
        # Rank scenarios
        rankings = {
            "cost_effectiveness": self._rank_scenarios(comparison["total_costs"], reverse=True),
            "risk_level": self._rank_scenarios(comparison["risk_levels"]),
            "savings_potential": self._rank_scenarios(comparison["savings_potential"])
        }
        comparison["scenario_rankings"] = rankings
        
        # Determine recommended scenario based on rankings
        total_ranks = {}
        for scenario in scenarios.keys():
            total_ranks[scenario] = sum(
                ranking.index(scenario) + 1
                for ranking in rankings.values()
            )
        comparison["recommended_scenario"] = min(
            total_ranks.items(),
            key=lambda x: x[1]
        )[0]
        
        return comparison
    
    def _rank_scenarios(
        self,
        metric_dict: Dict[str, float],
        reverse: bool = False
    ) -> List[str]:
        """Rank scenarios based on a metric."""
        return [
            k for k, v in sorted(
                metric_dict.items(),
                key=lambda x: x[1],
                reverse=reverse
            )
        ]
    
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
        target_budget: float = None,
        scenario: str = "base"
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
            "savings_summary": {},
            "scenario_info": {
                "name": scenario,
                "description": "Fallback scenario",
                "risk_level": "high"
            }
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
        
        # Calculate savings summary
        total_savings = sum(
            reduction["savings"]
            for reduction in optimization["cost_reductions"].values()
        )
        
        optimization["savings_summary"] = {
            "original_total": total_current,
            "total_savings": total_savings,
            "total_reallocation": 0,
            "optimized_total": total_current - total_savings,
            "percentage_saved": (total_savings / total_current * 100) if total_current > 0 else 0,
            "target_met": (
                target_budget is None or
                (total_current - total_savings) <= target_budget
            )
        }
        
        return optimization
    
    def _process_optimization(
        self,
        optimization: Dict[str, Any],
        original_estimates: Dict[str, Any],
        target_budget: float = None,
        scenario: str = "base"
    ) -> Dict[str, Any]:
        """Process and validate budget optimization suggestions."""
        processed = {
            "cost_reductions": {},
            "reallocations": {},
            "alternatives": {},
            "impact_analysis": {},
            "savings_summary": {},
            "recommendations": [],
            "scenario_info": optimization["scenario_info"]
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