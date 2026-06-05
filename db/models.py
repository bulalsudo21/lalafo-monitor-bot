from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass

class SearchQuery(Base):
    __tablename__ = "search_queries"
    id = Column(Integer, primary_key=True)
    keyword = Column(String, unique=True, nullable=False, index=True)
    last_checked = Column(DateTime, nullable=True)
    users = relationship("User", back_populates="query", lazy="selectin")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    max_price = Column(Float, nullable=False)
    query_id = Column(Integer, ForeignKey("search_queries.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    query = relationship("SearchQuery", back_populates="users", lazy="selectin")

class SeenAd(Base):
    __tablename__ = "seen_ads"
    id = Column(Integer, primary_key=True)
    ad_url = Column(String, unique=True, nullable=False, index=True)
    query_id = Column(Integer, ForeignKey("search_queries.id"), nullable=False, index=True)
    sent_at = Column(DateTime, server_default=func.now())
