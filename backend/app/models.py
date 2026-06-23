from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # rss | api
    url = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    articles = relationship("Article", back_populates="source")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    url = Column(Text, nullable=False)
    content_hash = Column(String(64), unique=True, index=True, nullable=False)
    published_at = Column(DateTime, nullable=True)
    processed = Column(Boolean, default=False)
    extraction_status = Column(
        String(20), default="pending"
    )  # pending, success, failed, irrelevant
    created_at = Column(DateTime, server_default=func.now())

    source = relationship("Source", back_populates="articles")
    events = relationship("Event", secondary="event_sources", back_populates="articles")


class EventType(Base):
    __tablename__ = "event_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    events = relationship("Event", back_populates="event_type")


class State(Base):
    __tablename__ = "states"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    locations = relationship("Location", back_populates="state")


class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=False)
    name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    state = relationship("State", back_populates="locations")
    events = relationship("Event", back_populates="location")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    event_type_id = Column(Integer, ForeignKey("event_types.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    event_date = Column(Date, nullable=True)
    confidence = Column(Float, default=0.0)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    event_type = relationship("EventType", back_populates="events")
    location = relationship("Location", back_populates="events")
    statistics = relationship("EventStatistics", back_populates="event", uselist=False)
    articles = relationship(
        "Article", secondary="event_sources", back_populates="events"
    )


class EventStatistics(Base):
    __tablename__ = "event_statistics"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), unique=True, nullable=False)
    killed = Column(Integer, default=0)
    injured = Column(Integer, default=0)
    abducted = Column(Integer, default=0)

    event = relationship("Event", back_populates="statistics")


class EventSource(Base):
    __tablename__ = "event_sources"
    event_id = Column(Integer, ForeignKey("events.id"), primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), primary_key=True)


class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(String(20), nullable=False)  # "national" | "state"
    state_id = Column(Integer, ForeignKey("states.id"), nullable=True)
    score = Column(Float, nullable=False)
    components = Column(Text, nullable=True)  # JSON blob
    snapshot_at = Column(DateTime, server_default=func.now())


class DigestSubscriber(Base):
    __tablename__ = "digest_subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    confirmation_token = Column(String(64), nullable=False)
    unsubscribe_token = Column(String(64), nullable=False)
    confirmed = Column(Boolean, default=False)
    subscribed_at = Column(DateTime, server_default=func.now())
    confirmed_at = Column(DateTime, nullable=True)
