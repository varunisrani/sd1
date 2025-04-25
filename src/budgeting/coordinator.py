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
    
    async def initialize_budget(
        self,
        production_data: Dict[str, Any],
        location_data: Dict[str, Any],
        crew_data: Dict[str, Any],
        target_budget: float = None,
        constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Initialize production budget with estimates and optimization."""
        try:
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
            
            return final_budget
            
        except Exception as e:
            logger.error(f"Failed to initialize budget: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize budget: {str(e)}")
    
    async def track_budget(
        self,
        actual_expenses: Dict[str, Any],
        tracking_period: str
    ) -> Dict[str, Any]:
        """Track actual expenses against current budget."""
        try:
            if not self.current_budget:
                logger.error("Budget not initialized before tracking")
                raise ValueError("Budget must be initialized before tracking")
            
            # Validate actual expenses data
            self._validate_expenses_data(actual_expenses)
            logger.info("Actual expenses data validated")
            
            tracking_data = await self.budget_tracker.track_expenses(
                self.current_budget,
                actual_expenses,
                tracking_period
            )
            
            if not tracking_data:
                logger.error("Budget tracker returned empty tracking data")
                raise ValueError("Failed to generate tracking data")
            
            # Store current tracking
            self.current_tracking = tracking_data
            logger.info("Budget tracking completed successfully")
            
            return tracking_data
            
        except Exception as e:
            logger.error(f"Failed to track budget: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to track budget: {str(e)}")
    
    async def optimize_current_budget(
        self,
        new_constraints: Dict[str, Any],
        new_target: float = None
    ) -> Dict[str, Any]:
        """Re-optimize current budget based on new constraints or targets."""
        try:
            if not self.current_budget:
                logger.error("Budget not initialized before optimization")
                raise ValueError("Budget must be initialized before optimization")
            
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
            logger.info("Budget optimization completed successfully")
            
            return {
                "optimized_budget": optimized_budget,
                "optimization_details": optimization
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize budget: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to optimize budget: {str(e)}")
    
    def get_budget_summary(self) -> Dict[str, Any]:
        """Get current budget and tracking summary."""
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
                "tracking_status": None
            }
            
            if self.current_tracking:
                summary["tracking_status"] = {
                    "period_summary": self.current_tracking["period_summary"],
                    "alerts": self.current_tracking["alerts"],
                    "projections": self.current_tracking["projections"]
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