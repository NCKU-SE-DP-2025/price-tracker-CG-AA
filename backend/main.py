import os

import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.container import get_openai_service
from src.crawler.crawler_base import NewsWithSummary
from src.crawler.udn_crawler import UDNCrawler
from src.database import NewsArticle, db_instance
from src.jobs import news_jobs
from src.news.router import router as news_router
from src.openai.service import OpenAIService
from src.prices.router import router as prices_router
from src.user.router import router as user_router

sentry_sdk.init(
    dsn="https://4001ffe917ccb261aa0e0c34026dc343@o4505702629834752.ingest.us.sentry.io/4507694792704000",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

app = FastAPI()
bgs = BackgroundScheduler()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def start_scheduler():
    # Run once on startup if the database is empty
    news_jobs.fetch_and_store_news(is_initial=True)

    # Schedule to run periodically
    bgs.add_job(news_jobs.fetch_and_store_news, "interval", minutes=100, args=[False])
    bgs.start()


@app.on_event("shutdown")
def shutdown_scheduler():
    bgs.shutdown()


app.include_router(user_router)
app.include_router(news_router)
app.include_router(prices_router)
