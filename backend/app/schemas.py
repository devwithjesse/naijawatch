from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

# ─── SOURCE SCHEMAS ─────────────────────────────────────────────────────────

class SourceBase(BaseModel):
    name: str
    type: str
    url: str

class SourceCreate(SourceBase):
    pass

class Source(SourceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ─── ARTICLE SCHEMAS ────────────────────────────────────────────────────────

class ArticleBase(BaseModel):
    title: str
    url: str
    content_hash: str
    published_at: Optional[datetime] = None

class ArticleCreate(ArticleBase):
    source_id: int
    body: Optional[str] = None

class Article(ArticleBase):
    id: int
    source_id: int
    body: Optional[str] = None
    processed: bool
    extraction_status: str
    created_at: datetime

    class Config:
        from_attributes = True

# ─── EVENT SCHEMAS ─────────────────────────────────────────────────────────

class EventTypeBase(BaseModel):
    name: str

class EventType(EventTypeBase):
    id: int
    class Config:
        from_attributes = True

class StateBase(BaseModel):
    name: str

class State(StateBase):
    id: int
    class Config:
        from_attributes = True

class LocationBase(BaseModel):
    state_id: int
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class Location(LocationBase):
    id: int
    state: State
    class Config:
        from_attributes = True

class EventStatisticsBase(BaseModel):
    killed: int = 0
    injured: int = 0
    abducted: int = 0

class EventStatistics(EventStatisticsBase):
    id: int
    event_id: int
    class Config:
        from_attributes = True

class EventBase(BaseModel):
    event_type_id: int
    location_id: int
    event_date: Optional[date] = None
    confidence: float = 0.0
    summary: Optional[str] = None

class EventCreate(EventBase):
    pass

class Event(EventBase):
    id: int
    created_at: datetime
    event_type: EventType
    location: Location
    statistics: Optional[EventStatistics] = None

    class Config:
        from_attributes = True

# ─── STATS SCHEMAS ─────────────────────────────────────────────────────────

class StateRiskRanking(BaseModel):
    state: str
    incidents: int
    fatalities: int
    abductions: int
    risk_index: float
    risk_tier: str

    class Config:
        from_attributes = True

class TravelRequest(BaseModel):
    origin: str
    destination: str

class SubscribeRequest(BaseModel):
    email: str
