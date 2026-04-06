"""
Shared Python enums that are used by both ORM models and application constants.
Defined here to avoid circular imports between models/ and core/.
"""

import enum


class InstitutionType(str, enum.Enum):
    university = "university"
    college = "college"


class DemandTrend(str, enum.Enum):
    growing = "growing"
    stable = "stable"
    declining = "declining"


class ScrapeStatus(str, enum.Enum):
    running = "running"
    success = "success"
    failed = "failed"
    anomaly = "anomaly"
