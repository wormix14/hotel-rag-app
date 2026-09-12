from pydantic import BaseModel

class RAGSearchResult(BaseModel):
    contexts: list[str]   