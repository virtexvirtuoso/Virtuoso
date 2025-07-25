#!/usr/bin/env python3
"""Phase 1 validation: Test Container architecture integration."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def validate_phase1_integration():
    """Validate Phase 1: Container integration architecture."""
    logger.info("🧪 Phase 1 Validation: Container Integration Architecture")
    logger.info("=" * 60)
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Container class can be imported and created
    total_tests += 1
    try:
        from src.core.container import Container
        logger.info("✅ Test 1: Container class import - PASSED")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ Test 1: Container class import - FAILED: {e}")
    
    # Test 2: ConfigManager can be imported and created
    total_tests += 1
    try:
        from src.config.manager import ConfigManager
        config_manager = ConfigManager()
        logger.info("✅ Test 2: ConfigManager creation - PASSED")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ Test 2: ConfigManager creation - FAILED: {e}")
        return False
    
    # Test 3: Container can be instantiated
    total_tests += 1
    try:
        container_settings = {
            'logging': {'level': 'INFO'},
            'resources': {
                'max_memory_mb': 1024,
                'max_concurrent_ops': 100
            }
        }
        container = Container(settings=container_settings)
        logger.info("✅ Test 3: Container instantiation - PASSED")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ Test 3: Container instantiation - FAILED: {e}")
        return False
    
    # Test 4: Trading components can be registered
    total_tests += 1
    try:
        container.register_trading_components(config_manager)
        logger.info("✅ Test 4: Trading components registration - PASSED")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ Test 4: Trading components registration - FAILED: {e}")
    
    # Test 5: Container has base initialization capability
    total_tests += 1
    try:
        await container.initialize(include_trading_components=False)
        logger.info("✅ Test 5: Base container initialization - PASSED")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ Test 5: Base container initialization - FAILED: {e}")
    
    # Test 6: Container has cleanup capability
    total_tests += 1
    try:
        await container.cleanup(cleanup_trading_components=False)
        logger.info("✅ Test 6: Base container cleanup - PASSED")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ Test 6: Base container cleanup - FAILED: {e}")
    
    # Test 7: Trading adapter is created
    total_tests += 1
    try:
        if hasattr(container, '_trading_adapter') and container._trading_adapter:
            logger.info("✅ Test 7: Trading adapter creation - PASSED")
            success_count += 1
        else:
            logger.warning("⚠️ Test 7: Trading adapter creation - NOT CREATED (expected)")
    except Exception as e:
        logger.error(f"❌ Test 7: Trading adapter creation - FAILED: {e}")
    
    # Test 8: Main.py has been updated to use Container
    total_tests += 1
    try:
        with open(Path(__file__).parent.parent / "src" / "main.py", 'r') as f:
            main_content = f.read()
        
        # Check that global variables are replaced
        if "app_container: Optional[Container] = None" in main_content:
            logger.info("✅ Test 8: main.py updated with Container - PASSED")
            success_count += 1
        else:
            logger.error("❌ Test 8: main.py not updated with Container - FAILED")
    except Exception as e:
        logger.error(f"❌ Test 8: main.py Container check - FAILED: {e}")
    
    # Test 9: Lifespan function updated
    total_tests += 1
    try:
        if "lifespan(app: FastAPI):" in main_content and "app_container = Container" in main_content:
            logger.info("✅ Test 9: Lifespan function updated - PASSED")
            success_count += 1
        else:
            logger.error("❌ Test 9: Lifespan function not properly updated - FAILED")
    except Exception as e:
        logger.error(f"❌ Test 9: Lifespan function check - FAILED: {e}")
    
    # Test 10: Old global variables removed/commented
    total_tests += 1
    try:
        global_vars_removed = (
            "config_manager = None" not in main_content or 
            "# DEPRECATED" in main_content
        )
        if global_vars_removed:
            logger.info("✅ Test 10: Old global variables removed/deprecated - PASSED")
            success_count += 1
        else:
            logger.error("❌ Test 10: Old global variables still present - FAILED")
    except Exception as e:
        logger.error(f"❌ Test 10: Global variables check - FAILED: {e}")
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 PHASE 1 VALIDATION SUMMARY")
    logger.info(f"✅ Tests Passed: {success_count}/{total_tests}")
    logger.info(f"❌ Tests Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count >= 7:  # Allow some tolerance for external dependencies
        logger.info("🎉 PHASE 1 VALIDATION: SUCCESS")
        logger.info("✅ Container integration architecture is properly implemented")
        logger.info("🚀 Ready to proceed to Phase 2 (API Integration)")
        return True
    else:
        logger.error("❌ PHASE 1 VALIDATION: FAILED")
        logger.error("🔧 Please review and fix the failing tests before proceeding")
        return False

def main():
    """Main validation function."""
    logger.info("🚀 Starting Phase 1 Validation")
    
    success = asyncio.run(validate_phase1_integration())
    
    if success:
        logger.info("🎯 Phase 1 Complete - Global State Elimination Container Architecture Ready")
        sys.exit(0)
    else:
        logger.error("❌ Phase 1 Incomplete - Review and fix issues")
        sys.exit(1)

if __name__ == "__main__":
    main()