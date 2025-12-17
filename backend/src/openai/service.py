import json

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam


class OpenAIService:
    def __init__(self, openai_api_key: str):
        self.ai_client = OpenAI(api_key=openai_api_key)

    def extract_keywords(self, prompt: str) -> str | None:
        """Extract keywords from user prompt using OpenAI."""
        messages: list[ChatCompletionMessageParam] = [
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

    def check_relevance(self, title: str) -> bool:
        messages: list[ChatCompletionMessageParam] = [
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
            if relevance_raw is None:
                raise ValueError("Empty response from OpenAI")
            relevance_norm = relevance_raw.strip().lower()
            return relevance_norm == "high"
        except Exception as e:
            print(f"Error checking relevance with OpenAI: {e}")
            return False

    def summarize_article(self, content_blocks: list[str]) -> dict | None:
        messages: list[ChatCompletionMessageParam] = [
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
            if raw is None:
                raise ValueError("Empty response from OpenAI")
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
