import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import NewsArticle, NewsArticleRepository, User, get_db
from ..user.service import auth_service
from .schemas import (
    NewsSearchResultSchema,
    NewsSummaryRequestSchema,
    PromptRequest,
)
from .service import NewsProcessor

router = APIRouter(prefix="/api/v1/news", tags=["news"])
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "xxx")


@router.get("/news")
def read_news(db: Session = Depends(get_db)):
    news_repo = NewsArticleRepository(db)
    news = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for n in news:
        upvotes, upvoted = news_repo.get_article_upvote_details(n.id, None)
        result.append(
            {**n.__dict__, "upvotes": upvotes, "is_upvoted": upvoted}
        )
    return result


@router.get("/user_news")
def read_user_news(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    news_repo = NewsArticleRepository(db)
    news = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for article in news:
        upvotes, upvoted = news_repo.get_article_upvote_details(
            article.id, current_user.id
        )
        result.append(
            {
                **article.__dict__,
                "upvotes": upvotes,
                "is_upvoted": upvoted,
            }
        )
    return result


@router.post("/search_news", response_model=list[NewsSearchResultSchema])
async def search_news(request: PromptRequest, db: Session = Depends(get_db)):
    """
    Search for news articles based on a user prompt.
    Uses AI to extract keywords and fetches detailed article content.
    """
    news_processor = NewsProcessor(db, OPENAI_API_KEY)
    results = news_processor.search_news_by_prompt(request.prompt)

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No news articles found for the given prompt",
        )

    return results


@router.post("/news_summary")
async def news_summary(
    payload: NewsSummaryRequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    news_processor = NewsProcessor(db, OPENAI_API_KEY)
    summary_data = news_processor._summarize_article(payload.content.split())
    if not summary_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary.",
        )
    return summary_data


@router.post("/{article_id}/upvote")
def upvote_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    news_repo = NewsArticleRepository(db)
    if not news_repo.exists(article_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )
    message = news_repo.toggle_upvote(article_id, current_user.id)
    return {"message": message}
