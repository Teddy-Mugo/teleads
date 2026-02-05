import uuid
from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    BigInteger,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


# -------------------------------------------------------------------
# Users (Admins / Operators)
# -------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'operator')"),
    )


# -------------------------------------------------------------------
# Customers
# -------------------------------------------------------------------

class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    campaigns = relationship("Campaign", back_populates="customer")
    telegram_accounts = relationship("TelegramAccount", back_populates="owner")


# -------------------------------------------------------------------
# Telegram Accounts (User Accounts)
# -------------------------------------------------------------------

class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    phone_number = Column(String, unique=True, nullable=False)
    session_name = Column(String, unique=True, nullable=False)

    api_id = Column(Integer, nullable=False)
    api_hash = Column(String, nullable=False)

    account_type = Column(String, nullable=False)
    owner_customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
    )

    status = Column(String, default="warming")
    daily_message_limit = Column(Integer, default=40)

    last_used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    owner = relationship("Customer", back_populates="telegram_accounts")
    campaigns = relationship(
        "CampaignAccount",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("account_type IN ('shared', 'dedicated')"),
        CheckConstraint(
            "status IN ('warming', 'active', 'paused', 'restricted', 'banned')"
        ),
        Index("idx_telegram_accounts_status", "status"),
    )


# -------------------------------------------------------------------
# Telegram Groups / Channels
# -------------------------------------------------------------------

class TelegramGroup(Base):
    __tablename__ = "telegram_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    telegram_id = Column(BigInteger)
    username = Column(String, unique=True)
    title = Column(String)

    group_type = Column(String)
    allow_ads = Column(Boolean, default=True)
    cooldown_minutes = Column(Integer, default=1440)

    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    campaigns = relationship(
        "CampaignGroup",
        back_populates="group",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "group_type IN ('group', 'supergroup', 'channel')"
        ),
    )


# -------------------------------------------------------------------
# Campaigns
# -------------------------------------------------------------------

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String, nullable=False)
    campaign_type = Column(String, nullable=False)
    message_template = Column(Text, nullable=False)

    interval_minutes = Column(Integer, nullable=False)
    start_at = Column(DateTime(timezone=True))
    end_at = Column(DateTime(timezone=True))

    status = Column(String, default="draft")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    customer = relationship("Customer", back_populates="campaigns")
    groups = relationship(
        "CampaignGroup",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    accounts = relationship(
        "CampaignAccount",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    message_logs = relationship("MessageLog", back_populates="campaign")

    __table_args__ = (
        CheckConstraint("campaign_type IN ('shared', 'dedicated')"),
        CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'completed')"
        ),
        Index("idx_campaigns_status", "status"),
    )


# -------------------------------------------------------------------
# Campaign ↔ Groups (M2M)
# -------------------------------------------------------------------

class CampaignGroup(Base):
    __tablename__ = "campaign_groups"

    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        primary_key=True,
    )
    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_groups.id", ondelete="CASCADE"),
        primary_key=True,
    )

    campaign = relationship("Campaign", back_populates="groups")
    group = relationship("TelegramGroup", back_populates="campaigns")


# -------------------------------------------------------------------
# Campaign ↔ Accounts (M2M)
# -------------------------------------------------------------------

class CampaignAccount(Base):
    __tablename__ = "campaign_accounts"

    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        primary_key=True,
    )
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    campaign = relationship("Campaign", back_populates="accounts")
    account = relationship("TelegramAccount", back_populates="campaigns")


# -------------------------------------------------------------------
# Message Logs
# -------------------------------------------------------------------

class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
    )
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_accounts.id", ondelete="SET NULL"),
    )
    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_groups.id", ondelete="SET NULL"),
    )

    target = Column(String, nullable=False)
    message_text = Column(Text)

    status = Column(String, nullable=False)
    error_code = Column(String)
    flood_wait_seconds = Column(Integer)

    sent_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="message_logs")

    __table_args__ = (
        CheckConstraint("status IN ('sent', 'failed', 'skipped')"),
        Index("idx_message_logs_account_id", "account_id"),
        Index("idx_message_logs_campaign_id", "campaign_id"),
    )


# -------------------------------------------------------------------
# Account Health Events
# -------------------------------------------------------------------

class AccountHealthEvent(Base):
    __tablename__ = "account_health_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_type = Column(String, nullable=False)
    details = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('floodwait', 'write_forbidden', 'paused', 'banned')"
        ),
    )


#account limits

class TelegramAccountDailyUsage(Base):
    __tablename__ = "telegram_account_daily_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    telegram_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )

    usage_date = Column(Date, nullable=False)
    messages_sent = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint("telegram_account_id", "usage_date"),
    )



# daily counters 

class DailyCounter(Base):
    __tablename__ = "daily_counters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    count = Column(Integer, default=0)
    date = Column(Date, default=date.today)

    account = relationship("TelegramAccount", back_populates="counter")

    def reset_if_needed(self):
        today = date.today()
        if self.date != today:
            self.date = today
            self.count = 0


# subscription plans

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, unique=True)

    max_accounts = Column(Integer)
    min_interval_seconds = Column(Integer)

    daily_account_limit = Column(Integer)
    group_cooldown_minutes = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
