"""
Scheduling Module

This module handles the creation and management of production schedules,
optimizing for location, crew availability, and other constraints.
"""

from sd1.src.scheduling.coordinator import SchedulingCoordinator

# Expose key classes at the module level
__all__ = ['SchedulingCoordinator'] 