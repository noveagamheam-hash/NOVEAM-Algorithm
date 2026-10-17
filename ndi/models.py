from typing import Literal
from pydantic import BaseModel, Field

Mode = Literal['personalized', 'chronological', 'following', 'discovery']

class Post(BaseModel):
    id: str
    author_id: str
    created_at: float = Field(ge=0)
    interest: float = Field(ge=0, le=1)
    relationship: float = Field(ge=0, le=1)
    quality: float = Field(ge=0, le=1)
    diversity: float = Field(ge=0, le=1)
    followed: bool = False
    visible: bool = True

class RankRequest(BaseModel):
    posts: list[Post] = Field(max_length=200)
    mode: Mode = 'personalized'
    now: float = Field(ge=0)

class RankedPost(BaseModel):
    id: str
    score: float

class RankResponse(BaseModel):
    algorithm: str
    version: str
    results: list[RankedPost]
