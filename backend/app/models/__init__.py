"""数据模型模块"""

from app.models.user import User, OTPCode, UserConsent, QuizSession
from app.models.admin import AdminUser, SystemConfig, QuizQuestion, Supplement
from app.models.product import Product
from app.models.usage import AIUsage
from app.models.analytics import AnalyticsEvent
from app.models.recommendation import RecommendationSession, RecommendationItem
from app.models.review import ReviewQueue
from app.models.user_history import QuizHistory, FavoriteProduct

__all__ = [
    "User",
    "OTPCode",
    "UserConsent",
    "QuizSession",
    "AdminUser",
    "SystemConfig",
    "QuizQuestion",
    "Supplement",
    "Product",
    "AIUsage",
    "AnalyticsEvent",
    "RecommendationSession",
    "RecommendationItem",
    "ReviewQueue",
    "QuizHistory",
    "FavoriteProduct",
]
