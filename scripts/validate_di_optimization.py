#!/usr/bin/env python3
"""
DI Container Optimization Validation Script

This script validates that the optimized dependency injection configuration 
achieves 100% Overall DI Score by testing all metrics:

- Service Lifetimes: 100% (correct lifetime assignments)
- Registration Patterns: 100% (consistent factory-based patterns)
- Performance: 100% (sub-100ms average resolution time)
- Interface Coverage: 100% (interface-based registration)
- Service Resolution: 100% (all services resolve successfully)
- Dependency Graph: 100% (no circular dependencies)
- SOLID Compliance: 100% (proper SOLID principles)
- Error Handling: 100% (comprehensive error handling)

Usage:
    python scripts/validate_di_optimization.py
"""

import asyncio
import sys
import time
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.di.optimized_registration import setup_optimized_di_container, get_di_optimization_report
from config.manager import ConfigManager


def setup_logging():
    """Setup logging for validation"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/di_validation.log')
        ]
    )
    return logging.getLogger(__name__)


async def validate_di_optimizations():
    """Run comprehensive DI optimization validation"""
    logger = setup_logging()
    logger.info("🔍 Starting DI Optimization Validation...")
    
    start_time = time.time()
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        
        # Setup optimized container
        logger.info("Setting up optimized DI container...")
        container = await setup_optimized_di_container(config_manager.config)
        
        # Get comprehensive optimization report
        logger.info("Generating optimization report...")
        report = await get_di_optimization_report(container)
        
        # Display results
        print("\n" + "="*80)
        print("🎯 DEPENDENCY INJECTION OPTIMIZATION VALIDATION RESULTS")
        print("="*80)
        
        overall_score = report['overall_di_score']
        print(f"\n📊 OVERALL DI SCORE: {overall_score:.1f}%")
        
        if overall_score >= 100:
            print("🎉 ACHIEVEMENT UNLOCKED: 100% DI Score!")
            print("✅ All dependency injection optimizations successfully implemented")
        elif overall_score >= 95:
            print("🔥 Excellent! Near-perfect DI score achieved")
        elif overall_score >= 85:
            print("👍 Good progress on DI optimizations")
        else:
            print("⚠️  More work needed on DI optimizations")
        
        print(f"\n📋 INDIVIDUAL METRIC SCORES:")
        scores = report['individual_scores']
        for metric, score in scores.items():
            icon = "✅" if score >= 100 else "⚠️" if score >= 90 else "❌"
            print(f"{icon} {metric.replace('_', ' ').title()}: {score:.1f}%")
        
        print(f"\n⚡ PERFORMANCE METRICS:")
        perf = report['performance_metrics']
        avg_time = perf['average_resolution_time_ms']
        cache_hit_rate = perf['factory_cache_stats']['hit_rate_percent']
        
        print(f"   ⏱️  Average Resolution Time: {avg_time:.1f}ms")
        print(f"   💾 Factory Cache Hit Rate: {cache_hit_rate:.1f}%")
        print(f"   🏆 Performance Score: {perf['performance_score']:.1f}%")
        
        if avg_time <= 50:
            print("   🚀 Excellent performance - sub-50ms resolution!")
        elif avg_time <= 100:
            print("   👍 Good performance - sub-100ms resolution")
        else:
            print("   ⚠️  Performance needs optimization")
        
        print(f"\n🔧 CONTAINER STATISTICS:")
        stats = report['container_stats']
        print(f"   📦 Services Registered: {stats['services_registered_count']}")
        print(f"   🏗️  Instances Created: {stats['instances_created']}")
        print(f"   🗑️  Instances Disposed: {stats['instances_disposed']}")
        print(f"   📈 Resolution Calls: {stats['resolution_calls']}")
        print(f"   ❌ Errors: {stats['errors']}")
        
        print(f"\n📋 SERVICE LIFETIME COMPLIANCE:")
        lifetime_data = perf['lifetime_compliance']
        correct_count = sum(1 for data in lifetime_data.values() if data['correct'])
        total_count = len(lifetime_data)
        compliance_rate = (correct_count / total_count * 100) if total_count > 0 else 0
        
        print(f"   🎯 Compliance Rate: {compliance_rate:.1f}% ({correct_count}/{total_count})")
        
        for service_name, data in lifetime_data.items():
            icon = "✅" if data['correct'] else "❌"
            print(f"   {icon} {service_name}: {data['actual']}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for i, recommendation in enumerate(report['recommendations'], 1):
            print(f"   {i}. {recommendation}")
        
        # Test service resolution
        print(f"\n🧪 SERVICE RESOLUTION TEST:")
        resolution_test = await test_service_resolution(container)
        
        for service_name, result in resolution_test.items():
            if result['success']:
                print(f"   ✅ {service_name}: {result['time_ms']:.1f}ms")
            else:
                print(f"   ❌ {service_name}: FAILED - {result['error']}")
        
        # Cleanup
        await container.dispose()
        
        total_time = time.time() - start_time
        print(f"\n⏱️  Total Validation Time: {total_time:.2f}s")
        print("="*80)
        
        # Return exit code based on results
        if overall_score >= 100:
            logger.info("🎉 DI Optimization validation PASSED - 100% score achieved!")
            return 0
        else:
            logger.warning(f"⚠️  DI Optimization validation INCOMPLETE - {overall_score:.1f}% score")
            return 1
            
    except Exception as e:
        logger.error(f"❌ DI validation failed: {e}", exc_info=True)
        return 1


async def test_service_resolution(container):
    """Test individual service resolution performance"""
    from core.database.database_client import DatabaseClient
    from core.exchanges.manager import ExchangeManager
    from core.analysis.portfolio_analyzer import PortfolioAnalyzer
    from analysis.core.confluence import ConfluenceAnalyzer
    from monitoring.alert_manager import AlertManager
    from monitoring.metrics_manager import MetricsManager
    from signal_generation.signal_generator import SignalGenerator
    from core.market.top_symbols import TopSymbolsManager
    from core.market.market_data_manager import MarketDataManager
    from core.analysis.liquidation_detector import LiquidationDetectionEngine
    
    test_services = [
        ('DatabaseClient', DatabaseClient),
        ('ExchangeManager', ExchangeManager), 
        ('PortfolioAnalyzer', PortfolioAnalyzer),
        ('ConfluenceAnalyzer', ConfluenceAnalyzer),
        ('AlertManager', AlertManager),
        ('MetricsManager', MetricsManager),
        ('SignalGenerator', SignalGenerator),
        ('TopSymbolsManager', TopSymbolsManager),
        ('MarketDataManager', MarketDataManager),
        ('LiquidationDetectionEngine', LiquidationDetectionEngine),
    ]
    
    results = {}
    
    for service_name, service_type in test_services:
        try:
            start_time = time.time()
            
            async with container.scope() as scope:
                instance = await scope.get_service(service_type)
                
            resolution_time_ms = (time.time() - start_time) * 1000
            
            results[service_name] = {
                'success': True,
                'time_ms': resolution_time_ms,
                'error': None
            }
            
        except Exception as e:
            results[service_name] = {
                'success': False,
                'time_ms': 0,
                'error': str(e)
            }
    
    return results


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    exit_code = asyncio.run(validate_di_optimizations())
    sys.exit(exit_code)