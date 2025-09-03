#!/usr/bin/env python3
"""
Distributed Session Management using Memcached
Provides persistent sessions across restarts and multiple processes
"""

import time
import uuid
import json
import hashlib
import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pymemcache.client.base import Client
from pymemcache import serde
import logging
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class SessionStatus(Enum):
    """Session status states"""
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    SUSPENDED = "suspended"

@dataclass
class Session:
    """Session data structure"""
    session_id: str
    user_id: Optional[str]
    created_at: float
    last_accessed: float
    expires_at: float
    status: SessionStatus
    data: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'expires_at': self.expires_at,
            'status': self.status.value,
            'data': self.data,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create session from dictionary"""
        return cls(
            session_id=data['session_id'],
            user_id=data.get('user_id'),
            created_at=data['created_at'],
            last_accessed=data['last_accessed'],
            expires_at=data['expires_at'],
            status=SessionStatus(data['status']),
            data=data.get('data', {}),
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent')
        )

class MemcachedSessionStore:
    """
    Distributed session store using Memcached
    Provides persistent sessions across restarts and processes
    """
    
    # Default session configuration
    DEFAULT_TTL = 3600  # 1 hour
    MAX_TTL = 86400     # 24 hours
    CLEANUP_INTERVAL = 300  # 5 minutes
    
    def __init__(self, 
                 host: str = '127.0.0.1', 
                 port: int = 11211,
                 default_ttl: int = None,
                 secure: bool = True):
        """
        Initialize session store
        
        Args:
            host: Memcached host
            port: Memcached port
            default_ttl: Default session TTL in seconds
            secure: Use secure session IDs
        """
        self.default_ttl = default_ttl or self.DEFAULT_TTL
        self.secure = secure
        
        try:
            self.mc = Client(
                (host, port),
                serializer=serde.python_memcache_serializer,
                deserializer=serde.python_memcache_deserializer,
                connect_timeout=1,
                timeout=0.5
            )
            # Test connection
            self.mc.set(b'session:test', b'1', expire=1)
            self.available = True
            logger.info(f"Session store connected to Memcached at {host}:{port}")
        except Exception as e:
            logger.warning(f"Memcached not available for sessions: {e}")
            self.available = False
            self.mc = None
        
        # Always initialize local sessions for fallback
        self.local_sessions = {}
        
        # Metrics
        self.metrics = {
            'created': 0,
            'retrieved': 0,
            'updated': 0,
            'destroyed': 0,
            'expired': 0,
            'active_sessions': 0
        }
        
        # Last cleanup time
        self.last_cleanup = time.time()
    
    def create_session(self, 
                       user_id: Optional[str] = None,
                       data: Optional[Dict[str, Any]] = None,
                       ttl: Optional[int] = None,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None) -> Session:
        """
        Create a new session
        
        Args:
            user_id: Optional user identifier
            data: Optional session data
            ttl: Session TTL in seconds
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created session object
        """
        # Generate secure session ID
        if self.secure:
            session_id = self._generate_secure_session_id()
        else:
            session_id = str(uuid.uuid4())
        
        current_time = time.time()
        ttl = min(ttl or self.default_ttl, self.MAX_TTL)
        
        # Create session object
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=current_time,
            last_accessed=current_time,
            expires_at=current_time + ttl,
            status=SessionStatus.ACTIVE,
            data=data or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Store session
        cache_key = f"session:{session_id}"
        
        if self.available and self.mc:
            try:
                self.mc.set(
                    cache_key.encode(),
                    session.to_dict(),
                    expire=ttl
                )
            except Exception as e:
                logger.error(f"Failed to store session in Memcached: {e}")
                # Fallback to local
                self.local_sessions[session_id] = session
        else:
            self.local_sessions[session_id] = session
        
        # Update metrics
        self.metrics['created'] += 1
        self.metrics['active_sessions'] += 1
        
        logger.debug(f"Created session {session_id} for user {user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object or None if not found/expired
        """
        cache_key = f"session:{session_id}"
        
        session_data = None
        
        if self.available and self.mc:
            try:
                session_data = self.mc.get(cache_key.encode())
            except Exception as e:
                logger.error(f"Failed to get session from Memcached: {e}")
        
        # Fallback to local if not found or Memcached unavailable
        if not session_data and session_id in self.local_sessions:
            session = self.local_sessions[session_id]
            if session.expires_at > time.time():
                session_data = session.to_dict()
            else:
                # Expired, remove from local
                del self.local_sessions[session_id]
                self.metrics['expired'] += 1
                return None
        
        if not session_data:
            return None
        
        # Create session object
        session = Session.from_dict(session_data)
        
        # Check expiration
        if session.expires_at <= time.time():
            self.destroy_session(session_id)
            self.metrics['expired'] += 1
            return None
        
        # Update last accessed time
        session.last_accessed = time.time()
        self.update_session(session)
        
        self.metrics['retrieved'] += 1
        return session
    
    def update_session(self, session: Session) -> bool:
        """
        Update existing session
        
        Args:
            session: Session object to update
            
        Returns:
            True if successful
        """
        cache_key = f"session:{session.session_id}"
        ttl = int(session.expires_at - time.time())
        
        if ttl <= 0:
            # Session expired
            self.destroy_session(session.session_id)
            return False
        
        success = False
        
        if self.available and self.mc:
            try:
                self.mc.set(
                    cache_key.encode(),
                    session.to_dict(),
                    expire=ttl
                )
                success = True
            except Exception as e:
                logger.error(f"Failed to update session in Memcached: {e}")
        
        # Update local if needed
        if not success or session.session_id in self.local_sessions:
            self.local_sessions[session.session_id] = session
            success = True
        
        if success:
            self.metrics['updated'] += 1
        
        return success
    
    def destroy_session(self, session_id: str) -> bool:
        """
        Destroy a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful
        """
        cache_key = f"session:{session_id}"
        success = False
        
        if self.available and self.mc:
            try:
                self.mc.delete(cache_key.encode())
                success = True
            except Exception as e:
                logger.error(f"Failed to destroy session in Memcached: {e}")
        
        # Remove from local
        if session_id in self.local_sessions:
            del self.local_sessions[session_id]
            success = True
        
        if success:
            self.metrics['destroyed'] += 1
            self.metrics['active_sessions'] = max(0, self.metrics['active_sessions'] - 1)
            logger.debug(f"Destroyed session {session_id}")
        
        return success
    
    def extend_session(self, session_id: str, additional_ttl: int) -> bool:
        """
        Extend session expiration
        
        Args:
            session_id: Session identifier
            additional_ttl: Additional seconds to add
            
        Returns:
            True if successful
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Extend expiration
        new_expires = session.expires_at + additional_ttl
        max_expires = time.time() + self.MAX_TTL
        session.expires_at = min(new_expires, max_expires)
        
        return self.update_session(session)
    
    def set_session_data(self, session_id: str, key: str, value: Any) -> bool:
        """
        Set data in session
        
        Args:
            session_id: Session identifier
            key: Data key
            value: Data value
            
        Returns:
            True if successful
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.data[key] = value
        return self.update_session(session)
    
    def get_session_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Get data from session
        
        Args:
            session_id: Session identifier
            key: Data key
            default: Default value if not found
            
        Returns:
            Data value or default
        """
        session = self.get_session(session_id)
        if not session:
            return default
        
        return session.data.get(key, default)
    
    def get_user_sessions(self, user_id: str) -> List[Session]:
        """
        Get all sessions for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of active sessions
        """
        sessions = []
        
        # This is inefficient but necessary without additional indexing
        # In production, consider maintaining a user->sessions index
        
        # Check local sessions
        for session in self.local_sessions.values():
            if session.user_id == user_id and session.expires_at > time.time():
                sessions.append(session)
        
        # Note: Cannot efficiently search Memcached without knowing keys
        # Consider maintaining a separate index in Memcached
        
        return sessions
    
    def invalidate_user_sessions(self, user_id: str) -> int:
        """
        Invalidate all sessions for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of sessions invalidated
        """
        sessions = self.get_user_sessions(user_id)
        count = 0
        
        for session in sessions:
            if self.destroy_session(session.session_id):
                count += 1
        
        logger.info(f"Invalidated {count} sessions for user {user_id}")
        return count
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions from local storage"""
        current_time = time.time()
        
        # Only cleanup periodically
        if current_time - self.last_cleanup < self.CLEANUP_INTERVAL:
            return
        
        # Clean local sessions
        expired_ids = [
            sid for sid, session in self.local_sessions.items()
            if session.expires_at <= current_time
        ]
        
        for sid in expired_ids:
            del self.local_sessions[sid]
            self.metrics['expired'] += 1
        
        if expired_ids:
            logger.debug(f"Cleaned up {len(expired_ids)} expired local sessions")
        
        self.last_cleanup = current_time
    
    def _generate_secure_session_id(self) -> str:
        """Generate cryptographically secure session ID"""
        # Generate random bytes
        random_bytes = secrets.token_bytes(32)
        
        # Add timestamp for uniqueness
        timestamp = str(time.time()).encode()
        
        # Create hash
        hash_input = random_bytes + timestamp
        session_hash = hashlib.sha256(hash_input).hexdigest()
        
        return session_hash
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get session store metrics"""
        # Cleanup before reporting
        self.cleanup_expired_sessions()
        
        return {
            'created': self.metrics['created'],
            'retrieved': self.metrics['retrieved'],
            'updated': self.metrics['updated'],
            'destroyed': self.metrics['destroyed'],
            'expired': self.metrics['expired'],
            'active_sessions': len(self.local_sessions) if not self.available else self.metrics['active_sessions'],
            'backend': 'memcached' if self.available else 'local'
        }
    
    def close(self):
        """Close connection to Memcached"""
        if self.mc:
            try:
                self.mc.close()
            except:
                pass

# Global instance for easy access
_session_store = None

def get_session_store() -> MemcachedSessionStore:
    """Get or create global session store instance"""
    global _session_store
    if _session_store is None:
        _session_store = MemcachedSessionStore()
    return _session_store