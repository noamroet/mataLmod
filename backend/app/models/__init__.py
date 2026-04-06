"""
Import all models here so that:
1. SQLAlchemy registers them with Base.metadata before Alembic autogenerate runs.
2. Relationship forward references resolve correctly.
"""

from app.models.base import Base
from app.models.career_data import CareerData
from app.models.institution import Institution
from app.models.program import Program
from app.models.saved_program import SavedProgram
from app.models.scrape_run import ScrapeRun
from app.models.sekem_formula import SekemFormula
from app.models.syllabus import Syllabus
from app.models.user import User

__all__ = [
    "Base",
    "Institution",
    "Program",
    "SekemFormula",
    "Syllabus",
    "CareerData",
    "ScrapeRun",
    "User",
    "SavedProgram",
]
