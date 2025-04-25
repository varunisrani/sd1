from typing import Dict, Any, List
import json
import logging
import re
from datetime import datetime
from agents import Agent, Runner
from ...base_config import AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)

class BudgetTrackerAgent:
    def __init__(self):
        self.agent = Agent(
            name="Budget Tracker",
            instructions=AGENT_INSTRUCTIONS["budget_tracker"]
        )
    
    async def track_expenses(
        self,
        budget_data: Dict[str, Any],
        actual_expenses: Dict[str, Any],
        tracking_period: str
    ) -> Dict[str, Any]:
        """Track and analyze actual expenses against budget."""
        prompt = f"""You are a professional film production budget tracker. Analyze expenses and generate a tracking report in valid JSON format.

        Required JSON structure:
        {{
            "summary": {{
                "start_date": string,
                "end_date": string,
                "total_budget": float,
                "total_spent": float,
                "remaining": float,
                "percent_spent": float
            }},
            "categories": {{
                "category_name": {{
                    "budgeted": float,
                    "actual": float,
                    "remaining": float,
                    "percent_spent": float,
                    "status": string
                }}
            }},
            "variances": {{
                "category": {{
                    "amount": float,
                    "percentage": float,
                    "reason": string,
                    "impact": string,
                    "action": string
                }}
            }},
            "trends": {{
                "daily_avg": {{}},
                "weekly_totals": {{}},
                "analysis": [string],
                "burn_rate": float
            }},
            "alerts": [
                {{
                    "type": string,
                    "category": string,
                    "message": string,
                    "threshold": float,
                    "current": float,
                    "timestamp": string
                }}
            ],
            "projections": {{
                "total": float,
                "variance": float,
                "completion_date": string,
                "confidence": string,
                "risks": [string]
            }},
            "cash_flow": {{
                "balance": float,
                "upcoming": {{}},
                "schedule": {{}},
                "requirements": [string]
            }}
        }}
        
        Tracking period: {tracking_period}
        
        Budget Data:
        {json.dumps(budget_data, indent=2)}
        
        Actual Expenses:
        {json.dumps(actual_expenses, indent=2)}

        IMPORTANT: Respond ONLY with valid JSON matching the structure above. Do not include any other text or explanations.
        """
        
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received expense tracking response")
            
            # Try to extract JSON from the response
            tracking = self._extract_json(result.final_output)
            if not tracking:
                logger.error("Failed to extract valid JSON from response")
                logger.debug(f"Raw response: {result.final_output}")
                # Create a basic fallback response
                return self._create_fallback_tracking(budget_data, actual_expenses, tracking_period)
            
            processed = self._process_tracking(tracking, budget_data, actual_expenses)
            logger.info("Successfully processed expense tracking")
            return processed
        except Exception as e:
            logger.error(f"Error in expense tracking: {str(e)}", exc_info=True)
            return self._create_fallback_tracking(budget_data, actual_expenses, tracking_period)
    
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
    
    def _create_fallback_tracking(
        self,
        budget_data: Dict[str, Any],
        actual_expenses: Dict[str, Any],
        tracking_period: str
    ) -> Dict[str, Any]:
        """Create basic fallback tracking when JSON parsing fails."""
        logger.info("Creating fallback expense tracking")
        
        # Parse tracking period
        try:
            start_date = tracking_period.split(" to ")[0]
            end_date = tracking_period.split(" to ")[1]
        except:
            start_date = datetime.now().strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Calculate basic totals
        total_budget = budget_data["total_estimates"]["grand_total"]
        total_spent = sum(
            sum(expense.values())
            for category in actual_expenses.values()
            for expense in category.values()
            if isinstance(expense, dict)
        )
        
        tracking = {
            "period_summary": {
                "period_start": start_date,
                "period_end": end_date,
                "total_budget": total_budget,
                "total_spent": total_spent,
                "remaining_budget": total_budget - total_spent,
                "percent_spent": (total_spent / total_budget * 100) if total_budget > 0 else 0
            },
            "category_tracking": {},
            "variances": {},
            "trends": {
                "daily_averages": {},
                "weekly_totals": {},
                "trend_analysis": ["Basic tracking enabled"],
                "burn_rate": total_spent / 30 if total_spent > 0 else 0  # Assume 30-day period
            },
            "alerts": [],
            "projections": {
                "estimated_total": total_spent * 1.1,  # Basic projection
                "estimated_variance": 0,
                "completion_date": end_date,
                "confidence_level": "medium",
                "risk_factors": ["Using fallback tracking"]
            },
            "cash_flow": {
                "current_balance": total_budget - total_spent,
                "upcoming_expenses": {},
                "payment_schedule": {},
                "cash_requirements": ["Standard cash flow tracking"]
            }
        }
        
        # Process categories
        for category, budget in budget_data.items():
            if isinstance(budget, dict) and category != "total_estimates":
                category_spent = sum(
                    expense.get("total_cost", 0)
                    for expense in actual_expenses.get(category, {}).values()
                )
                category_budget = sum(
                    item.get("total_cost", 0)
                    for item in budget.values()
                )
                
                tracking["category_tracking"][category] = {
                    "budgeted": category_budget,
                    "actual": category_spent,
                    "remaining": category_budget - category_spent,
                    "percent_spent": (category_spent / category_budget * 100) if category_budget > 0 else 0,
                    "status": "on_track" if category_spent <= category_budget else "over_budget"
                }
                
                # Add variance if significant
                if abs(category_spent - category_budget) > (category_budget * 0.1):
                    tracking["variances"][category] = {
                        "amount": category_spent - category_budget,
                        "percentage": ((category_spent - category_budget) / category_budget * 100) if category_budget > 0 else 0,
                        "reason": "Variance detected",
                        "impact": "medium",
                        "corrective_action": "Monitor spending"
                    }
        
        # Add basic alerts
        if total_spent > total_budget * 0.9:
            tracking["alerts"].append({
                "type": "warning",
                "category": "overall",
                "message": "Budget usage above 90%",
                "threshold": total_budget * 0.9,
                "current_value": total_spent,
                "timestamp": datetime.now().isoformat()
            })
        
        return tracking
    
    def _process_tracking(
        self,
        tracking: Dict[str, Any],
        budget: Dict[str, Any],
        actuals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and validate expense tracking data."""
        processed = {
            "period_summary": {},
            "category_tracking": {},
            "variances": {},
            "trends": {},
            "alerts": [],
            "projections": {},
            "cash_flow": {}
        }
        
        # Process period summary
        if "summary" in tracking:
            processed["period_summary"] = {
                "period_start": tracking["summary"].get("start_date"),
                "period_end": tracking["summary"].get("end_date"),
                "total_budget": tracking["summary"].get("total_budget", 0),
                "total_spent": tracking["summary"].get("total_spent", 0),
                "remaining_budget": tracking["summary"].get("remaining", 0),
                "percent_spent": tracking["summary"].get("percent_spent", 0)
            }
        
        # Process category tracking
        if "categories" in tracking:
            for category, data in tracking["categories"].items():
                processed["category_tracking"][category] = {
                    "budgeted": data.get("budgeted", 0),
                    "actual": data.get("actual", 0),
                    "remaining": data.get("remaining", 0),
                    "percent_spent": data.get("percent_spent", 0),
                    "status": data.get("status", "on_track")
                }
        
        # Process variances
        if "variances" in tracking:
            for category, variance in tracking["variances"].items():
                processed["variances"][category] = {
                    "amount": variance.get("amount", 0),
                    "percentage": variance.get("percentage", 0),
                    "reason": variance.get("reason", ""),
                    "impact": variance.get("impact", "low"),
                    "corrective_action": variance.get("action", "")
                }
        
        # Process spending trends
        if "trends" in tracking:
            processed["trends"] = {
                "daily_averages": tracking["trends"].get("daily_avg", {}),
                "weekly_totals": tracking["trends"].get("weekly_totals", {}),
                "trend_analysis": tracking["trends"].get("analysis", []),
                "burn_rate": tracking["trends"].get("burn_rate", 0)
            }
        
        # Process alerts
        if "alerts" in tracking:
            processed["alerts"] = [
                {
                    "type": alert.get("type", "warning"),
                    "category": alert.get("category", ""),
                    "message": alert.get("message", ""),
                    "threshold": alert.get("threshold", 0),
                    "current_value": alert.get("current", 0),
                    "timestamp": alert.get("timestamp", datetime.now().isoformat())
                }
                for alert in tracking["alerts"]
            ]
        
        # Process projections
        if "projections" in tracking:
            processed["projections"] = {
                "estimated_total": tracking["projections"].get("total", 0),
                "estimated_variance": tracking["projections"].get("variance", 0),
                "completion_date": tracking["projections"].get("completion_date", ""),
                "confidence_level": tracking["projections"].get("confidence", "medium"),
                "risk_factors": tracking["projections"].get("risks", [])
            }
        
        # Process cash flow
        if "cash_flow" in tracking:
            processed["cash_flow"] = {
                "current_balance": tracking["cash_flow"].get("balance", 0),
                "upcoming_expenses": tracking["cash_flow"].get("upcoming", {}),
                "payment_schedule": tracking["cash_flow"].get("schedule", {}),
                "cash_requirements": tracking["cash_flow"].get("requirements", [])
            }
        
        return processed 