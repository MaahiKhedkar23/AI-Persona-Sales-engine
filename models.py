"""
models.py — SQLAlchemy ORM models for SalesAI Platform
All database tables defined here using Flask-SQLAlchemy style.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    Float, DateTime, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

# ── DATABASE SETUP ────────────────────────────────────────
DATABASE_URL = "sqlite:///salesai.db"
engine       = create_engine(DATABASE_URL, echo=False)
Session      = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass


# ── TABLE 1: CAMPAIGNS ────────────────────────────────────
class Campaign(Base):
    __tablename__ = "campaigns"

    id                = Column(Integer, primary_key=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=True)
    product_name      = Column(String(200), nullable=False)
    category          = Column(String(50),  nullable=False)
    persona           = Column(String(100), nullable=False)
    behavior          = Column(String(100), nullable=False)
    status            = Column(String(30),  default="active")
    execution_status  = Column(String(30),  default="draft")
    created_at        = Column(DateTime,    default=datetime.utcnow)

    # Relationships
    stages          = relationship("StrategyStage",   back_populates="campaign", cascade="all, delete")
    posts           = relationship("GeneratedPost",   back_populates="campaign", cascade="all, delete")
    analytics       = relationship("Analytics",       back_populates="campaign", uselist=False, cascade="all, delete")
    recommendations = relationship("Recommendation",  back_populates="campaign", cascade="all, delete")

    def to_dict(self):
        return {
            "id":               self.id,
            "user_id":          self.user_id,
            "product_name":     self.product_name,
            "category":         self.category,
            "persona":          self.persona,
            "behavior":         self.behavior,
            "status":           self.status,
            "execution_status": self.execution_status,
            "created_at":       self.created_at.strftime("%d %b %Y, %H:%M"),
        }


# ── TABLE 2: STRATEGY STAGES ──────────────────────────────
class StrategyStage(Base):
    __tablename__ = "strategy_stages"

    id                  = Column(Integer, primary_key=True)
    campaign_id         = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    stage_name          = Column(String(50),  nullable=False)   # Awareness, Interest…
    goal                = Column(Text,        nullable=True)
    insight             = Column(Text,        nullable=True)
    tactics             = Column(Text,        nullable=True)     # JSON string
    implementation_tips = Column(Text,        nullable=True)     # JSON string
    kpis                = Column(Text,        nullable=True)     # JSON string
    stage_order         = Column(Integer,     default=0)

    campaign = relationship("Campaign", back_populates="stages")


# ── TABLE 3: GENERATED POSTS / CONTENT ───────────────────
class GeneratedPost(Base):
    __tablename__ = "generated_posts"

    id           = Column(Integer, primary_key=True)
    campaign_id  = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    stage_name   = Column(String(50),  nullable=False)
    content_type = Column(String(50),  nullable=False)  # sales_message / email / marketing_text
    subject      = Column(Text,        nullable=True)   # for emails
    content      = Column(Text,        nullable=False)

    campaign = relationship("Campaign", back_populates="posts")


# ── TABLE 4: ANALYTICS ────────────────────────────────────
class Analytics(Base):
    __tablename__ = "analytics"

    id               = Column(Integer, primary_key=True)
    campaign_id      = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    reach            = Column(Integer, default=0)
    engagement       = Column(Float,   default=0.0)   # percentage
    clicks           = Column(Integer, default=0)
    conversion_score = Column(Float,   default=0.0)   # 0-100
    progress         = Column(Float,   default=0.0)   # 0-100
    tactic_data      = Column(Text,    nullable=True)  # JSON: per-tactic performance
    updated_at       = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="analytics")


# ── TABLE 5: AI RECOMMENDATIONS ──────────────────────────
class Recommendation(Base):
    __tablename__ = "recommendations"

    id                  = Column(Integer, primary_key=True)
    campaign_id         = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    recommendation_text = Column(Text,   nullable=False)
    priority            = Column(String(20), default="medium")  # high / medium / low
    created_at          = Column(DateTime,   default=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="recommendations")


# ── TABLE 8: USERS (authentication) ─────────────────────
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True)
    username      = Column(String(80),  nullable=False, unique=True)
    email         = Column(String(120), nullable=False, unique=True)
    password_hash = Column(String(256), nullable=True)   # nullable for OAuth users
    oauth_provider= Column(String(30),  nullable=True)   # google / github / None
    oauth_id      = Column(String(120), nullable=True)   # provider user id
    avatar_url    = Column(String(300), nullable=True)   # profile picture
    created_at    = Column(DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id":       self.id,
            "username": self.username,
            "email":    self.email,
        }


# ── CREATE ALL TABLES ─────────────────────────────────────
def init_db():
    Base.metadata.create_all(engine)
    print("✅ Database tables created.")


# ── TABLE 6: TRACKING EVENTS (real clicks) ───────────────
class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id           = Column(Integer, primary_key=True)
    campaign_id  = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    event_type   = Column(String(30),  nullable=False)   # click / view / open
    stage        = Column(String(50),  nullable=True)    # Awareness / Interest…
    channel      = Column(String(80),  nullable=True)    # instagram / email…
    link_token   = Column(String(20),  nullable=True)    # short token for URL
    ip_hash      = Column(String(64),  nullable=True)    # hashed for privacy
    user_agent   = Column(String(200), nullable=True)
    referrer     = Column(String(200), nullable=True)
    created_at   = Column(DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":          self.id,
            "campaign_id": self.campaign_id,
            "event_type":  self.event_type,
            "stage":       self.stage,
            "channel":     self.channel,
            "created_at":  self.created_at.strftime("%d %b %Y, %H:%M"),
        }


# ── TABLE 7: TRACKABLE LINKS ─────────────────────────────
class TrackableLink(Base):
    __tablename__ = "trackable_links"

    id          = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    token       = Column(String(20),  nullable=False, unique=True)
    stage       = Column(String(50),  nullable=True)
    channel     = Column(String(80),  nullable=True)
    label       = Column(String(200), nullable=True)
    destination = Column(Text,        nullable=True)   # optional redirect URL
    clicks      = Column(Integer,     default=0)
    created_at  = Column(DateTime,    default=datetime.utcnow)
