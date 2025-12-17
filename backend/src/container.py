import os

from .crawler.udn_crawler import UDNCrawler
from .openai.service import OpenAIService

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "xxx")

udn_crawler = UDNCrawler()
openai_service = OpenAIService(OPENAI_API_KEY)


def get_udn_crawler() -> UDNCrawler:
    return udn_crawler


def get_openai_service() -> OpenAIService:
    return openai_service
