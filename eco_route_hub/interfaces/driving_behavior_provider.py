"""
Driving behavior provider interface.

Defines the abstract base class for identifying, modeling, or injecting 
driver behavior profiles into energy consumption calculation pipelines.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from eco_route_hub.domain.enums import DrivingBehaviorEnum


class DrivingBehaviorProvider(ABC):
    """
    Abstract Base Class for driver behavior providers and evaluators.

    Attributes:
        driving_behavior (DrivingBehaviorEnum): Currently selected driver behavior profile.
    """

    def __init__(
        self,
        default_behavior: DrivingBehaviorEnum = DrivingBehaviorEnum.NORMAL,
    ) -> None:
        self.driving_behavior: DrivingBehaviorEnum = default_behavior

    @abstractmethod
    def evaluate_behavior(
        self, telemetry_data: Optional[Dict[str, Any]] = None
    ) -> DrivingBehaviorEnum:
        """
        Evaluate and determine the driving behavior profile based on trip telemetry or parameters.

        Args:
            telemetry_data (Optional[Dict[str, Any]]): Route telemetry metrics 
                (e.g., speed variations, stops per km, aggressiveness score).

        Returns:
            DrivingBehaviorEnum: Evaluated driver behavior profile.
        """
        pass
