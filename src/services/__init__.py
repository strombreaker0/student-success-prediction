"""Services package initialization."""
from src.services import auth_service
from src.services import student_service
from src.services import prediction_service
from src.services import academic_history_service

__all__ = ["auth_service", "student_service", "prediction_service", "academic_history_service"]
