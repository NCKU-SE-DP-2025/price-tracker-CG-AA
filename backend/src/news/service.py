import json
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from openai import OpenAI

from ..database import NewsArticleRepository


class NewsProcessor:
    def __init__(self, db_session: Session, openai_api_key: str):
        self.news_repo = NewsArticleRepository(db_session)
        self.ai_client = OpenAI(api_key=openai_api_key)
        self.udn_api_url = "https://udn.com/api/more"

    def _fetch_news_from_api(
        self, search_term: str, is_initial: bool = False
    ) -> list[dict]:
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

    def _extract_keywords(self, prompt: str) -> str | None:
        """Extract keywords from user prompt using OpenAI."""
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一個關鍵字提取機器人，用戶將會輸入一段文字，"
                    "表示其希望看見的新聞內容，請提取出用戶希望看見的關鍵字，"
                    "請截取最重要的關鍵字即可，避免出現「新聞」、「資訊」等混淆搜尋引擎的字詞。"
                    "(僅須回答關鍵字，若有多個關鍵字，請以空格分隔)"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            completion = self.ai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
            )
            keywords = completion.choices[0].message.content
            return keywords.strip() if keywords else None
        except Exception as e:
            print(f"Error extracting keywords with OpenAI: {e}")
            return None

    def _check_relevance(self, title: str) -> bool:
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
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            title_el = soup.find("h1", class_="article-content__title")
            time_el = soup.find("time", class_="article-content__time")
            content_section = soup.find(
                "section", class_="article-content__editor"
            )

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
        news_items = self._fetch_news_from_api("價格", is_initial)

        for item in news_items:
            title = item.get("title")
            url = item.get("titleLink")
            if not title or not url:
                continue

            if not self._check_relevance(title):
                continue

            detailed_news = self._scrape_article_details(url)
            if not detailed_news:
                continue

            summary_data = self._summarize_article(detailed_news["content"])
            if not summary_data:
                continue

            detailed_news["summary"] = summary_data["summary"]
            detailed_news["reason"] = summary_data["reason"]

            self.news_repo.add_article(detailed_news)

            print(f"Added article: {detailed_news['title']}")

    def search_news_by_prompt(self, prompt: str) -> list[dict]:
        """
        Search for news articles based on a user prompt.

        1. Extract keywords from the prompt using AI
        2. Fetch news articles using those keywords
        3. Scrape detailed content from each article
        4. Return sorted results by time
        """
        # Step 1: Extract keywords from prompt
        keywords = self._extract_keywords(prompt)
        if not keywords:
            print(f"Failed to extract keywords from prompt: {prompt}")
            return []

        print(f"Extracted keywords: {keywords}")

        # Step 2: Fetch news items using the extracted keywords
        news_items = self._fetch_news_from_api(keywords, is_initial=False)
        if not news_items:
            print("No news items found")
            return []

        # Step 3: Scrape detailed content from each article
        news_list = []
        for item in news_items:
            url = item.get("titleLink")
            if not url:
                continue

            try:
                detailed_news = self._scrape_article_details(url)
                if not detailed_news:
                    continue

                # Join content paragraphs into a single string
                detailed_news["content"] = " ".join(
                    detailed_news.get("content", [])
                )
                news_list.append(detailed_news)
            except Exception as e:
                print(
                    f"Error processing article {url} [{type(e).__name__}]: {e}"
                )
                continue

        # Step 4: Sort by time (newest first) and return
        return sorted(news_list, key=lambda x: x.get("time", ""), reverse=True)
