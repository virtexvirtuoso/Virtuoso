import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, Index,
    BigInteger, Enum, ForeignKey, create_engine, select
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import and_, or_, desc, asc, func
import uuid
import json

from src.core.models.liquidation import LiquidationEvent, LiquidationType, LiquidationSeverity

Base = declarative_base()

class LiquidationEventDB(Base):
    """Database model for liquidation events."""
    __tablename__ = 'liquidation_events'
    
    # Primary key and identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Basic event info
    symbol = Column(String(50), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Liquidation details
    liquidation_type = Column(Enum(LiquidationType), nullable=False)
    severity = Column(Enum(LiquidationSeverity), nullable=False, index=True)
    confidence_score = Column(Float, nullable=False)
    
    # Price and volume metrics
    trigger_price = Column(Float, nullable=False)
    price_impact = Column(Float, default=0.0)
    volume_spike_ratio = Column(Float, default=1.0)
    liquidated_amount_usd = Column(Float, nullable=False, index=True)
    
    # Market microstructure
    bid_ask_spread_pct = Column(Float, default=0.0)
    order_book_imbalance = Column(Float, default=0.0)
    market_depth_impact = Column(Float, default=0.0)
    volatility_spike = Column(Float, default=1.0)

    # Optional technical indicators
    rsi = Column(Float, nullable=True)
    volume_weighted_price = Column(Float, nullable=True)
    funding_rate = Column(Float, nullable=True)
    open_interest_change = Column(Float, nullable=True)
    recovery_time_seconds = Column(Integer, nullable=True)

    # Duration and triggers
    duration_seconds = Column(Integer, default=0)
    suspected_triggers = Column(JSONB, default=list)  # PostgreSQL JSONB for better performance
    market_conditions = Column(JSONB, default=dict)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_symbol_exchange_timestamp', 'symbol', 'exchange', 'timestamp'),
        Index('idx_severity_timestamp', 'severity', 'timestamp'),
        Index('idx_liquidated_amount_timestamp', 'liquidated_amount_usd', 'timestamp'),
        Index('idx_exchange_timestamp', 'exchange', 'timestamp'),
    )

class LiquidationAggregatesDB(Base):
    """Database model for aggregated liquidation data."""
    __tablename__ = 'liquidation_aggregates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Aggregation dimensions
    symbol = Column(String(50), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)
    time_bucket = Column(DateTime, nullable=False, index=True)  # 1min, 5min, 1hour buckets
    bucket_size = Column(String(10), nullable=False)  # '1m', '5m', '1h', '1d'
    
    # Aggregate metrics
    total_liquidations = Column(Integer, default=0)
    total_volume_usd = Column(Float, default=0.0)
    long_liquidations = Column(Integer, default=0)
    short_liquidations = Column(Integer, default=0)
    cascade_events = Column(Integer, default=0)
    
    # Severity breakdown
    critical_liquidations = Column(Integer, default=0)
    high_liquidations = Column(Integer, default=0)
    medium_liquidations = Column(Integer, default=0)
    low_liquidations = Column(Integer, default=0)
    
    # Price impact metrics
    max_price_impact = Column(Float, default=0.0)
    avg_price_impact = Column(Float, default=0.0)
    max_volume_spike = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_symbol_bucket_time', 'symbol', 'bucket_size', 'time_bucket'),
        Index('idx_exchange_bucket_time', 'exchange', 'bucket_size', 'time_bucket'),
    )

