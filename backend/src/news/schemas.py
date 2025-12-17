from pydantic import BaseModel


class PromptRequest(BaseModel):
    prompt: str


class NewsSummaryRequestSchema(BaseModel):
    content: str


class NewsSearchResultSchema(BaseModel):
    """Schema for news search results returned by the search_news endpoint."""

    url: str
    title: str
    time: str
    content: str
