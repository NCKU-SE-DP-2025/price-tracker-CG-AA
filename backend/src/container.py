from .config import settings
from .crawler.udn_crawler import UDNCrawler
from .openai.service import OpenAIService

udn_crawler = UDNCrawler()
openai_service = OpenAIService(settings.OPENAI_API_KEY)


def get_udn_crawler() -> UDNCrawler:
    return udn_crawler


def get_openai_service() -> OpenAIService:
    return openai_service
