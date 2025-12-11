from ..container import get_openai_service
from ..crawler.crawler_base import NewsWithSummary
from ..crawler.udn_crawler import UDNCrawler
from ..database import NewsArticle, db_instance


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
