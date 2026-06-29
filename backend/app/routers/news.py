from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Article

router = APIRouter()


@router.get("/feed", response_model=List[schemas.Article], status_code=200)
def get_news_feed(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
):
    """
    Description: Paginated, filtered security news feed.
    Details: Returns the raw news feed from the articles table. It automatically filters out articles
    deemed "irrelevant" by the LLM extraction engine and supports skip and limit parameters for
    pagination.
    """
    articles = (
        db.query(Article)
        .filter(Article.extraction_status != "irrelevant")
        .filter(Article.body != None)
        .order_by(Article.published_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return articles
