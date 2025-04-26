from typing import Dict, Any, List
import json
import logging
from datetime import datetime
from .agents.cost_estimator_agent import CostEstimatorAgent
from .agents.budget_optimizer_agent import BudgetOptimizerAgent
from .agents.budget_tracker_agent import BudgetTrackerAgent

logger = logging.getLogger(__name__)

class BudgetingCoordinator:
    def __init__(self):
        logger.info("Initializing BudgetingCoordinator")
        self.cost_estimator = CostEstimatorAgent()
        self.budget_optimizer = BudgetOptimizerAgent()
        self.budget_tracker = BudgetTrackerAgent()
        self.current_budget = None
        self.current_tracking = None
        self.vendor_data = {}
        self.cash_flow_data = None
    
    async def initialize_budget(
        self,
        production_data: Dict[str, Any],
        location_data: Dict[str, Any],
        crew_data: Dict[str, Any],
        target_budget: float = None,
        constraints: Dict[str, Any] = None,
        vendor_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Initialize production budget with estimates and optimization."""
        try:
            # Store vendor data if provided
            if vendor_data:
                self.vendor_data = vendor_data
            
            # Validate input data
            self._validate_input_data(production_data, location_data, crew_data)
            logger.info("Input data validated successfully")
            
            # Step 1: Generate initial cost estimates
            logger.info("Generating initial cost estimates")
            estimates = await self.cost_estimator.estimate_costs(
                production_data,
                location_data,
                crew_data
            )
            
            if not estimates:
                logger.error("Cost estimator returned empty estimates")
                raise ValueError("Failed to generate cost estimates")
            
            logger.info("Cost estimates generated successfully")
            
            # Step 2: Optimize budget if target or constraints provided
            if target_budget or constraints:
                logger.info("Optimizing budget with constraints")
                optimization = await self.budget_optimizer.optimize_budget(
                    estimates,
                    constraints or {},
                    target_budget
                )
                
                if not optimization:
                    logger.error("Budget optimizer returned empty optimization")
                    raise ValueError("Failed to optimize budget")
                
                # Update estimates with optimizations
                final_budget = self._apply_optimization(estimates, optimization)
                logger.info("Budget optimization applied successfully")
            else:
                final_budget = estimates
            
            # Store current budget
            self.current_budget = final_budget
            
            # Initialize cash flow tracking if vendor data is available
            if vendor_data:
                self.cash_flow_data = await self.budget_tracker._analyze_cash_flow(
                    final_budget,
                    {},  # No actuals yet
                    vendor_data
                )
            
            return final_budget
            
        except Exception as e:
            logger.error(f"Failed to initialize budget: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize budget: {str(e)}")
    
    async def track_budget(
        self,
        actual_expenses: Dict[str, Any],
        tracking_period: str,
        vendor_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Track actual expenses against current budget with vendor analysis."""
        try:
            if not self.current_budget:
                logger.error("Budget not initialized before tracking")
                raise ValueError("Budget must be initialized before tracking")
            
            # Update vendor data if provided
            if vendor_data:
                self.vendor_data = vendor_data
            
            # Validate actual expenses data
            self._validate_expenses_data(actual_expenses)
            logger.info("Actual expenses data validated")
            
            # Track expenses with vendor analysis
            tracking_data = await self.budget_tracker.track_expenses(
                self.current_budget,
                actual_expenses,
                tracking_period,
                self.vendor_data
            )
            
            if not tracking_data:
                logger.error("Budget tracker returned empty tracking data")
                raise ValueError("Failed to generate tracking data")
            
            # Update cash flow analysis
            if self.vendor_data:
                self.cash_flow_data = await self.budget_tracker._analyze_cash_flow(
                    self.current_budget,
                    actual_expenses,
                    self.vendor_data
                )
            
            # Store current tracking
            self.current_tracking = tracking_data
            logger.info("Budget tracking completed successfully")
            
            return tracking_data
            
        except Exception as e:
            logger.error(f"Failed to track budget: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to track budget: {str(e)}")
    
    async def analyze_vendor_performance(
        self,
        vendor_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Analyze vendor performance and payment status."""
        try:
            if not self.current_tracking:
                logger.error("No tracking data available for vendor analysis")
                raise ValueError("Budget tracking must be performed before vendor analysis")
            
            # Use provided vendor data or stored data
            vendor_data_to_analyze = vendor_data or self.vendor_data
            if not vendor_data_to_analyze:
                logger.error("No vendor data available for analysis")
                raise ValueError("Vendor data must be provided")
            
            analysis = await self.budget_tracker._analyze_vendor_performance(
                vendor_data_to_analyze,
                self.current_tracking.get("actuals", {})
            )
            
            logger.info("Vendor analysis completed successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze vendor performance: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to analyze vendor performance: {str(e)}")
    
    async def get_cash_flow_analysis(self) -> Dict[str, Any]:
        """Get current cash flow analysis and projections."""
        try:
            if not self.cash_flow_data:
                logger.error("No cash flow data available")
                raise ValueError("Cash flow analysis has not been performed")
            
            return {
                "cash_flow_status": self.cash_flow_data,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get cash flow analysis: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to get cash flow analysis: {str(e)}")
    
    async def optimize_current_budget(
        self,
        new_constraints: Dict[str, Any],
        new_target: float = None,
        vendor_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Re-optimize current budget based on new constraints or targets."""
        try:
            if not self.current_budget:
                logger.error("Budget not initialized before optimization")
                raise ValueError("Budget must be initialized before optimization")
            
            # Update vendor data if provided
            if vendor_data:
                self.vendor_data = vendor_data
            
            # Validate constraints
            self._validate_constraints(new_constraints)
            logger.info("New constraints validated")
            
            optimization = await self.budget_optimizer.optimize_budget(
                self.current_budget,
                new_constraints,
                new_target
            )
            
            if not optimization:
                logger.error("Budget optimizer returned empty optimization")
                raise ValueError("Failed to optimize budget")
            
            # Apply optimization to current budget
            optimized_budget = self._apply_optimization(
                self.current_budget,
                optimization
            )
            
            # Update current budget
            self.current_budget = optimized_budget
            
            # Update cash flow analysis if vendor data is available
            if self.vendor_data:
                self.cash_flow_data = await self.budget_tracker._analyze_cash_flow(
                    optimized_budget,
                    self.current_tracking.get("actuals", {}) if self.current_tracking else {},
                    self.vendor_data
                )
            
            logger.info("Budget optimization completed successfully")
            
            return {
                "optimized_budget": optimized_budget,
                "optimization_details": optimization,
                "cash_flow_impact": self.cash_flow_data if self.cash_flow_data else None
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize budget: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to optimize budget: {str(e)}")
    
    def get_budget_summary(self) -> Dict[str, Any]:
        """Get current budget and tracking summary with vendor and cash flow analysis."""
        try:
            if not self.current_budget:
                logger.error("Budget not initialized")
                raise ValueError("Budget not initialized")
            
            summary = {
                "budget_status": {
                    "total_budget": self.current_budget["total_estimates"]["grand_total"],
                    "last_updated": datetime.now().isoformat(),
                    "categories": {
                        category: total
                        for category, total in self.current_budget["total_estimates"].items()
                        if category != "grand_total"
                    }
                },
                "tracking_status": None,
                "vendor_status": None,
                "cash_flow_status": None
            }
            
            if self.current_tracking:
                summary["tracking_status"] = {
                    "period_summary": self.current_tracking["period_summary"],
                    "alerts": self.current_tracking["alerts"],
                    "projections": self.current_tracking["projections"]
                }
                
                if "vendor_analysis" in self.current_tracking:
                    summary["vendor_status"] = {
                        "total_vendors": len(self.current_tracking["vendor_analysis"]["spend_by_vendor"]),
                        "total_spend": sum(
                            vendor["total_spend"]
                            for vendor in self.current_tracking["vendor_analysis"]["spend_by_vendor"].values()
                        ),
                        "outstanding_payments": sum(
                            status["outstanding"]
                            for status in self.current_tracking["vendor_analysis"]["payment_status"].values()
                        ),
                        "performance_summary": {
                            vendor_id: metrics["reliability_score"]
                            for vendor_id, metrics in self.current_tracking["vendor_analysis"]["performance_metrics"].items()
                        }
                    }
            
            if self.cash_flow_data:
                summary["cash_flow_status"] = {
                    "current_balance": self.cash_flow_data["current_balance"],
                    "upcoming_total": sum(
                        payment["amount"]
                        for payment in self.cash_flow_data["upcoming_payments"]
                    ),
                    "health_status": self.cash_flow_data["cash_flow_health"],
                    "recommendations": self.cash_flow_data["recommendations"]
                }
            
            logger.info("Budget summary generated successfully")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get budget summary: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to get budget summary: {str(e)}")
    
    def _validate_input_data(
        self,
        production_data: Dict[str, Any],
        location_data: Dict[str, Any],
        crew_data: Dict[str, Any]
    ) -> None:
        """Validate input data for budget initialization."""
        if not isinstance(production_data, dict):
            raise ValueError("Production data must be a dictionary")
        if not isinstance(location_data, dict):
            raise ValueError("Location data must be a dictionary")
        if not isinstance(crew_data, dict):
            raise ValueError("Crew data must be a dictionary")
        
        required_production_fields = ["scene_count", "schedule_days"]
        for field in required_production_fields:
            if field not in production_data:
                raise ValueError(f"Missing required field in production data: {field}")
        
        if "locations" not in location_data:
            raise ValueError("Location data must include 'locations' field")
        
        required_crew_fields = ["size", "departments"]
        for field in required_crew_fields:
            if field not in crew_data:
                raise ValueError(f"Missing required field in crew data: {field}")
    
    def _validate_expenses_data(self, expenses: Dict[str, Any]) -> None:
        """Validate actual expenses data for tracking."""
        if not isinstance(expenses, dict):
            raise ValueError("Expenses data must be a dictionary")
        
        for category, data in expenses.items():
            if not isinstance(data, dict):
                raise ValueError(f"Invalid expenses data format for category: {category}")
            
            for item, cost in data.items():
                if not isinstance(cost, (int, float, dict)):
                    raise ValueError(f"Invalid cost format for {category}.{item}")
                if isinstance(cost, dict) and "vendor_id" in cost:
                    if not cost.get("amount"):
                        raise ValueError(f"Missing amount for vendor expense in {category}.{item}")
    
    def _validate_constraints(self, constraints: Dict[str, Any]) -> None:
        """Validate budget constraints."""
        if not isinstance(constraints, dict):
            raise ValueError("Constraints must be a dictionary")
        
        required_fields = ["quality_level", "equipment_preference", "crew_size"]
        for field in required_fields:
            if field not in constraints:
                raise ValueError(f"Missing required constraint: {field}")
    
    def _apply_optimization(
        self,
        current_budget: Dict[str, Any],
        optimization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply optimization changes to current budget."""
        try:
            optimized = current_budget.copy()
            
            # Apply cost reductions
            if "cost_reductions" in optimization:
                for category, reduction in optimization["cost_reductions"].items():
                    if category in optimized:
                        for item, data in optimized[category].items():
                            if isinstance(data, dict) and "total_cost" in data:
                                ratio = reduction["proposed_cost"] / reduction["current_cost"]
                                data["total_cost"] = data["total_cost"] * ratio
            
            # Apply reallocations
            if "reallocations" in optimization:
                for from_category, realloc in optimization["reallocations"].items():
                    if from_category in optimized and realloc["to_category"] in optimized:
                        amount = realloc["amount"]
                        # Reduce from source
                        if isinstance(optimized[from_category], dict):
                            for item in optimized[from_category].values():
                                if isinstance(item, dict) and "total_cost" in item:
                                    item["total_cost"] -= amount
                        # Add to destination
                        if isinstance(optimized[realloc["to_category"]], dict):
                            for item in optimized[realloc["to_category"]].values():
                                if isinstance(item, dict) and "total_cost" in item:
                                    item["total_cost"] += amount
            
            # Recalculate totals
            self._recalculate_totals(optimized)
            
            return optimized
            
        except Exception as e:
            logger.error(f"Failed to apply optimization: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to apply optimization: {str(e)}")
    
    def _recalculate_totals(self, budget: Dict[str, Any]) -> None:
        """Recalculate all total costs in the budget."""
        try:
            if "total_estimates" in budget:
                totals = budget["total_estimates"]
                
                # Recalculate category totals
                for category in totals:
                    if category != "grand_total":
                        category_data = budget.get(category.replace("total_", ""), {})
                        totals[category] = sum(
                            item["total_cost"]
                            for item in category_data.values()
                            if isinstance(item, dict) and "total_cost" in item
                        )
                
                # Recalculate grand total
                totals["grand_total"] = sum(
                    total for category, total in totals.items()
                    if category != "grand_total"
                )
        except Exception as e:
            logger.error(f"Failed to recalculate totals: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to recalculate totals: {str(e)}") 