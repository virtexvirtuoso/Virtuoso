#!/usr/bin/env python3
"""
Bitcoin Beta Report Demo Script

This script demonstrates how to integrate the Bitcoin Beta Report
with your production trading system. Run this after your main system is running.
"""

import asyncio
import logging
import requests
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BitcoinBetaDemo:
    """Demo class for Bitcoin Beta Report integration."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    async def check_system_status(self):
        """Check if the main system is running."""
        try:
            response = requests.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Main system is running")
                logger.info(f"   Status: {data.get('status', 'unknown')}")
                
                # Check components
                components = data.get('components', {})
                for name, info in components.items():
                    status = info.get('status', 'unknown')
                    logger.info(f"   {name}: {status}")
                    
                return True
            else:
                logger.error(f"❌ System returned status {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error("❌ Cannot connect to main system")
            logger.info("   Make sure the main system is running on localhost:8000")
            return False
        except Exception as e:
            logger.error(f"❌ Error checking system: {str(e)}")
            return False
            
    async def check_beta_report_status(self):
        """Check Bitcoin Beta Report availability."""
        try:
            response = requests.get(f"{self.base_url}/api/bitcoin-beta/status")
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Bitcoin Beta Report feature is available")
                logger.info(f"   Description: {data.get('description')}")
                
                features = data.get('features', [])
                for feature in features:
                    logger.info(f"   • {feature}")
                    
                schedule = data.get('schedule', {})
                logger.info(f"   Schedule: {schedule.get('frequency')} at {', '.join(schedule.get('times', []))}")
                
                return True
            else:
                logger.error(f"❌ Beta report API returned status {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error("❌ Cannot connect to beta report API")
            return False
        except Exception as e:
            logger.error(f"❌ Error checking beta report: {str(e)}")
            return False
            
    async def get_current_symbols(self):
        """Get currently analyzed symbols."""
        try:
            response = requests.get(f"{self.base_url}/api/top-symbols")
            if response.status_code == 200:
                data = response.json()
                symbols = data.get('symbols', [])
                logger.info(f"📊 Current symbols being analyzed: {len(symbols)}")
                for symbol in symbols:
                    logger.info(f"   • {symbol}")
                return symbols
            else:
                logger.warning("⚠️  Could not fetch current symbols")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error getting symbols: {str(e)}")
            return []
            
    async def generate_beta_report(self):
        """Generate a Bitcoin Beta Report manually."""
        try:
            logger.info("🚀 Generating Bitcoin Beta Report...")
            
            response = requests.post(f"{self.base_url}/api/bitcoin-beta/generate")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Bitcoin Beta Report generated successfully!")
                logger.info(f"   Report path: {data.get('report_path')}")
                logger.info(f"   File size: {data.get('file_size_kb', 0):.1f} KB")
                logger.info(f"   Generated at: {data.get('timestamp')}")
                
                return data.get('report_path')
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                logger.error(f"❌ Report generation failed: {error_data.get('detail', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error generating report: {str(e)}")
            return None
            
    async def demo_workflow(self):
        """Run the complete demo workflow."""
        logger.info("🔍 Bitcoin Beta Report Integration Demo")
        logger.info("=" * 50)
        
        # Check system status
        logger.info("1. Checking main system status...")
        system_ok = await self.check_system_status()
        
        if not system_ok:
            logger.error("❌ Main system is not available. Please start the main system first.")
            return False
            
        await asyncio.sleep(1)
        
        # Check Bitcoin Beta Report feature
        logger.info("\n2. Checking Bitcoin Beta Report feature...")
        beta_ok = await self.check_beta_report_status()
        
        if not beta_ok:
            logger.error("❌ Bitcoin Beta Report feature is not available.")
            return False
            
        await asyncio.sleep(1)
        
        # Get current symbols
        logger.info("\n3. Getting current symbols...")
        symbols = await self.get_current_symbols()
        
        if not symbols:
            logger.warning("⚠️  No symbols found, but continuing with demo...")
            
        await asyncio.sleep(1)
        
        # Generate report
        logger.info("\n4. Generating Bitcoin Beta Report...")
        report_path = await self.generate_beta_report()
        
        if report_path:
            logger.info("\n✅ Demo completed successfully!")
            logger.info(f"📄 Your Bitcoin Beta Report is ready: {report_path}")
            logger.info("\n📈 The report includes:")
            logger.info("   • Multi-timeframe beta analysis (4H, 30M, 5M, 1M)")
            logger.info("   • Normalized price performance charts")
            logger.info("   • Beta comparison across timeframes")
            logger.info("   • Correlation heatmap")
            logger.info("   • Statistical measures for traders")
            logger.info("   • Key trading insights")
            
            logger.info("\n🔄 For automated reports:")
            logger.info("   • Reports will be generated every 6 hours at:")
            logger.info("     00:00, 06:00, 12:00, 18:00 UTC")
            logger.info("   • Integration with your alert system available")
            
            return True
        else:
            logger.error("\n❌ Demo failed during report generation")
            return False

async def main():
    """Run the demo."""
    demo = BitcoinBetaDemo()
    
    try:
        success = await demo.demo_workflow()
        if success:
            print("\n🎉 Demo completed successfully!")
            print("The Bitcoin Beta Report is now ready for production use.")
        else:
            print("\n⚠️  Demo encountered issues. Check the logs above.")
            
    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {str(e)}")

def run_demo():
    """Synchronous wrapper for the demo."""
    print("🚀 Bitcoin Beta Report Integration Demo")
    print("This demo will test the Bitcoin Beta Report with your live system")
    print("Make sure your main Virtuoso system is running first!")
    print()
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error running demo: {str(e)}")

if __name__ == "__main__":
    run_demo() 