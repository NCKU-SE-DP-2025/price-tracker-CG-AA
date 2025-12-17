# Re-export all components for backward compatibility
# Also re-export NewsArticleRepository for backward compatibility
from ..repositories.news_repository import NewsArticleRepository
from .core import Base, Database, db_instance, get_db
from .models import USER_NEWS_ASSOCIATION_TABLE, NewsArticle, User

__all__ = [
    "Base",
    "Database",
    "db_instance",
    "get_db",
    "NewsArticle",
    "NewsArticleRepository",
    "User",
    "USER_NEWS_ASSOCIATION_TABLE",
]
