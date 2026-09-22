from abc import ABC

from route_consumption_estimator.domain import DrivingBehaviorEnum


class DrivingBehaviorProvider(ABC):
    def __init__(self):
        self._driving_behavior: DrivingBehaviorEnum = DrivingBehaviorEnum.NORMAL

    @property
    def driving_behavior(self):
        return self._driving_behavior

    @driving_behavior.setter
    def driving_behavior(self, value):
        self._driving_behavior = value
