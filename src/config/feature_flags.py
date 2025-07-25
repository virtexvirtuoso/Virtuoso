"""
Feature Flag Management System
Provides centralized feature flag management with runtime toggling and validation.
"""

import logging
from typing import Dict, Any, Optional, List, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path


logger = logging.getLogger(__name__)


class FeatureState(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


@dataclass
class FeatureFlag:
    """Represents a single feature flag."""
    name: str
    enabled: bool
    category: str
    description: str = ""
    experimental: bool = False
    deprecated: bool = False
    dependencies: List[str] = field(default_factory=list)
    environment_override: Optional[str] = None
    rollout_percentage: float = 100.0
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    
    @property
    def state(self) -> FeatureState:
        """Get the current state of the feature flag."""
        if self.deprecated:
            return FeatureState.DEPRECATED
        elif self.experimental:
            return FeatureState.EXPERIMENTAL
        elif self.enabled:
            return FeatureState.ENABLED
        else:
            return FeatureState.DISABLED
    
    def is_enabled_for_user(self, user_id: Optional[str] = None) -> bool:
        """Check if feature is enabled for a specific user (rollout support)."""
        if not self.enabled:
            return False
        
        if self.rollout_percentage >= 100.0:
            return True
        
        if user_id is None:
            # Without user ID, use random rollout
            import random
            return random.random() * 100 < self.rollout_percentage
        
        # Deterministic rollout based on user ID hash
        import hashlib
        hash_value = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
        return (hash_value % 100) < self.rollout_percentage


class FeatureFlagManager:
    """Manages feature flags with runtime toggling and dependency checking."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.feature_flags_config = config.get('feature_flags', {})
        self.logger = logging.getLogger(__name__)
        
        # Feature flag storage
        self.flags: Dict[str, FeatureFlag] = {}
        self.categories: Set[str] = set()
        self.change_listeners: List[Callable[[str, bool], None]] = []
        
        # Load feature flags from configuration
        self._load_feature_flags()
        
        # Performance optimization: Cache enabled flags
        self._enabled_flags_cache: Dict[str, bool] = {}
        self._cache_expiry = datetime.now() + timedelta(minutes=5)
        
        self.logger.info(f"Feature Flag Manager initialized with {len(self.flags)} flags")
        self.logger.info(f"Categories: {sorted(self.categories)}")
    
    def _load_feature_flags(self):
        """Load feature flags from configuration."""
        for category_name, category_flags in self.feature_flags_config.items():
            self.categories.add(category_name)
            
            if not isinstance(category_flags, dict):
                continue
                
            for flag_name, flag_enabled in category_flags.items():
                full_flag_name = f"{category_name}.{flag_name}"
                
                # Check for environment override
                env_var = f"FEATURE_{category_name.upper()}_{flag_name.upper()}"
                env_override = os.getenv(env_var)
                if env_override is not None:
                    flag_enabled = env_override.lower() in ('true', '1', 'yes', 'on')
                
                # Determine if experimental or deprecated
                experimental = category_name == "experimental"
                deprecated = False  # Could be determined by flag naming convention
                
                self.flags[full_flag_name] = FeatureFlag(
                    name=full_flag_name,
                    enabled=bool(flag_enabled),
                    category=category_name,
                    description=f"Feature flag for {flag_name} in {category_name}",
                    experimental=experimental,
                    deprecated=deprecated,
                    environment_override=env_var
                )
        
        self.logger.info(f"Loaded {len(self.flags)} feature flags")
    
    def is_enabled(self, flag_name: str, user_id: Optional[str] = None) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_name: Feature flag name (can be full name or short name)
            user_id: Optional user ID for rollout support
            
        Returns:
            True if feature is enabled, False otherwise
        """
        # Use cache if available and not expired
        if user_id is None and datetime.now() < self._cache_expiry:
            if flag_name in self._enabled_flags_cache:
                return self._enabled_flags_cache[flag_name]
        
        # Resolve flag name if it's a short name
        resolved_name = self._resolve_flag_name(flag_name)
        if not resolved_name:
            self.logger.warning(f"Feature flag '{flag_name}' not found")
            return False
        
        flag = self.flags[resolved_name]
        enabled = flag.is_enabled_for_user(user_id)
        
        # Cache the result (only for non-user-specific queries)
        if user_id is None:
            self._enabled_flags_cache[flag_name] = enabled
        
        return enabled
    
    def _resolve_flag_name(self, flag_name: str) -> Optional[str]:
        """Resolve flag name to full name."""
        # If it's already a full name and exists
        if flag_name in self.flags:
            return flag_name
        
        # Try to find by short name
        matching_flags = [name for name in self.flags.keys() if name.endswith(f".{flag_name}")]
        
        if len(matching_flags) == 1:
            return matching_flags[0]
        elif len(matching_flags) > 1:
            self.logger.warning(f"Ambiguous flag name '{flag_name}': {matching_flags}")
            return matching_flags[0]  # Return first match
        
        return None
    
    def enable_flag(self, flag_name: str, notify_listeners: bool = True):
        """Enable a feature flag."""
        resolved_name = self._resolve_flag_name(flag_name)
        if not resolved_name:
            raise ValueError(f"Feature flag '{flag_name}' not found")
        
        flag = self.flags[resolved_name]
        if not flag.enabled:
            flag.enabled = True
            flag.last_modified = datetime.now()
            
            # Clear cache
            self._clear_cache()
            
            if notify_listeners:
                self._notify_listeners(resolved_name, True)
            
            self.logger.info(f"Enabled feature flag: {resolved_name}")
    
    def disable_flag(self, flag_name: str, notify_listeners: bool = True):
        """Disable a feature flag."""
        resolved_name = self._resolve_flag_name(flag_name)
        if not resolved_name:
            raise ValueError(f"Feature flag '{flag_name}' not found")
        
        flag = self.flags[resolved_name]
        if flag.enabled:
            flag.enabled = False
            flag.last_modified = datetime.now()
            
            # Clear cache
            self._clear_cache()
            
            if notify_listeners:
                self._notify_listeners(resolved_name, False)
            
            self.logger.info(f"Disabled feature flag: {resolved_name}")
    
    def toggle_flag(self, flag_name: str, notify_listeners: bool = True):
        """Toggle a feature flag."""
        resolved_name = self._resolve_flag_name(flag_name)
        if not resolved_name:
            raise ValueError(f"Feature flag '{flag_name}' not found")
        
        flag = self.flags[resolved_name]
        if flag.enabled:
            self.disable_flag(flag_name, notify_listeners)
        else:
            self.enable_flag(flag_name, notify_listeners)
    
    def get_flag(self, flag_name: str) -> Optional[FeatureFlag]:
        """Get a feature flag object."""
        resolved_name = self._resolve_flag_name(flag_name)
        if resolved_name:
            return self.flags[resolved_name]
        return None
    
    def get_flags_by_category(self, category: str) -> Dict[str, FeatureFlag]:
        """Get all flags in a specific category."""
        return {name: flag for name, flag in self.flags.items() if flag.category == category}
    
    def get_enabled_flags(self) -> Dict[str, FeatureFlag]:
        """Get all enabled flags."""
        return {name: flag for name, flag in self.flags.items() if flag.enabled}
    
    def get_experimental_flags(self) -> Dict[str, FeatureFlag]:
        """Get all experimental flags."""
        return {name: flag for name, flag in self.flags.items() if flag.experimental}
    
    def add_change_listener(self, callback: Callable[[str, bool], None]):
        """Add a listener for feature flag changes."""
        self.change_listeners.append(callback)
    
    def remove_change_listener(self, callback: Callable[[str, bool], None]):
        """Remove a change listener."""
        if callback in self.change_listeners:
            self.change_listeners.remove(callback)
    
    def _notify_listeners(self, flag_name: str, enabled: bool):
        """Notify all listeners of a flag change."""
        for listener in self.change_listeners:
            try:
                listener(flag_name, enabled)
            except Exception as e:
                self.logger.error(f"Error notifying flag change listener: {str(e)}")
    
    def _clear_cache(self):
        """Clear the enabled flags cache."""
        self._enabled_flags_cache.clear()
        self._cache_expiry = datetime.now() + timedelta(minutes=5)
    
    def check_dependencies(self, flag_name: str) -> List[str]:
        """Check if all dependencies for a flag are satisfied."""
        flag = self.get_flag(flag_name)
        if not flag:
            return [f"Flag '{flag_name}' not found"]
        
        missing_dependencies = []
        for dep in flag.dependencies:
            if not self.is_enabled(dep):
                missing_dependencies.append(dep)
        
        return missing_dependencies
    
    def get_flag_status_report(self) -> Dict[str, Any]:
        """Generate a comprehensive flag status report."""
        total_flags = len(self.flags)
        enabled_count = len(self.get_enabled_flags())
        experimental_count = len(self.get_experimental_flags())
        deprecated_count = len([f for f in self.flags.values() if f.deprecated])
        
        category_stats = {}
        for category in self.categories:
            category_flags = self.get_flags_by_category(category)
            category_stats[category] = {
                'total': len(category_flags),
                'enabled': len([f for f in category_flags.values() if f.enabled]),
                'experimental': len([f for f in category_flags.values() if f.experimental])
            }
        
        return {
            'summary': {
                'total_flags': total_flags,
                'enabled_flags': enabled_count,
                'disabled_flags': total_flags - enabled_count,
                'experimental_flags': experimental_count,
                'deprecated_flags': deprecated_count,
                'categories': len(self.categories)
            },
            'category_breakdown': category_stats,
            'enabled_flags': {name: flag.state.value for name, flag in self.get_enabled_flags().items()},
            'experimental_flags': {name: flag.enabled for name, flag in self.get_experimental_flags().items()},
            'cache_info': {
                'cached_flags': len(self._enabled_flags_cache),
                'cache_expires': self._cache_expiry.isoformat()
            }
        }
    
    def export_flags_config(self) -> Dict[str, Any]:
        """Export current flag configuration for saving."""
        config = {}
        
        for category in self.categories:
            config[category] = {}
            category_flags = self.get_flags_by_category(category)
            
            for flag_name, flag in category_flags.items():
                short_name = flag_name.split('.', 1)[1]  # Remove category prefix
                config[category][short_name] = flag.enabled
        
        return config
    
    def save_flags_to_file(self, file_path: Path):
        """Save current flag configuration to a file."""
        config = self.export_flags_config()
        
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        self.logger.info(f"Saved feature flags configuration to {file_path}")


# Decorator for feature flag gating
def feature_flag(flag_name: str, manager: Optional[FeatureFlagManager] = None):
    """
    Decorator to gate function execution behind a feature flag.
    
    Args:
        flag_name: Name of the feature flag
        manager: FeatureFlagManager instance (if None, uses global instance)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Use global manager if none provided
            if manager is None:
                # Try to get from global context (would need to be set up)
                global_manager = getattr(wrapper, '_global_manager', None)
                if global_manager is None:
                    logger.warning(f"No feature flag manager available for flag '{flag_name}'")
                    return func(*args, **kwargs)
                current_manager = global_manager
            else:
                current_manager = manager
            
            if current_manager.is_enabled(flag_name):
                return func(*args, **kwargs)
            else:
                logger.debug(f"Function '{func.__name__}' skipped due to disabled flag '{flag_name}'")
                return None
        
        return wrapper
    return decorator


# Context manager for temporary flag changes
class TemporaryFlagChange:
    """Context manager for temporarily changing a feature flag."""
    
    def __init__(self, manager: FeatureFlagManager, flag_name: str, enabled: bool):
        self.manager = manager
        self.flag_name = flag_name
        self.new_enabled = enabled
        self.original_enabled = None
    
    def __enter__(self):
        flag = self.manager.get_flag(self.flag_name)
        if flag:
            self.original_enabled = flag.enabled
            if self.new_enabled != self.original_enabled:
                if self.new_enabled:
                    self.manager.enable_flag(self.flag_name, notify_listeners=False)
                else:
                    self.manager.disable_flag(self.flag_name, notify_listeners=False)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_enabled is not None:
            flag = self.manager.get_flag(self.flag_name)
            if flag and flag.enabled != self.original_enabled:
                if self.original_enabled:
                    self.manager.enable_flag(self.flag_name, notify_listeners=False)
                else:
                    self.manager.disable_flag(self.flag_name, notify_listeners=False)


def create_feature_flag_manager(config: Dict[str, Any]) -> FeatureFlagManager:
    """Factory function to create feature flag manager from configuration."""
    return FeatureFlagManager(config)


async def test_feature_flags():
    """Test feature flag functionality."""
    config = {
        'feature_flags': {
            'trading': {
                'advanced_orders': True,
                'portfolio_rebalancing': False
            },
            'analysis': {
                'ml_signals': False,
                'enhanced_indicators': True
            },
            'experimental': {
                'quantum_models': False,
                'ai_sizing': False
            }
        }
    }
    
    # Create feature flag manager
    manager = FeatureFlagManager(config)
    
    # Test flag checking
    print("Feature Flag Tests:")
    print(f"advanced_orders enabled: {manager.is_enabled('advanced_orders')}")
    print(f"ml_signals enabled: {manager.is_enabled('ml_signals')}")
    print(f"enhanced_indicators enabled: {manager.is_enabled('enhanced_indicators')}")
    
    # Test flag toggling
    print(f"\nBefore toggle - portfolio_rebalancing: {manager.is_enabled('portfolio_rebalancing')}")
    manager.toggle_flag('portfolio_rebalancing')
    print(f"After toggle - portfolio_rebalancing: {manager.is_enabled('portfolio_rebalancing')}")
    
    # Test status report
    report = manager.get_flag_status_report()
    print(f"\nStatus Report:")
    print(f"Total flags: {report['summary']['total_flags']}")
    print(f"Enabled flags: {report['summary']['enabled_flags']}")
    print(f"Categories: {report['summary']['categories']}")
    
    # Test category filtering
    trading_flags = manager.get_flags_by_category('trading')
    print(f"\nTrading flags: {len(trading_flags)}")
    for name, flag in trading_flags.items():
        print(f"  {name}: {flag.state.value}")
    
    # Test temporary flag change
    print(f"\nTesting temporary flag change:")
    print(f"Before context: ml_signals = {manager.is_enabled('ml_signals')}")
    
    with TemporaryFlagChange(manager, 'ml_signals', True):
        print(f"Inside context: ml_signals = {manager.is_enabled('ml_signals')}")
    
    print(f"After context: ml_signals = {manager.is_enabled('ml_signals')}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_feature_flags())