import datetime
import uuid
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncAttrs
)
from sqlalchemy.orm import sessionmaker, Mapped
from sqlalchemy import (
    BigInteger,
    String,
    DateTime,
    Uuid,
    Integer,
    Boolean,
    ForeignKey,
    ARRAY,
    DATE
)
from sqlalchemy.orm import mapped_column, relationship, DeclarativeBase
from contextlib import asynccontextmanager
from config import Config

async_engine  = create_async_engine(Config.DATABASE_URI)
async_session = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id            = mapped_column(BigInteger, primary_key=True)
    is_premium    = mapped_column(Boolean, default=False)
    gender        = mapped_column(String(10))
    age           = mapped_column(Integer)
    country       = mapped_column(String(10))
    subscription  = relationship("Subscription", back_populates='user', uselist=False)
    preference: Mapped['Preference']  = relationship("Preference", back_populates='user', uselist=False)
    created_at    = mapped_column(DateTime, default=datetime.datetime.now())
    current_state = mapped_column(Integer, default=1)
    chatting_with = mapped_column(BigInteger, unique=True)
    last_partner_id = mapped_column(BigInteger)
    india_region  = mapped_column(String)
    chat_count    = mapped_column(Integer, default=0)
    chat_closed_date = mapped_column(DATE)
    report_count = mapped_column(Integer, default=0)
    release_date = mapped_column(DateTime)

    def __repr__(self):
        return f"User<{self.id}>"

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id            = mapped_column(Integer, primary_key=True)
    uuid          = mapped_column(Uuid(as_uuid=False), default=uuid.uuid4)
    type          = mapped_column(String(10), nullable=False)
    price_in_star = mapped_column(Integer)
    user_id       = mapped_column(BigInteger, ForeignKey('users.id'))
    user          = relationship("User", back_populates="subscription", uselist=False)
    end_date      = mapped_column(DateTime)
    created_at    = mapped_column(DateTime, default=datetime.datetime.now())



class Preference(Base):
    __tablename__ = "preferences"
    id            = mapped_column(Integer, primary_key=True)
    uuid          = mapped_column(Uuid(as_uuid=False), default=uuid.uuid4)
    gender        = mapped_column(String(10))
    user_id       = mapped_column(BigInteger, ForeignKey('users.id'), unique=True)
    user          = relationship("User", back_populates="preference")
    min_age       = mapped_column(Integer)
    max_age       = mapped_column(Integer)
    country       = mapped_column(ARRAY(String))
    india_region  = mapped_column(ARRAY(String))


@asynccontextmanager
async def get_session():
    async with async_session() as session:
        yield session
        