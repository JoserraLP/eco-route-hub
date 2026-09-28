"""
Domain enumeration types.

Provides strongly-typed string enumerations used across DTOs,
DAO persistence models, and estimation algorithm plugins.
"""

from enum import Enum


class MotorTypeEnum(str, Enum):
    """Supported vehicle powertrain types."""
    ELECTRIC = "ELECTRIC"
    DIESEL = "DIESEL"
    GASOLINE = "GASOLINE"
    HYBRID = "HYBRID"


class RouteTypeEnum(str, Enum):
    """Route optimization criteria types."""
    FASTEST = "FASTEST"
    SHORTEST = "SHORTEST"
    ECO = "ECO"


class FeatureTopicEnum(str, Enum):
    """App feature feedback categories for user reviews."""
    ACCESSIBILITY = "ACCESABILITY"
    RESPONSETIME = "RESPONSETIME"
    CONFIGURABILITY = "CONFIGURABILITY"
    USABILITY = "USABILITY"
    TRUSTABILITY = "TRUSTABILITY"
    ROBUSTNESS = "ROBUSTNESS"
    UTILITY = "UTILITY"


class DrivingBehaviorEnum(str, Enum):
    """Driver behavior profiles used in energy consumption algorithms."""
    ECO = "eco"
    DEFENSIVE = "defensive"
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"
    AUTONOMOUS_EFFICIENT = "autonomous_efficient"