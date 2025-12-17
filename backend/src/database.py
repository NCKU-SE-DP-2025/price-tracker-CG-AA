from contextlib import contextmanager
from typing import Union

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    case,
    create_engine,
    delete,
    func,
    insert,
    literal,
    select,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

from .crawler.crawler_base import NewsWithSummary

Base = declarative_base()

USER_NEWS_ASSOCIATION_TABLE = Table(
    "user_news_upvotes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column(
        "news_articles_id",
        Integer,
        ForeignKey("news_articles.id"),
        primary_key=True,
    ),
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    upvoted_news = relationship(
        "NewsArticle",
        secondary=USER_NEWS_ASSOCIATION_TABLE,
        back_populates="upvoted_by_users",
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    time = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    upvoted_by_users = relationship(
        "User",
        secondary=USER_NEWS_ASSOCIATION_TABLE,
        back_populates="upvoted_news",
    )


class Database:
    def __init__(self, db_url: str = "sqlite:///news_database.db", echo: bool = True):
        self.engine = create_engine(db_url, echo=echo)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self._create_tables()

    def _create_tables(self):
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()


class NewsArticleRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def add_article(
        self, article_data: Union[NewsWithSummary, dict]
    ) -> NewsArticle | None:
        """
        Adds a new news article to the database.
        Accepts either a NewsWithSummary Pydantic model or a dictionary.
        Skips duplicates based on URL.

        :param article_data: A NewsWithSummary model or dictionary containing news article data.
        :return: The created NewsArticle object, or None if duplicate.
        """
        # Convert Pydantic model to dict if needed
        if isinstance(article_data, NewsWithSummary):
            data = {
                "url": str(article_data.url),
                "title": article_data.title,
                "time": article_data.time,
                "content": article_data.content,
                "summary": article_data.summary,
                "reason": article_data.reason,
            }
        else:
            data = article_data

        # Check for duplicate by URL
        if self.find_by_url(str(data["url"])):
            print(f"Article already exists: {data['url']}")
            return None

        # Handle content - join if list, use as-is if string
        content = data["content"]
        if isinstance(content, list):
            content = " ".join(content)

        new_article = NewsArticle(
            url=str(data["url"]),
            title=data["title"],
            time=data["time"],
            content=content,
            summary=data["summary"],
            reason=data["reason"],
        )

        try:
            self.db.add(new_article)
            self.db.commit()
            self.db.refresh(new_article)
            return new_article
        except SQLAlchemyError as e:
            self.db.rollback()
            print(f"Database commit failed: {e}")
            raise

    def get_article_upvote_details(self, article_id: int, user_id: int | None):
        count = (
            self.db.query(USER_NEWS_ASSOCIATION_TABLE)
            .filter_by(news_articles_id=article_id)
            .count()
        )
        voted = False
        if user_id:
            voted = (
                self.db.query(USER_NEWS_ASSOCIATION_TABLE)
                .filter_by(news_articles_id=article_id, user_id=user_id)
                .first()
                is not None
            )
        return count, voted

    def get_all_news_with_upvotes(
        self, user_id: int | None = None
    ) -> list[tuple[NewsArticle, int, bool]]:
        """
        Fetch all news articles with upvote counts and user's upvote status
        in a single optimized query using JOINs/subqueries.

        :param user_id: The current user's ID, or None for anonymous users.
        :return: List of tuples (NewsArticle, upvotes_count, is_upvoted).
        """
        # Subquery for upvote counts per article
        upvote_count_subq = (
            self.db.query(
                USER_NEWS_ASSOCIATION_TABLE.c.news_articles_id,
                func.count().label("upvotes"),
            )
            .group_by(USER_NEWS_ASSOCIATION_TABLE.c.news_articles_id)
            .subquery()
        )

        if user_id is not None:
            # Subquery for user's upvoted article IDs
            user_upvote_subq = (
                self.db.query(USER_NEWS_ASSOCIATION_TABLE.c.news_articles_id)
                .filter(USER_NEWS_ASSOCIATION_TABLE.c.user_id == user_id)
                .subquery()
            )

            # Main query with both upvote count and user's upvote status
            query = (
                self.db.query(
                    NewsArticle,
                    func.coalesce(upvote_count_subq.c.upvotes, 0).label("upvotes"),
                    case(
                        (user_upvote_subq.c.news_articles_id.isnot(None), True),
                        else_=False,
                    ).label("is_upvoted"),
                )
                .outerjoin(
                    upvote_count_subq,
                    NewsArticle.id == upvote_count_subq.c.news_articles_id,
                )
                .outerjoin(
                    user_upvote_subq,
                    NewsArticle.id == user_upvote_subq.c.news_articles_id,
                )
                .order_by(NewsArticle.time.desc())
            )
        else:
            # Query without user upvote status (anonymous user)
            query = (
                self.db.query(
                    NewsArticle,
                    func.coalesce(upvote_count_subq.c.upvotes, 0).label("upvotes"),
                    literal(False).label("is_upvoted"),
                )
                .outerjoin(
                    upvote_count_subq,
                    NewsArticle.id == upvote_count_subq.c.news_articles_id,
                )
                .order_by(NewsArticle.time.desc())
            )

        return query.all()

    def exists(self, article_id: int) -> bool:
        return self.db.query(NewsArticle).filter_by(id=article_id).first() is not None

    def toggle_upvote(self, article_id: int, user_id: int) -> str:
        existing_upvote = self.db.execute(
            select(USER_NEWS_ASSOCIATION_TABLE).where(
                USER_NEWS_ASSOCIATION_TABLE.c.news_articles_id == article_id,
                USER_NEWS_ASSOCIATION_TABLE.c.user_id == user_id,
            )
        ).scalar()

        if existing_upvote:
            delete_stmt = delete(USER_NEWS_ASSOCIATION_TABLE).where(
                USER_NEWS_ASSOCIATION_TABLE.c.news_articles_id == article_id,
                USER_NEWS_ASSOCIATION_TABLE.c.user_id == user_id,
            )
            self.db.execute(delete_stmt)
            self.db.commit()
            return "Upvote removed"
        else:
            insert_stmt = insert(USER_NEWS_ASSOCIATION_TABLE).values(
                news_articles_id=article_id, user_id=user_id
            )
            self.db.execute(insert_stmt)
            self.db.commit()
            return "Article upvoted"

    def find_by_url(self, url: str) -> NewsArticle | None:
        return self.db.query(NewsArticle).filter_by(url=url).first()


# Global database instance
db_instance = Database()


# Dependency for FastAPI or other frameworks
def get_db():
    with db_instance.get_session() as session:
        yield session
