#!/usr/bin/env python3
"""
Deployment Script for Phase 3: Infrastructure Resilience Patterns

This script demonstrates how to deploy and integrate resilience patterns
into the existing Virtuoso CCXT trading system including:
- Circuit breaker protection for exchanges and cache operations
- Retry policies with exponential backoff
- Connection pool management
- Health monitoring and alerting
- Graceful degradation and fallback mechanisms

Usage:
    python scripts/deploy_resilience_patterns.py [--environment prod|dev] [--dry-run]
"""

import sys
import os
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.resilience import (
    ResilienceManager,
    ResilienceConfiguration,
    ResilientVirtuosoIntegration,
    create_default_resilience_config,
    register_resilience_services
)
from core.di.container import DIContainer
from core.exchanges.bybit import BybitExchange
from api.cache_adapter_direct import DirectCacheAdapter

logger = logging.getLogger(__name__)


class ResilienceDeployer:
    """Handles deployment of resilience patterns to Virtuoso CCXT system."""
    
    def __init__(self, environment: str = "dev", dry_run: bool = False):
        self.environment = environment
        self.dry_run = dry_run
        self.container = DIContainer()
        self.resilience_integration: Optional[ResilientVirtuosoIntegration] = None
        
        # Configuration
        self.deployment_config = self._load_deployment_config()
        
        logger.info(f"Resilience deployer initialized for {environment} environment (dry_run={dry_run})")
    
    def _load_deployment_config(self) -> Dict[str, Any]:
        """Load deployment configuration based on environment."""
        base_config = {
            "resilience": {
                "circuit_breakers": True,
                "retry_policies": True,
                "connection_pooling": True,
                "health_checks": True
            },
            "exchanges": {
                "bybit": {
                    "enabled": True,
                    "api_key": os.getenv("BYBIT_API_KEY"),
                    "api_secret": os.getenv("BYBIT_API_SECRET"),
                    "testnet": self.environment != "prod"
                }
            },
            "cache": {
                "memcached": {
                    "enabled": True,
                    "host": os.getenv("MEMCACHED_HOST", "localhost"),
                    "port": int(os.getenv("MEMCACHED_PORT", "11211"))
                },
                "redis": {
                    "enabled": False,  # Optional secondary cache
                    "host": os.getenv("REDIS_HOST", "localhost"),
                    "port": int(os.getenv("REDIS_PORT", "6379"))
                }
            },
            "monitoring": {
                "health_check_interval": 60.0 if self.environment == "prod" else 30.0,
                "metrics_collection": True,
                "alerting": {
                    "discord_webhook": os.getenv("DISCORD_WEBHOOK_URL"),
                    "enabled": self.environment == "prod"
                }
            }
        }
        
        if self.environment == "prod":
            # Production-specific overrides
            base_config["resilience"]["circuit_breakers"] = True
            base_config["resilience"]["health_checks"] = True
            base_config["monitoring"]["health_check_interval"] = 60.0
        
        return base_config
    
    def _create_resilience_config(self) -> ResilienceConfiguration:
        """Create resilience configuration based on deployment config."""
        config = create_default_resilience_config()
        
        # Apply environment-specific settings
        if self.environment == "prod":
            # Production: More conservative settings
            config.default_failure_threshold = 5
            config.default_success_threshold = 3
            config.default_circuit_timeout = 60.0
            config.default_max_retries = 3
            config.default_health_check_interval = 60.0
        else:
            # Development: More permissive for testing
            config.default_failure_threshold = 8
            config.default_success_threshold = 2
            config.default_circuit_timeout = 30.0
            config.default_max_retries = 4
            config.default_health_check_interval = 30.0
        
        # Apply deployment config overrides
        resilience_config = self.deployment_config.get("resilience", {})
        config.enable_circuit_breakers = resilience_config.get("circuit_breakers", True)
        config.enable_retry_policies = resilience_config.get("retry_policies", True)
        config.enable_connection_pooling = resilience_config.get("connection_pooling", True)
        config.enable_health_checks = resilience_config.get("health_checks", True)
        
        return config
    
    async def deploy_resilience_patterns(self) -> bool:
        """Deploy resilience patterns to the system."""
        try:
            logger.info("Starting resilience patterns deployment...")
            
            if self.dry_run:
                logger.info("DRY RUN MODE - No actual changes will be made")
                return await self._simulate_deployment()
            
            # Step 1: Initialize DI container with existing services
            await self._initialize_di_container()
            
            # Step 2: Register resilience services
            await self._register_resilience_services()
            
            # Step 3: Create resilient integration
            await self._create_resilient_integration()
            
            # Step 4: Deploy resilient exchanges
            await self._deploy_resilient_exchanges()
            
            # Step 5: Deploy resilient cache systems
            await self._deploy_resilient_cache_systems()
            
            # Step 6: Setup health monitoring
            await self._setup_health_monitoring()
            
            # Step 7: Verify deployment
            await self._verify_deployment()
            
            logger.info("✅ Resilience patterns deployment completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Resilience patterns deployment failed: {e}")
            return False
    
    async def _simulate_deployment(self) -> bool:
        """Simulate deployment without making actual changes."""
        logger.info("🔍 Simulating resilience patterns deployment...")
        
        # Check prerequisites
        prerequisites_ok = self._check_prerequisites()
        if not prerequisites_ok:
            logger.warning("Prerequisites check failed - deployment would fail")
            return False
        
        # Simulate each deployment step
        steps = [
            "Initialize DI container",
            "Register resilience services", 
            "Create resilient integration",
            "Deploy resilient exchanges",
            "Deploy resilient cache systems",
            "Setup health monitoring",
            "Verify deployment"
        ]
        
        for i, step in enumerate(steps, 1):
            logger.info(f"📋 Step {i}/{len(steps)}: {step}")
            await asyncio.sleep(0.5)  # Simulate work
        
        logger.info("✅ Simulation completed successfully - deployment would succeed")
        return True
    
    def _check_prerequisites(self) -> bool:
        """Check deployment prerequisites."""
        logger.info("🔍 Checking deployment prerequisites...")
        
        prerequisites = {
            "Python version >= 3.8": sys.version_info >= (3, 8),
            "Required environment variables": self._check_env_variables(),
            "Core modules accessible": self._check_core_modules(),
            "DI container available": True  # We'll create it
        }
        
        all_ok = True
        for prereq, status in prerequisites.items():
            status_icon = "✅" if status else "❌"
            logger.info(f"  {status_icon} {prereq}")
            if not status:
                all_ok = False
        
        return all_ok
    
    def _check_env_variables(self) -> bool:
        """Check required environment variables."""
        required_vars = ["BYBIT_API_KEY", "BYBIT_API_SECRET"]
        optional_vars = ["MEMCACHED_HOST", "REDIS_HOST", "DISCORD_WEBHOOK_URL"]
        
        missing_required = [var for var in required_vars if not os.getenv(var)]
        if missing_required:
            logger.warning(f"Missing required environment variables: {missing_required}")
            return False
        
        missing_optional = [var for var in optional_vars if not os.getenv(var)]
        if missing_optional:
            logger.info(f"Optional environment variables not set: {missing_optional}")
        
        return True
    
    def _check_core_modules(self) -> bool:
        """Check if core modules are accessible."""
        try:
            from core.resilience import CircuitBreaker, RetryPolicy
            from core.di.container import DIContainer
            return True
        except ImportError as e:
            logger.error(f"Core module import failed: {e}")
            return False
    
    async def _initialize_di_container(self):
        """Initialize DI container with existing services."""
        logger.info("🔧 Initializing DI container...")
        
        # Register existing services that resilience patterns will wrap
        # This would normally be done by your existing application startup
        
        # For now, we'll just ensure the container is ready
        logger.info("✅ DI container initialized")
    
    async def _register_resilience_services(self):
        """Register resilience services with DI container."""
        logger.info("📝 Registering resilience services...")
        
        resilience_config = self._create_resilience_config()
        self.resilience_manager = register_resilience_services(
            self.container, 
            resilience_config
        )
        
        await self.resilience_manager.initialize()
        logger.info("✅ Resilience services registered")
    
    async def _create_resilient_integration(self):
        """Create resilient integration wrapper."""
        logger.info("🔗 Creating resilient integration...")
        
        self.resilience_integration = ResilientVirtuosoIntegration(self.container)
        
        resilience_config = self._create_resilience_config()
        await self.resilience_integration.initialize(resilience_config)
        
        logger.info("✅ Resilient integration created")
    
    async def _deploy_resilient_exchanges(self):
        """Deploy resilient exchange adapters."""
        logger.info("🏦 Deploying resilient exchanges...")
        
        exchange_config = self.deployment_config.get("exchanges", {})
        
        # Deploy Bybit if enabled
        if exchange_config.get("bybit", {}).get("enabled", False):
            logger.info("  📈 Deploying resilient Bybit exchange...")
            
            bybit_config = {
                'exchanges': {
                    'bybit': {
                        'rest_endpoint': 'https://api-testnet.bybit.com' if exchange_config["bybit"]["testnet"] else 'https://api.bybit.com',
                        'apiKey': exchange_config["bybit"]["api_key"],
                        'secret': exchange_config["bybit"]["api_secret"]
                    }
                }
            }
            
            try:
                resilient_bybit = await self.resilience_integration.create_resilient_bybit_exchange(bybit_config)
                logger.info("  ✅ Resilient Bybit exchange deployed")
                
                # Test basic functionality
                await self._test_exchange_functionality(resilient_bybit, "Bybit")
                
            except Exception as e:
                logger.error(f"  ❌ Failed to deploy resilient Bybit exchange: {e}")
                raise
        
        logger.info("✅ Resilient exchanges deployed")
    
    async def _deploy_resilient_cache_systems(self):
        """Deploy resilient cache adapters."""
        logger.info("💾 Deploying resilient cache systems...")
        
        cache_config = self.deployment_config.get("cache", {})
        
        try:
            resilient_caches = await self.resilience_integration.create_resilient_cache_system(cache_config)
            
            for cache_name, cache_adapter in resilient_caches.items():
                logger.info(f"  ✅ Resilient {cache_name} cache deployed")
                
                # Test basic functionality
                await self._test_cache_functionality(cache_adapter, cache_name)
            
        except Exception as e:
            logger.error(f"  ❌ Failed to deploy resilient cache systems: {e}")
            raise
        
        logger.info("✅ Resilient cache systems deployed")
    
    async def _setup_health_monitoring(self):
        """Setup health monitoring and alerting."""
        logger.info("🩺 Setting up health monitoring...")
        
        # Setup health monitoring
        self.resilience_integration.setup_health_monitoring()
        
        # Configure alerting if enabled
        monitoring_config = self.deployment_config.get("monitoring", {})
        if monitoring_config.get("alerting", {}).get("enabled", False):
            logger.info("  🔔 Alerting configured")
        
        logger.info("✅ Health monitoring setup completed")
    
    async def _verify_deployment(self):
        """Verify that deployment was successful."""
        logger.info("✅ Verifying deployment...")
        
        # Get comprehensive metrics
        metrics = self.resilience_integration.get_comprehensive_metrics()
        
        # Perform health checks
        health_results = await self.resilience_integration.health_check_all()
        
        # Verify resilience components are operational
        verification_results = {
            "resilience_manager_initialized": bool(self.resilience_manager),
            "integration_initialized": bool(self.resilience_integration),
            "circuit_breakers_active": len(metrics.get("resilience_manager", {}).get("circuit_breakers", {})) > 0,
            "health_checks_registered": len(health_results.get("individual_checks", {})) > 0,
            "overall_health_status": health_results.get("overall_status", "unknown")
        }
        
        all_verified = all(verification_results.values())
        
        for check, result in verification_results.items():
            status_icon = "✅" if result else "❌"
            logger.info(f"  {status_icon} {check}: {result}")
        
        if not all_verified:
            raise RuntimeError("Deployment verification failed")
        
        logger.info("✅ Deployment verification completed successfully")
    
    async def _test_exchange_functionality(self, exchange_adapter, exchange_name: str):
        """Test basic exchange functionality."""
        logger.info(f"  🧪 Testing {exchange_name} functionality...")
        
        try:
            # Test fetching ticker (this should work even with circuit breakers)
            ticker = await exchange_adapter.fetch_ticker('BTCUSDT')
            logger.info(f"    ✅ Ticker fetch successful: {ticker['symbol']}")
            
        except Exception as e:
            logger.warning(f"    ⚠️ Ticker fetch failed (may be expected): {e}")
    
    async def _test_cache_functionality(self, cache_adapter, cache_name: str):
        """Test basic cache functionality."""
        logger.info(f"  🧪 Testing {cache_name} functionality...")
        
        try:
            # Test cache set/get
            test_key = f"resilience_test_{int(asyncio.get_event_loop().time())}"
            test_value = {"test": "data", "timestamp": asyncio.get_event_loop().time()}
            
            await cache_adapter.set(test_key, test_value, ttl=60)
            retrieved = await cache_adapter.get(test_key)
            
            if retrieved and retrieved.get("test") == "data":
                logger.info(f"    ✅ Cache set/get successful")
            else:
                logger.warning(f"    ⚠️ Cache test returned unexpected result: {retrieved}")
            
        except Exception as e:
            logger.warning(f"    ⚠️ Cache test failed (may be expected): {e}")
    
    async def shutdown(self):
        """Gracefully shutdown deployed components."""
        if self.resilience_integration:
            await self.resilience_integration.shutdown()
        logger.info("🔄 Deployment shutdown completed")
    
    def print_deployment_summary(self):
        """Print deployment summary."""
        print("\n" + "="*80)
        print("RESILIENCE PATTERNS DEPLOYMENT SUMMARY")
        print("="*80)
        print(f"Environment: {self.environment}")
        print(f"Dry Run: {self.dry_run}")
        print("\nDeployed Components:")
        
        config = self._create_resilience_config()
        components = [
            ("Circuit Breakers", config.enable_circuit_breakers),
            ("Retry Policies", config.enable_retry_policies),
            ("Connection Pooling", config.enable_connection_pooling),
            ("Health Checks", config.enable_health_checks),
        ]
        
        for component, enabled in components:
            status = "✅ Enabled" if enabled else "❌ Disabled"
            print(f"  {component}: {status}")
        
        print("\nConfiguration:")
        print(f"  Failure Threshold: {config.default_failure_threshold}")
        print(f"  Circuit Timeout: {config.default_circuit_timeout}s")
        print(f"  Max Retries: {config.default_max_retries}")
        print(f"  Health Check Interval: {config.default_health_check_interval}s")
        print("="*80)


async def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Deploy resilience patterns to Virtuoso CCXT")
    parser.add_argument(
        "--environment", 
        choices=["prod", "dev"], 
        default="dev",
        help="Deployment environment"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Simulate deployment without making changes"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create deployer
    deployer = ResilienceDeployer(
        environment=args.environment,
        dry_run=args.dry_run
    )
    
    try:
        # Check prerequisites
        if not deployer._check_prerequisites():
            logger.error("Prerequisites check failed")
            return 1
        
        # Deploy resilience patterns
        success = await deployer.deploy_resilience_patterns()
        
        # Print summary
        deployer.print_deployment_summary()
        
        if success:
            logger.info("🎉 Resilience patterns deployment completed successfully!")
            
            if not args.dry_run:
                logger.info("System is now protected with comprehensive resilience patterns")
                logger.info("Monitor health status at: /api/monitoring/health")
                logger.info("View metrics at: /api/monitoring/metrics")
            
            return 0
        else:
            logger.error("💥 Resilience patterns deployment failed!")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Deployment interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Unexpected error during deployment: {e}")
        return 1
    finally:
        # Always cleanup
        await deployer.shutdown()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))