class LiquidationStorage:
    """Comprehensive storage layer for liquidation data."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.logger = logging.getLogger(__name__)
        
        # Create async engine
        if database_url.startswith('postgresql'):
            # Use asyncpg for PostgreSQL
            async_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
        else:
            # Use aiosqlite for SQLite
            async_url = database_url.replace('sqlite://', 'sqlite+aiosqlite://')
        
        self.async_engine = create_async_engine(async_url, echo=False)
        self.AsyncSessionLocal = sessionmaker(
            self.async_engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def create_tables(self):
        """Create database tables if they don't exist."""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self.logger.info("Database tables created successfully")
        except Exception as e:
            self.logger.error(f"Error creating database tables: {e}")
            raise
    
    async def store_liquidation_event(self, liquidation_event: LiquidationEvent) -> bool:
        """Store a single liquidation event."""
        try:
            async with self.AsyncSessionLocal() as session:
                # Check if event already exists (query by event_id, not primary key UUID)
                result = await session.execute(
                    select(LiquidationEventDB).where(LiquidationEventDB.event_id == liquidation_event.event_id)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    self.logger.debug(f"Liquidation event {liquidation_event.event_id} already exists")
                    return False
                
                # Create new event
                db_event = LiquidationEventDB(
                    event_id=liquidation_event.event_id,
                    symbol=liquidation_event.symbol,
                    exchange=liquidation_event.exchange,
                    timestamp=liquidation_event.timestamp,
                    liquidation_type=liquidation_event.liquidation_type,
                    severity=liquidation_event.severity,
                    confidence_score=liquidation_event.confidence_score,
                    trigger_price=liquidation_event.trigger_price,
                    price_impact=liquidation_event.price_impact,
                    volume_spike_ratio=liquidation_event.volume_spike_ratio,
                    liquidated_amount_usd=liquidation_event.liquidated_amount_usd,
                    bid_ask_spread_pct=liquidation_event.bid_ask_spread_pct,
                    order_book_imbalance=liquidation_event.order_book_imbalance,
                    market_depth_impact=liquidation_event.market_depth_impact,
                    volatility_spike=liquidation_event.volatility_spike,
                    duration_seconds=liquidation_event.duration_seconds,
                    suspected_triggers=liquidation_event.suspected_triggers,
                    market_conditions=liquidation_event.market_conditions,
                    # Optional fields
                    rsi=liquidation_event.rsi,
                    volume_weighted_price=liquidation_event.volume_weighted_price,
                    funding_rate=liquidation_event.funding_rate,
                    open_interest_change=liquidation_event.open_interest_change,
                    recovery_time_seconds=liquidation_event.recovery_time_seconds
                )
                
                session.add(db_event)
                await session.commit()
                
                self.logger.debug(f"Stored liquidation event: {liquidation_event.event_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing liquidation event: {e}")
            return False
    
    async def store_liquidation_events_batch(self, liquidation_events: List[LiquidationEvent]) -> int:
        """Store multiple liquidation events in a batch."""
        stored_count = 0
        
        try:
            async with self.AsyncSessionLocal() as session:
                for event in liquidation_events:
                    # Check if event already exists
                    result = await session.execute(
                        f"SELECT event_id FROM liquidation_events WHERE event_id = '{event.event_id}'"
                    )
                    if result.fetchone():
                        continue
                    
                    db_event = LiquidationEventDB(
                        event_id=event.event_id,
                        symbol=event.symbol,
                        exchange=event.exchange,
                        timestamp=event.timestamp,
                        liquidation_type=event.liquidation_type,
                        severity=event.severity,
                        confidence_score=event.confidence_score,
                        trigger_price=event.trigger_price,
                        price_impact=event.price_impact,
                        volume_spike_ratio=event.volume_spike_ratio,
                        liquidated_amount_usd=event.liquidated_amount_usd,
                        bid_ask_spread_pct=event.bid_ask_spread_pct,
                        order_book_imbalance=event.order_book_imbalance,
                        market_depth_impact=event.market_depth_impact,
                        volatility_spike=event.volatility_spike,
                        duration_seconds=event.duration_seconds,
                        suspected_triggers=event.suspected_triggers,
                        market_conditions=event.market_conditions,
                        # Optional fields
                        rsi=event.rsi,
                        volume_weighted_price=event.volume_weighted_price,
                        funding_rate=event.funding_rate,
                        open_interest_change=event.open_interest_change,
                        recovery_time_seconds=event.recovery_time_seconds
                    )
                    
                    session.add(db_event)
                    stored_count += 1
                
                await session.commit()
                self.logger.info(f"Stored {stored_count} liquidation events in batch")
                
        except Exception as e:
            self.logger.error(f"Error storing liquidation events batch: {e}")
        
        return stored_count
    
    async def get_liquidation_events(
        self,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[LiquidationSeverity] = None,
        min_amount_usd: Optional[float] = None,
        limit: int = 1000
    ) -> List[LiquidationEvent]:
        """Get liquidation events with filters."""
        
        try:
            async with self.AsyncSessionLocal() as session:
                query = session.query(LiquidationEventDB)
                
                # Apply filters
                if symbol:
                    query = query.filter(LiquidationEventDB.symbol == symbol)
                if exchange:
                    query = query.filter(LiquidationEventDB.exchange == exchange)
                if start_time:
                    query = query.filter(LiquidationEventDB.timestamp >= start_time)
                if end_time:
                    query = query.filter(LiquidationEventDB.timestamp <= end_time)
                if severity:
                    query = query.filter(LiquidationEventDB.severity == severity)
                if min_amount_usd:
                    query = query.filter(LiquidationEventDB.liquidated_amount_usd >= min_amount_usd)
                
                # Order by timestamp descending and limit
                query = query.order_by(desc(LiquidationEventDB.timestamp)).limit(limit)
                
                # Execute query
                result = await session.execute(query)
                db_events = result.scalars().all()
                
                # Convert to Pydantic models
                events = []
                for db_event in db_events:
                    event = LiquidationEvent(
                        event_id=db_event.event_id,
                        symbol=db_event.symbol,
                        exchange=db_event.exchange,
                        timestamp=db_event.timestamp,
                        liquidation_type=db_event.liquidation_type,
                        severity=db_event.severity,
                        confidence_score=db_event.confidence_score,
                        trigger_price=db_event.trigger_price,
                        price_impact=db_event.price_impact,
                        volume_spike_ratio=db_event.volume_spike_ratio,
                        liquidated_amount_usd=db_event.liquidated_amount_usd,
                        bid_ask_spread_pct=db_event.bid_ask_spread_pct,
                        order_book_imbalance=db_event.order_book_imbalance,
                        market_depth_impact=db_event.market_depth_impact,
                        volatility_spike=db_event.volatility_spike,
                        duration_seconds=db_event.duration_seconds,
                        suspected_triggers=db_event.suspected_triggers,
                        market_conditions=db_event.market_conditions,
                        # Optional fields
                        rsi=db_event.rsi,
                        volume_weighted_price=db_event.volume_weighted_price,
                        funding_rate=db_event.funding_rate,
                        open_interest_change=db_event.open_interest_change,
                        recovery_time_seconds=db_event.recovery_time_seconds
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            self.logger.error(f"Error getting liquidation events: {e}")
            return []
    
    async def get_liquidation_statistics(
        self,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get liquidation statistics for the specified time period."""
        
        try:
            start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            async with self.AsyncSessionLocal() as session:
                query = session.query(LiquidationEventDB).filter(
                    LiquidationEventDB.timestamp >= start_time
                )
                
                if symbol:
                    query = query.filter(LiquidationEventDB.symbol == symbol)
                if exchange:
                    query = query.filter(LiquidationEventDB.exchange == exchange)
                
                result = await session.execute(query)
                events = result.scalars().all()
                
                if not events:
                    return {
                        'total_liquidations': 0,
                        'total_volume_usd': 0.0,
                        'long_liquidations': 0,
                        'short_liquidations': 0,
                        'severity_breakdown': {
                            'critical': 0, 'high': 0, 'medium': 0, 'low': 0
                        }
                    }
                
                # Calculate statistics
                total_liquidations = len(events)
                total_volume_usd = sum(e.liquidated_amount_usd for e in events)
                
                long_liquidations = sum(1 for e in events 
                                      if e.liquidation_type == LiquidationType.LONG_LIQUIDATION)
                short_liquidations = sum(1 for e in events 
                                       if e.liquidation_type == LiquidationType.SHORT_LIQUIDATION)
                
                severity_breakdown = {
                    'critical': sum(1 for e in events if e.severity == LiquidationSeverity.CRITICAL),
                    'high': sum(1 for e in events if e.severity == LiquidationSeverity.HIGH),
                    'medium': sum(1 for e in events if e.severity == LiquidationSeverity.MEDIUM),
                    'low': sum(1 for e in events if e.severity == LiquidationSeverity.LOW)
                }
                
                return {
                    'total_liquidations': total_liquidations,
                    'total_volume_usd': total_volume_usd,
                    'long_liquidations': long_liquidations,
                    'short_liquidations': short_liquidations,
                    'severity_breakdown': severity_breakdown,
                    'time_period_hours': hours
                }
                
        except Exception as e:
            self.logger.error(f"Error getting liquidation statistics: {e}")
            return {}
    
    async def cleanup_old_events(self, days_to_keep: int = 30) -> int:
        """Clean up old liquidation events to manage database size."""
        
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            async with self.AsyncSessionLocal() as session:
                result = await session.execute(
                    f"DELETE FROM liquidation_events WHERE timestamp < '{cutoff_date}'"
                )
                deleted_count = result.rowcount
                await session.commit()
                
                self.logger.info(f"Cleaned up {deleted_count} old liquidation events")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old events: {e}")
            return 0 