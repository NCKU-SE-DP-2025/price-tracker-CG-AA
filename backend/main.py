import asyncio
import os
from typing import List

import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.database import (
    NewsArticle,
    NewsArticleRepository,
    User,
    db_instance,
    get_db,
)
from src.news import NewsProcessor, NewsSummaryRequestSchema, PromptRequest
from src.user import UserAuthSchema, auth_service

sentry_sdk.init(
    dsn="https://4001ffe917ccb261aa0e0c34026dc343@o4505702629834752.ingest.us.sentry.io/4507694792704000",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

app = FastAPI()
bgs = BackgroundScheduler()

# It's recommended to load secrets from environment variables
# For local development, you can set this before running the app:
# export OPENAI_API_KEY='your_key_here'
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "xxx")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def fetch_and_store_news(is_initial: bool = False):
    """Wrapper function to fetch, process, and store news."""
    print(f"Starting news fetch job. Initial run: {is_initial}")
    with db_instance.get_session() as db:
        try:
            if is_initial and db.query(NewsArticle).count() > 0:
                print("Database is not empty. Skipping initial population.")
                return

            news_processor = NewsProcessor(db, OPENAI_API_KEY)
            news_processor.process_news(is_initial=is_initial)
            print("News fetch job finished.")
        except Exception as e:
            print(f"An error occurred during news processing: {e}")


@app.on_event("startup")
def start_scheduler():
    # Run once on startup if the database is empty
    fetch_and_store_news(is_initial=True)

    # Schedule to run periodically
    bgs.add_job(fetch_and_store_news, "interval", minutes=100, args=[False])
    bgs.start()


@app.on_event("shutdown")
def shutdown_scheduler():
    bgs.shutdown()


# --- User Authentication Endpoints ---


@app.post("/api/v1/users/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Handles user login and returns a JWT access token."""
    user = auth_service.authenticate_user(
        db, form_data.username, form_data.password
    )
    access_token = auth_service.create_access_token(
        data={"sub": user.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/v1/users/register", status_code=status.HTTP_201_CREATED)
def create_user(user: UserAuthSchema, db: Session = Depends(get_db)):
    """Registers a new user."""
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    hashed_password = auth_service.get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {
        "username": db_user.username,
        "message": "User created successfully",
    }


@app.get("/api/v1/users/me")
def read_users_me(current_user: User = Depends(auth_service.get_current_user)):
    """Returns the current authenticated user's details."""
    return {"username": current_user.username}


# --- News Endpoints ---


@app.get("/api/v1/news/news")
def read_news(db: Session = Depends(get_db)):
    """Returns all news articles for anonymous users."""
    news_repo = NewsArticleRepository(db)
    news = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for n in news:
        upvotes, upvoted = news_repo.get_article_upvote_details(n.id, None)
        result.append(
            {**n.__dict__, "upvotes": upvotes, "is_upvoted": upvoted}
        )
    return result


@app.get("/api/v1/news/user_news")
def read_user_news(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    Returns all news articles for an authenticated user, with upvote status.
    """
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


@app.post("/api/v1/news/search_news")
async def search_news(request: PromptRequest, db: Session = Depends(get_db)):
    """
    (This endpoint is deprecated as per the new design)
    Searches for news based on a prompt. This functionality is now handled
    by the background news processing job.
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="This search endpoint is deprecated. "
        "News is now fetched automatically.",
    )


@app.post("/api/v1/news/news_summary")
async def news_summary(
    payload: NewsSummaryRequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """Generates a summary for a given news content."""
    news_processor = NewsProcessor(db, OPENAI_API_KEY)
    summary_data = news_processor._summarize_article(payload.content.split())
    if not summary_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary.",
        )
    return summary_data


@app.post("/api/v1/news/{article_id}/upvote")
def upvote_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """Toggles an upvote on an article for the current user."""
    news_repo = NewsArticleRepository(db)
    if not news_repo.exists(article_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )
    message = news_repo.toggle_upvote(article_id, current_user.id)
    return {"message": message}


# --- External Price API Endpoint ---


@app.get("/api/v1/prices/necessities-price", response_model=List[dict])
async def get_necessities_prices(
    category: str = Query(None), commodity: str = Query(None)
):
    """
    Fetches necessities prices. If no category or commodity is specified,
    it fetches all prices for all commodities defined in the application.
    Otherwise, it acts as a proxy to the external government API for the
    specified query.
    """
    import httpx

    async with httpx.AsyncClient() as client:

        # Original proxy behavior for specific queries with retry
        last_exception = None
        params = {}
        if category and commodity:
            params = {"CategoryName": category, "Name": commodity}
        else:
            params = {"CategoryName": "'", "Name": "'"}
        for _ in range(2):  # Try up to 2 times
            try:
                response = await client.get(
                    "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice",
                    params=params,
                    timeout=10,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                await asyncio.sleep(1)
            except httpx.RequestError as e:
                last_exception = e
                await asyncio.sleep(1)

        if isinstance(last_exception, httpx.HTTPStatusError):
            raise HTTPException(
                status_code=last_exception.response.status_code,
                detail="External API returned an error: "
                f"{last_exception.response.text}",
            )
        if isinstance(last_exception, httpx.RequestError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not fetch data from external API: "
                f"{last_exception}",
            )
