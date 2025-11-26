import os

import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.container import get_openai_service
from src.crawler.crawler_base import NewsWithSummary
from src.crawler.udn_crawler import UDNCrawler
from src.database import NewsArticle, db_instance
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


def fetch_and_store_news(is_initial: bool = False):
    """Wrapper function to fetch, process, and store news."""
    print(f"Starting news fetch job. Initial run: {is_initial}")
    with db_instance.get_session() as db:
        try:
            if is_initial and db.query(NewsArticle).count() > 0:
                print("Database is not empty. Skipping initial population.")
                return

            crawler = UDNCrawler(timeout=10)
            open_ai_service = get_openai_service()

            # mimic old behavior: initial run fetches multiple pages, later runs only one
            search_term = "價格"
            page = (1, 10) if is_initial else 1

            headlines = crawler.get_headline(search_term=search_term, page=page)
            print(f"Fetched {len(headlines)} headlines from UDN.")

            for headline in headlines:
                try:
                    news = crawler.parse(str(headline.url))

                    # --- build NewsWithSummary from News ---
                    # Expecting something like: {"summary": "...", "reason": "..."}
                    summary_data = open_ai_service.summarize_article([news.content])
                    if not summary_data:
                        print(f"Skipping article (no summary): {headline.url}")
                        continue

                    news_with_summary = NewsWithSummary(
                        title=news.title,
                        url=news.url,
                        time=news.time,
                        content=news.content,
                        summary=summary_data["summary"],
                        reason=summary_data["reason"],
                    )
                    # --------------------------------------

                    crawler.save(news_with_summary, db)
                    print(f"Saved article: {news_with_summary.title}")
                except Exception as e:
                    print(f"Error processing article {headline.url}: {e}")

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
