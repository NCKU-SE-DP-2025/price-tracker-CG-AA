from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from ..crawler.udn_crawler import UDNCrawler
from ..database import NewsArticleRepository
from ..openai.service import OpenAIService


class NewsProcessor:
    def __init__(
        self,
        db_session: Session,
        open_ai_service: OpenAIService,
        udn_crawler: UDNCrawler,
    ):
        self.news_repo = NewsArticleRepository(db_session)
        self.open_ai_service = open_ai_service
        self.udn_crawler = udn_crawler
        self.udn_api_url = "https://udn.com/api/more"

    def search_news_by_prompt(self, prompt: str) -> list[dict]:
        """
        Search for news articles based on a user prompt.

        1. Extract keywords from the prompt using AI
        2. Fetch news articles using those keywords
        3. Scrape detailed content from each article
        4. Return sorted results by time
        """
        # Step 1: Extract keywords from prompt
        keywords = self.open_ai_service.extract_keywords(prompt)
        if not keywords:
            print("Failed to extract keywords from prompt")
            return []

        print(f"Extracted keywords: {keywords}")

        # Step 2: Fetch news items using the extracted keywords
        news_items = self.udn_crawler.get_headline(keywords, 10)
        if not news_items:
            print("No news items found")
            return []

        # Step 3: Scrape detailed content from each article
        news_list = []
        for item in news_items:
            url = item.url
            if not url:
                continue

            try:
                news = self.udn_crawler.parse(str(url))
                detailed_news = {
                    "url": news.url,
                    "title": news.title,
                    "time": news.time,
                    "content": news.content,
                }
                if not detailed_news:
                    continue

                # Join content paragraphs into a single string
                detailed_news["content"] = " ".join(detailed_news.get("content", []))
                news_list.append(detailed_news)
            except Exception as e:
                print(f"Error processing article {url}: {e}")
                continue

        # Step 4: Sort by time (newest first) and return
        return sorted(news_list, key=lambda x: x.get("time", ""), reverse=True)
