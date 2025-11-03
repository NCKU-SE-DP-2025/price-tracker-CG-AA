import json
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import NewsArticleRepository


class PromptRequest(BaseModel):
    prompt: str


class NewsSummaryRequestSchema(BaseModel):
    content: str


class NewsProcessor:
    def __init__(self, db_session: Session, openai_api_key: str):
        self.news_repo = NewsArticleRepository(db_session)
        self.ai_client = OpenAI(api_key=openai_api_key)
        self.udn_api_url = "https://udn.com/api/more"

    def _fetch_news_from_api(
        self, search_term: str, is_initial: bool = False
    ) -> list[dict]:
        """
        Fetch news metadata from UDN's search API.

        :param search_term: The term to search for.
        :param is_initial: If True, fetches multiple pages (1..9);
          else only page 1.
        :return: A list of raw news objects from the API
          (contains title, titleLink, etc.).
        """
        all_news_data: list[dict] = []
        pages_to_fetch = range(1, 10) if is_initial else range(1, 2)

        for page_num in pages_to_fetch:
            params = {
                "page": page_num,
                "id": f"search:{quote(search_term)}",
                "channelId": 2,
                "type": "searchword",
            }
            try:
                response = requests.get(
                    self.udn_api_url, params=params, timeout=10
                )
                response.raise_for_status()
                all_news_data.extend(response.json().get("lists", []))
            except requests.RequestException as e:
                print(
                    f"Error fetching news from UDN API (page {page_num}): {e}"
                )
                break

        return all_news_data

    def _check_relevance(self, title: str) -> bool:
        """
        Ask the model to judge if the title is about
        「民生用品的價格變化」.

        Returns True only if model answers 'high'.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一個關聯度評估機器人，"
                    "請評估新聞標題是否與「民生用品的價格變化」相關，"
                    "並給予'high'、'medium'、'low'評價。"
                    "（僅需回答'high'、'medium'、'low'三個詞之一）"
                ),
            },
            {"role": "user", "content": title},
        ]

        try:
            completion = self.ai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
            )
            relevance_raw = completion.choices[0].message.content
            relevance_norm = relevance_raw.strip().lower()
            return relevance_norm == "high"
        except Exception as e:
            print(f"Error checking relevance with OpenAI: {e}")
            return False

    def _scrape_article_details(self, url: str) -> dict | None:
        """
        Given a UDN article URL, scrape:
        - title
        - time
        - content paragraphs (list[str])

        Returns dict on success, None on failure.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            title_el = soup.find("h1", class_="article-content__title")
            time_el = soup.find("time", class_="article-content__time")
            content_section = soup.find(
                "section", class_="article-content__editor"
            )

            # If structure changed and we can't find required nodes,
            # bail out gracefully
            if not title_el or not time_el or not content_section:
                print(f"Missing expected elements while scraping {url}")
                return None

            paragraphs = [
                p.get_text(strip=True)
                for p in content_section.find_all("p")
                if p.get_text(strip=True) != "" and "▪" not in p.get_text()
            ]

            return {
                "url": url,
                "title": title_el.get_text(strip=True),
                "time": time_el.get_text(strip=True),
                "content": paragraphs,
            }

        except (requests.RequestException, AttributeError) as e:
            print(f"Error scraping article {url}: {e}")
            return None

    def _summarize_article(self, content_blocks: list[str]) -> dict | None:
        """
        Ask the model to summarize:
        - 影響
        - 原因

        Expects pure valid JSON with keys "影響" and "原因".
        Returns {"summary": "...", "reason": "..."} or None.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一個新聞摘要生成機器人。"
                    "請統整新聞中提及的『影響』以及主要『原因』，"
                    "各約50個字。"
                    "請只輸出有效的 JSON（使用雙引號），格式必須是："
                    '{"影響": "...", "原因": "..."}'
                    "不要輸出任何多餘文字。"
                ),
            },
            {"role": "user", "content": " ".join(content_blocks)},
        ]

        try:
            completion = self.ai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
            )
            raw = completion.choices[0].message.content
            parsed = json.loads(raw)
            return {
                "summary": parsed["影響"],
                "reason": parsed["原因"],
            }
        except (json.JSONDecodeError, KeyError) as e:
            print(f"OpenAI JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"Error summarizing article with OpenAI: {e}")
            return None

    def process_news(self, is_initial: bool = False):
        """
        Fetches, filters, summarizes, and stores news articles
        about price changes in 民生用品.

        :param is_initial: If True, crawl multiple pages (broader fetch).
        """
        news_items = self._fetch_news_from_api("價格", is_initial)

        for item in news_items:
            # item should contain "title" and "titleLink" from UDN API
            title = item.get("title")
            url = item.get("titleLink")
            if not title or not url:
                continue

            # Step 1: filter by relevance
            if not self._check_relevance(title):
                continue

            # Step 2: scrape full article
            detailed_news = self._scrape_article_details(url)
            if not detailed_news:
                continue

            # Step 3: summarize with LLM
            summary_data = self._summarize_article(detailed_news["content"])
            if not summary_data:
                continue

            # Attach summary metadata required by DB insert
            detailed_news["summary"] = summary_data["summary"]
            detailed_news["reason"] = summary_data["reason"]

            # Step 4: persist
            self.news_repo.add_article(detailed_news)

            print(f"Added article: {detailed_news['title']}")
