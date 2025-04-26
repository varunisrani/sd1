from typing import Dict, Any, List
import json
import logging
import re
from datetime import datetime, timedelta
from agents import Agent, Runner
from ...base_config import AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)

class BudgetTrackerAgent:
    def __init__(self):
        self.agent = Agent(
            name="Budget Tracker",
            instructions=AGENT_INSTRUCTIONS["budget_tracker"]
        )
        # Initialize health monitoring thresholds
        self.health_thresholds = {
            "critical": {
                "spend_rate": 1.2,  # 20% over budget rate
                "remaining": 0.1,    # 10% remaining
                "variance": 0.2      # 20% variance
            },
            "warning": {
                "spend_rate": 1.1,   # 10% over budget rate
                "remaining": 0.2,    # 20% remaining
                "variance": 0.1      # 10% variance
            },
            "healthy": {
                "spend_rate": 1.0,   # At or under budget rate
                "remaining": 0.3,    # 30% or more remaining
                "variance": 0.05     # 5% variance
            }
        }
    
    async def track_expenses(
        self,
        budget_data: Dict[str, Any],
        actual_expenses: Dict[str, Any],
        tracking_period: str,
        vendor_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Track and analyze actual expenses against budget with health monitoring."""
        # Calculate health metrics
        health_metrics = self._calculate_health_metrics(
            budget_data,
            actual_expenses,
            tracking_period
        )
        
        prompt = self._generate_tracking_prompt(
            budget_data,
            actual_expenses,
            tracking_period,
            health_metrics,
            vendor_data
        )
        
        try:
            result = await Runner.run(self.agent, prompt)
            logger.info("Received expense tracking response")
            
            tracking = self._extract_json(result.final_output)
            if not tracking:
                logger.error("Failed to extract valid JSON from response")
                return self._create_fallback_tracking(
                    budget_data,
                    actual_expenses,
                    tracking_period,
                    health_metrics
                )
            
            processed = self._process_tracking(
                tracking,
                budget_data,
                actual_expenses,
                health_metrics
            )
            logger.info("Successfully processed expense tracking")
            return processed
            
        except Exception as e:
            logger.error(f"Error in expense tracking: {str(e)}", exc_info=True)
            return self._create_fallback_tracking(
                budget_data,
                actual_expenses,
                tracking_period,
                health_metrics
            )
    
    def _calculate_health_metrics(
        self,
        budget: Dict[str, Any],
        actuals: Dict[str, Any],
        period: str
    ) -> Dict[str, Any]:
        """Calculate budget health metrics."""
        try:
            # Parse period dates
            start_date = datetime.strptime(period.split(" to ")[0], "%Y-%m-%d")
            end_date = datetime.strptime(period.split(" to ")[1], "%Y-%m-%d")
            days_elapsed = (datetime.now() - start_date).days
            total_days = (end_date - start_date).days
            
            # Calculate basic metrics
            total_budget = budget["total_estimates"]["grand_total"]
            total_spent = sum(
                sum(expense.values())
                for category in actuals.values()
                for expense in category.values()
                if isinstance(expense, dict)
            )
            
            # Calculate health indicators
            spend_rate = (total_spent / days_elapsed) * total_days / total_budget if days_elapsed > 0 else 0
            remaining_percent = (total_budget - total_spent) / total_budget if total_budget > 0 else 0
            burn_rate = total_spent / days_elapsed if days_elapsed > 0 else 0
            
            # Calculate category variances
            category_variances = {}
            for category in budget:
                if isinstance(budget[category], dict) and category != "total_estimates":
                    budgeted = sum(
                        item.get("total_cost", 0)
                        for item in budget[category].values()
                    )
                    actual = sum(
                        expense.get("total_cost", 0)
                        for expense in actuals.get(category, {}).values()
                    )
                    if budgeted > 0:
                        category_variances[category] = (actual - budgeted) / budgeted
            
            # Determine health status
            health_status = "healthy"
            for threshold_name, thresholds in self.health_thresholds.items():
                if (
                    spend_rate > thresholds["spend_rate"] or
                    remaining_percent < thresholds["remaining"] or
                    any(abs(var) > thresholds["variance"] for var in category_variances.values())
                ):
                    health_status = threshold_name
                    break
            
            return {
                "status": health_status,
                "metrics": {
                    "spend_rate": spend_rate,
                    "burn_rate": burn_rate,
                    "remaining_percent": remaining_percent,
                    "days_elapsed": days_elapsed,
                    "days_remaining": total_days - days_elapsed,
                    "category_variances": category_variances
                },
                "indicators": {
                    "on_track": spend_rate <= 1.0,
                    "within_budget": total_spent <= total_budget,
                    "healthy_burn": burn_rate <= (total_budget / total_days) if total_days > 0 else True
                },
                "trends": {
                    "daily_average": total_spent / days_elapsed if days_elapsed > 0 else 0,
                    "projected_total": (total_spent / days_elapsed) * total_days if days_elapsed > 0 else 0,
                    "variance_trend": "stable"  # This should be calculated from historical data
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating health metrics: {str(e)}", exc_info=True)
            return {
                "status": "unknown",
                "metrics": {},
                "indicators": {},
                "trends": {}
            }
    
    def _generate_tracking_prompt(
        self,
        budget: Dict[str, Any],
        actuals: Dict[str, Any],
        period: str,
        health: Dict[str, Any],
        vendor_data: Dict[str, Any] = None
    ) -> str:
        """Generate tracking prompt with health metrics."""
        return f"""You are a professional Indian film production budget tracker. Analyze expenses and generate a tracking report in valid JSON format.

        Required JSON structure:
        {{
            "health_status": {{
                "overall": string,
                "metrics": {{}},
                "alerts": [string],
                "recommendations": [string]
            }},
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
                    "status": string,
                    "health_indicators": {{}}
                }}
            }},
            "variances": {{
                "category": {{
                    "amount": float,
                    "percentage": float,
                    "reason": string,
                    "impact": string,
                    "action": string,
                    "trend": string
                }}
            }},
            "trends": {{
                "daily_avg": {{}},
                "weekly_totals": {{}},
                "analysis": [string],
                "burn_rate": float,
                "forecast": {{}}
            }},
            "alerts": [
                {{
                    "type": string,
                    "category": string,
                    "message": string,
                    "threshold": float,
                    "current": float,
                    "timestamp": string,
                    "priority": string
                }}
            ],
            "projections": {{
                "total": float,
                "variance": float,
                "completion_date": string,
                "confidence": string,
                "risks": [string],
                "mitigation_strategies": [string]
            }},
            "cash_flow": {{
                "balance": float,
                "upcoming": {{}},
                "schedule": {{}},
                "requirements": [string]
            }},
            "vendor_analysis": {{
                "spend_by_vendor": {{}},
                "payment_status": {{}},
                "performance_metrics": {{}}
            }}
        }}
        
        Tracking period: {period}
        
        Budget Data:
        {json.dumps(budget, indent=2)}
        
        Actual Expenses:
        {json.dumps(actuals, indent=2)}
        
        Health Metrics:
        {json.dumps(health, indent=2)}
        
        {f'Vendor Data: {json.dumps(vendor_data, indent=2)}' if vendor_data else ''}

        IMPORTANT: Respond ONLY with valid JSON matching the structure above. Do not include any other text or explanations."""
    
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
        tracking_period: str,
        health_metrics: Dict[str, Any]
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
            },
            "health_status": health_metrics["status"],
            "health_metrics": health_metrics["metrics"],
            "health_indicators": health_metrics["indicators"],
            "health_trends": health_metrics["trends"]
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
                    "status": "on_track" if category_spent <= category_budget else "over_budget",
                    "health_indicators": {}
                }
                
                # Add variance if significant
                if abs(category_spent - category_budget) > (category_budget * 0.1):
                    tracking["variances"][category] = {
                        "amount": category_spent - category_budget,
                        "percentage": ((category_spent - category_budget) / category_budget * 100) if category_budget > 0 else 0,
                        "reason": "Variance detected",
                        "impact": "medium",
                        "corrective_action": "Monitor spending",
                        "trend": "unstable"
                    }
        
        # Add basic alerts
        if total_spent > total_budget * 0.9:
            tracking["alerts"].append({
                "type": "warning",
                "category": "overall",
                "message": "Budget usage above 90%",
                "threshold": total_budget * 0.9,
                "current_value": total_spent,
                "timestamp": datetime.now().isoformat(),
                "priority": "high"
            })
        
        return tracking
    
    def _process_tracking(
        self,
        tracking: Dict[str, Any],
        budget: Dict[str, Any],
        actuals: Dict[str, Any],
        health_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and validate expense tracking data."""
        processed = {
            "period_summary": {},
            "category_tracking": {},
            "variances": {},
            "trends": {},
            "alerts": [],
            "projections": {},
            "cash_flow": {},
            "health_status": health_metrics["status"],
            "health_metrics": health_metrics["metrics"],
            "health_indicators": health_metrics["indicators"],
            "health_trends": health_metrics["trends"]
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
                    "status": data.get("status", "on_track"),
                    "health_indicators": data.get("health_indicators", {})
                }
        
        # Process variances
        if "variances" in tracking:
            for category, variance in tracking["variances"].items():
                processed["variances"][category] = {
                    "amount": variance.get("amount", 0),
                    "percentage": variance.get("percentage", 0),
                    "reason": variance.get("reason", ""),
                    "impact": variance.get("impact", "low"),
                    "corrective_action": variance.get("action", ""),
                    "trend": variance.get("trend", "stable")
                }
        
        # Process spending trends
        if "trends" in tracking:
            processed["trends"] = {
                "daily_averages": tracking["trends"].get("daily_avg", {}),
                "weekly_totals": tracking["trends"].get("weekly_totals", {}),
                "trend_analysis": tracking["trends"].get("analysis", []),
                "burn_rate": tracking["trends"].get("burn_rate", 0),
                "forecast": tracking["trends"].get("forecast", {})
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
                    "timestamp": alert.get("timestamp", datetime.now().isoformat()),
                    "priority": alert.get("priority", "medium")
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
                "risk_factors": tracking["projections"].get("risks", []),
                "mitigation_strategies": tracking["projections"].get("mitigation_strategies", [])
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
    
    def _analyze_vendor_performance(
        self,
        vendor_data: Dict[str, Any],
        actuals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze vendor performance and payment status."""
        try:
            vendor_analysis = {
                "spend_by_vendor": {},
                "payment_status": {},
                "performance_metrics": {}
            }
            
            for vendor_id, vendor in vendor_data.items():
                # Calculate total spend for vendor
                total_spend = sum(
                    expense["amount"]
                    for category in actuals.values()
                    for expense in category.values()
                    if isinstance(expense, dict) and expense.get("vendor_id") == vendor_id
                )
                
                # Calculate payment metrics
                payments = vendor.get("payments", [])
                total_paid = sum(payment["amount"] for payment in payments)
                outstanding = total_spend - total_paid
                
                # Calculate performance metrics
                delivery_delays = vendor.get("delivery_delays", [])
                avg_delay = sum(delay["days"] for delay in delivery_delays) / len(delivery_delays) if delivery_delays else 0
                quality_ratings = vendor.get("quality_ratings", [])
                avg_rating = sum(rating["score"] for rating in quality_ratings) / len(quality_ratings) if quality_ratings else 0
                
                vendor_analysis["spend_by_vendor"][vendor_id] = {
                    "name": vendor.get("name", "Unknown"),
                    "total_spend": total_spend,
                    "categories": self._get_vendor_categories(vendor_id, actuals)
                }
                
                vendor_analysis["payment_status"][vendor_id] = {
                    "total_spend": total_spend,
                    "total_paid": total_paid,
                    "outstanding": outstanding,
                    "payment_history": payments,
                    "upcoming_payments": self._get_upcoming_payments(vendor)
                }
                
                vendor_analysis["performance_metrics"][vendor_id] = {
                    "avg_delivery_delay": avg_delay,
                    "quality_rating": avg_rating,
                    "reliability_score": self._calculate_reliability_score(avg_delay, avg_rating),
                    "cost_efficiency": self._calculate_cost_efficiency(vendor, total_spend),
                    "issues": vendor.get("issues", []),
                    "recommendations": self._generate_vendor_recommendations(
                        avg_delay,
                        avg_rating,
                        outstanding,
                        vendor.get("issues", [])
                    )
                }
            
            return vendor_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing vendor performance: {str(e)}", exc_info=True)
            return {
                "spend_by_vendor": {},
                "payment_status": {},
                "performance_metrics": {}
            }
    
    def _get_vendor_categories(
        self,
        vendor_id: str,
        actuals: Dict[str, Any]
    ) -> Dict[str, float]:
        """Get spending breakdown by category for a vendor."""
        categories = {}
        for category, expenses in actuals.items():
            category_total = sum(
                expense["amount"]
                for expense in expenses.values()
                if isinstance(expense, dict) and expense.get("vendor_id") == vendor_id
            )
            if category_total > 0:
                categories[category] = category_total
        return categories
    
    def _get_upcoming_payments(
        self,
        vendor: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get list of upcoming payments for a vendor."""
        now = datetime.now()
        return [
            payment for payment in vendor.get("scheduled_payments", [])
            if datetime.strptime(payment["due_date"], "%Y-%m-%d") > now
        ]
    
    def _calculate_reliability_score(
        self,
        avg_delay: float,
        avg_rating: float
    ) -> float:
        """Calculate vendor reliability score (0-100)."""
        # Convert avg_delay to a 0-10 scale (0 days = 10, 7+ days = 0)
        delay_score = max(0, 10 - (avg_delay / 0.7))
        # Convert avg_rating to 0-10 scale
        rating_score = avg_rating * 2  # Assuming ratings are 0-5
        # Combine scores with weights
        return (delay_score * 0.4 + rating_score * 0.6) * 10
    
    def _calculate_cost_efficiency(
        self,
        vendor: Dict[str, Any],
        total_spend: float
    ) -> Dict[str, Any]:
        """Calculate vendor cost efficiency metrics."""
        market_rates = vendor.get("market_rates", {})
        efficiency_metrics = {
            "overall_rating": "competitive",
            "savings_potential": 0.0,
            "rate_comparison": {}
        }
        
        for service, rate in vendor.get("rates", {}).items():
            market_rate = market_rates.get(service, rate)
            variance = (rate - market_rate) / market_rate if market_rate > 0 else 0
            efficiency_metrics["rate_comparison"][service] = {
                "vendor_rate": rate,
                "market_rate": market_rate,
                "variance_percent": variance * 100
            }
            
        # Calculate potential savings
        total_variance = sum(
            comp["variance_percent"] for comp in efficiency_metrics["rate_comparison"].values()
        )
        avg_variance = total_variance / len(efficiency_metrics["rate_comparison"]) if efficiency_metrics["rate_comparison"] else 0
        
        if avg_variance > 10:
            efficiency_metrics["overall_rating"] = "expensive"
            efficiency_metrics["savings_potential"] = total_spend * (avg_variance / 100)
        elif avg_variance < -5:
            efficiency_metrics["overall_rating"] = "cost_effective"
            
        return efficiency_metrics
    
    def _generate_vendor_recommendations(
        self,
        avg_delay: float,
        avg_rating: float,
        outstanding: float,
        issues: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations for vendor management."""
        recommendations = []
        
        if avg_delay > 3:
            recommendations.append(
                "Consider implementing delivery penalties in future contracts"
            )
        if avg_rating < 3.5:
            recommendations.append(
                "Review quality control processes and establish clear quality metrics"
            )
        if outstanding > 0:
            recommendations.append(
                f"Schedule payment of ₹{outstanding:,.2f} outstanding balance"
            )
        if len(issues) > 2:
            recommendations.append(
                "Schedule vendor performance review meeting"
            )
            
        return recommendations
    
    def _analyze_cash_flow(
        self,
        budget: Dict[str, Any],
        actuals: Dict[str, Any],
        vendor_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze cash flow and generate projections."""
        try:
            now = datetime.now()
            upcoming_payments = []
            
            # Collect all upcoming payments
            for vendor_id, vendor in vendor_data.items():
                upcoming_payments.extend([
                    {
                        "vendor_id": vendor_id,
                        "vendor_name": vendor.get("name", "Unknown"),
                        "amount": payment["amount"],
                        "due_date": payment["due_date"],
                        "category": payment.get("category", "Unknown")
                    }
                    for payment in vendor.get("scheduled_payments", [])
                    if datetime.strptime(payment["due_date"], "%Y-%m-%d") > now
                ])
            
            # Sort payments by due date
            upcoming_payments.sort(key=lambda x: x["due_date"])
            
            # Calculate current balance
            total_budget = budget["total_estimates"]["grand_total"]
            total_spent = sum(
                sum(expense.values())
                for category in actuals.values()
                for expense in category.values()
                if isinstance(expense, dict)
            )
            current_balance = total_budget - total_spent
            
            # Group upcoming payments by week
            weekly_requirements = {}
            for payment in upcoming_payments:
                due_date = datetime.strptime(payment["due_date"], "%Y-%m-%d")
                week_start = (due_date - timedelta(days=due_date.weekday())).strftime("%Y-%m-%d")
                if week_start not in weekly_requirements:
                    weekly_requirements[week_start] = {
                        "total": 0,
                        "payments": []
                    }
                weekly_requirements[week_start]["total"] += payment["amount"]
                weekly_requirements[week_start]["payments"].append(payment)
            
            return {
                "current_balance": current_balance,
                "upcoming_payments": upcoming_payments,
                "weekly_requirements": weekly_requirements,
                "cash_flow_health": self._assess_cash_flow_health(
                    current_balance,
                    weekly_requirements
                ),
                "recommendations": self._generate_cash_flow_recommendations(
                    current_balance,
                    weekly_requirements
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing cash flow: {str(e)}", exc_info=True)
            return {
                "current_balance": 0,
                "upcoming_payments": [],
                "weekly_requirements": {},
                "cash_flow_health": "unknown",
                "recommendations": []
            }
    
    def _assess_cash_flow_health(
        self,
        current_balance: float,
        weekly_requirements: Dict[str, Dict[str, Any]]
    ) -> str:
        """Assess cash flow health based on current balance and upcoming requirements."""
        try:
            # Calculate total upcoming requirements
            total_upcoming = sum(week["total"] for week in weekly_requirements.values())
            
            if current_balance <= 0:
                return "critical"
            elif current_balance < total_upcoming:
                return "at_risk"
            elif current_balance < total_upcoming * 1.2:
                return "caution"
            else:
                return "healthy"
                
        except Exception as e:
            logger.error(f"Error assessing cash flow health: {str(e)}", exc_info=True)
            return "unknown"
    
    def _generate_cash_flow_recommendations(
        self,
        current_balance: float,
        weekly_requirements: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Generate cash flow management recommendations."""
        recommendations = []
        total_upcoming = sum(week["total"] for week in weekly_requirements.values())
        
        if current_balance <= 0:
            recommendations.append(
                "URGENT: Immediate fund injection required to cover negative balance"
            )
        if current_balance < total_upcoming:
            recommendations.append(
                f"Secure additional funding of ₹{(total_upcoming - current_balance):,.2f} to cover upcoming payments"
            )
        
        # Analyze weekly distribution
        weekly_totals = [week["total"] for week in weekly_requirements.values()]
        if weekly_totals:
            max_weekly = max(weekly_totals)
            avg_weekly = sum(weekly_totals) / len(weekly_totals)
            
            if max_weekly > avg_weekly * 1.5:
                recommendations.append(
                    "Consider renegotiating payment schedules to balance weekly cash requirements"
                )
        
        if current_balance > total_upcoming * 2:
            recommendations.append(
                "Consider investing excess funds or negotiating early payment discounts"
            )
            
        return recommendations 