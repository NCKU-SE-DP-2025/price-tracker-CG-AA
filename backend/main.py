import os

import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database import NewsArticle, db_instance
from src.news.router import router as news_router
from src.news.service import NewsProcessor
from src.prices.router import router as prices_router
from src.user.router import router as user_router

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


app.include_router(user_router)
app.include_router(news_router)
app.include_router(prices_router)
