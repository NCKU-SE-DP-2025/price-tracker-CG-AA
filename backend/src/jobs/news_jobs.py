from typing import Tuple, Union

from sqlalchemy.orm import Session

from ..container import get_openai_service
from ..crawler.crawler_base import NewsWithSummary
from ..crawler.udn_crawler import UDNCrawler
from ..database import NewsArticleRepository, db_instance

# Configuration Constants
SEARCH_TERM = "價格"
CRAWLER_TIMEOUT = 10
INITIAL_PAGE_RANGE = (1, 10)
DEFAULT_PAGE = 1


def _should_skip_initial_run(db: Session, is_initial: bool) -> bool:
    """Checks if the database is already populated during an initial run."""
    from ..database import NewsArticle

    if is_initial and db.query(NewsArticle).count() > 0:
        print("Database is not empty. Skipping initial population.")
        return True
    return False


def _process_and_save_article(
    crawler: UDNCrawler, open_ai_service, db: Session, headline
) -> None:
    """
    Fetches details for a single headline, summarizes it, and saves it to the DB.
    Encapsulates specific article error handling.
    """
    try:
        news = crawler.parse(str(headline.url))

        # Fetch Summary
        summary_data = open_ai_service.summarize_article([news.content])

        # Guard clause: Ensure we have valid data before proceeding
        if not summary_data:
            print(f"Skipping article (no summary): {headline.url}")
            return

        news_with_summary = NewsWithSummary(
            title=news.title,
            url=news.url,
            time=news.time,
            content=news.content,
            summary=summary_data["summary"],
            reason=summary_data["reason"],
        )

        # Use repository to save article
        repo = NewsArticleRepository(db)
        saved_article = repo.add_article(news_with_summary)
        if saved_article:
            print(f"Saved article: {news_with_summary.title}")

    except Exception as e:
        print(f"Error processing article {headline.url}: {e}")


def fetch_and_store_news(is_initial: bool = False):
    """Wrapper function to fetch, process, and store news."""
    print(f"Starting news fetch job. Initial run: {is_initial}")

    with db_instance.get_session() as db:
        try:
            # 1. Validation Phase
            if _should_skip_initial_run(db, is_initial):
                return

            # 2. Setup Phase
            crawler = UDNCrawler(timeout=CRAWLER_TIMEOUT)
            open_ai_service = get_openai_service()

            # Determine fetching strategy
            pages: Union[int, Tuple[int, int]] = (
                INITIAL_PAGE_RANGE if is_initial else DEFAULT_PAGE
            )

            # 3. Execution Phase
            headlines = crawler.get_headline(search_term=SEARCH_TERM, page=pages)
            print(f"Fetched {len(headlines)} headlines from UDN.")

            for headline in headlines:
                _process_and_save_article(crawler, open_ai_service, db, headline)

            print("News fetch job finished.")

        except Exception as e:
            # Catch-all for high-level failures (e.g., crawler initialization fails)
            print(f"An error occurred during news processing: {e}")
