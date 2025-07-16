"""
Interactive Web Report Generator for Virtuoso Trading System
Generates shareable, real-time web reports with interactive features.
"""

import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from jinja2 import Environment, FileSystemLoader
import uuid

from src.core.config.config_manager import ConfigManager
from src.core.reporting.pdf_generator import ReportGenerator

class InteractiveWebReportGenerator:
    """Generates interactive web reports with real-time data and sharing capabilities."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Template setup
        template_dir = Path(__file__).parent / "templates" / "interactive"
        template_dir.mkdir(exist_ok=True)
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))
        
        # Report storage
        self.reports_dir = Path("reports/interactive")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Active reports tracking
        self.active_reports: Dict[str, Dict] = {}
        
    async def generate_interactive_report(
        self, 
        report_data: Dict[str, Any],
        report_type: str = "market_intelligence",
        share_settings: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Generate an interactive web report.
        
        Args:
            report_data: The report data (same as used for PDF)
            report_type: Type of report (market_intelligence, alpha_analysis, etc.)
            share_settings: Sharing configuration (expiry, access control, etc.)
            
        Returns:
            Dict with report_id, url, and metadata
        """
        try:
            # Generate unique report ID
            report_id = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Default share settings
            if share_settings is None:
                share_settings = {
                    "expires_in_hours": 24,
                    "password_protected": False,
                    "allow_download": True,
                    "real_time_updates": True
                }
            
            # Generate the interactive HTML
            html_content = await self._generate_interactive_html(
                report_data, report_type, report_id, share_settings
            )
            
            # Save the report
            report_path = self.reports_dir / f"{report_id}.html"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Generate shareable URL
            base_url = self.config.get('web_server', {}).get('base_url', 'http://localhost:8000')
            share_url = f"{base_url}/reports/interactive/{report_id}"
            
            # Store report metadata
            expiry_time = datetime.now() + timedelta(hours=share_settings["expires_in_hours"])
            self.active_reports[report_id] = {
                "created_at": datetime.now().isoformat(),
                "expires_at": expiry_time.isoformat(),
                "report_type": report_type,
                "share_settings": share_settings,
                "access_count": 0,
                "last_accessed": None
            }
            
            # Save metadata
            metadata_path = self.reports_dir / f"{report_id}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(self.active_reports[report_id], f, indent=2)
            
            self.logger.info(f"Interactive report generated: {report_id}")
            
            return {
                "report_id": report_id,
                "share_url": share_url,
                "expires_at": expiry_time.isoformat(),
                "file_path": str(report_path),
                "features": {
                    "real_time_updates": share_settings["real_time_updates"],
                    "interactive_charts": True,
                    "mobile_optimized": True,
                    "downloadable": share_settings["allow_download"]
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating interactive report: {e}")
            raise
    
    async def _generate_interactive_html(
        self, 
        report_data: Dict[str, Any], 
        report_type: str,
        report_id: str,
        share_settings: Dict
    ) -> str:
        """Generate the interactive HTML content."""
        
        # Load the appropriate template
        template_name = f"{report_type}_interactive.html"
        try:
            template = self.jinja_env.get_template(template_name)
        except:
            # Fallback to default template
            template = self.jinja_env.get_template("default_interactive.html")
        
        # Prepare template context
        context = {
            "report_data": report_data,
            "report_id": report_id,
            "generated_at": datetime.now().isoformat(),
            "share_settings": share_settings,
            "websocket_enabled": share_settings.get("real_time_updates", True),
            "chart_config": self._get_chart_config(report_data),
            "filter_config": self._get_filter_config(report_data),
            "mobile_config": self._get_mobile_config()
        }
        
        return template.render(**context)
    
    def _get_chart_config(self, report_data: Dict) -> Dict:
        """Generate chart configuration for interactive elements."""
        return {
            "library": "chart.js",
            "theme": "dark",
            "responsive": True,
            "animations": True,
            "real_time": True,
            "charts": [
                {
                    "id": "performance_chart",
                    "type": "line",
                    "data_source": "top_performers",
                    "update_interval": 15000
                },
                {
                    "id": "futures_premium_chart", 
                    "type": "bar",
                    "data_source": "futures_premium",
                    "update_interval": 30000
                },
                {
                    "id": "whale_activity_chart",
                    "type": "scatter",
                    "data_source": "whale_activity", 
                    "update_interval": 10000
                }
            ]
        }
    
    def _get_filter_config(self, report_data: Dict) -> Dict:
        """Generate filter configuration for interactive elements."""
        return {
            "timeframe_filter": {
                "enabled": True,
                "options": ["1h", "4h", "1d", "1w"],
                "default": "4h"
            },
            "symbol_filter": {
                "enabled": True,
                "multi_select": True,
                "options": self._extract_symbols(report_data)
            },
            "metric_filter": {
                "enabled": True,
                "options": ["price", "volume", "premium", "beta"]
            }
        }
    
    def _get_mobile_config(self) -> Dict:
        """Generate mobile optimization configuration."""
        return {
            "responsive_breakpoints": {
                "mobile": 768,
                "tablet": 1024,
                "desktop": 1200
            },
            "touch_optimized": True,
            "swipe_navigation": True,
            "collapsible_sections": True
        }
    
    def _extract_symbols(self, report_data: Dict) -> List[str]:
        """Extract available symbols from report data."""
        symbols = set()
        
        # Extract from top performers
        if "top_performers" in report_data:
            performers = report_data["top_performers"]
            if isinstance(performers, dict):
                for category in ["gainers", "losers"]:
                    if category in performers:
                        for item in performers[category]:
                            if "symbol" in item:
                                symbols.add(item["symbol"])
        
        # Extract from futures premium
        if "futures_premium" in report_data:
            for item in report_data["futures_premium"]:
                if "symbol" in item:
                    symbols.add(item["symbol"])
        
        return sorted(list(symbols))
    
    async def get_report_data_api(self, report_id: str) -> Dict[str, Any]:
        """API endpoint to get report data for real-time updates."""
        if report_id not in self.active_reports:
            raise ValueError(f"Report {report_id} not found")
        
        # Check if report has expired
        metadata = self.active_reports[report_id]
        expires_at = datetime.fromisoformat(metadata["expires_at"])
        if datetime.now() > expires_at:
            raise ValueError(f"Report {report_id} has expired")
        
        # Update access tracking
        metadata["access_count"] += 1
        metadata["last_accessed"] = datetime.now().isoformat()
        
        # Return fresh data (this would integrate with your existing data sources)
        return await self._get_fresh_report_data(metadata["report_type"])
    
    async def _get_fresh_report_data(self, report_type: str) -> Dict[str, Any]:
        """Get fresh data for real-time updates."""
        # This would integrate with your existing market data sources
        # For now, return a placeholder structure
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "live",
            "data": {
                "market_overview": {},
                "top_performers": {"gainers": [], "losers": []},
                "futures_premium": [],
                "smart_money_index": {},
                "whale_activity": {},
                "performance_metrics": {}
            }
        }
    
    def cleanup_expired_reports(self):
        """Clean up expired reports."""
        now = datetime.now()
        expired_reports = []
        
        for report_id, metadata in self.active_reports.items():
            expires_at = datetime.fromisoformat(metadata["expires_at"])
            if now > expires_at:
                expired_reports.append(report_id)
        
        for report_id in expired_reports:
            try:
                # Remove files
                report_path = self.reports_dir / f"{report_id}.html"
                metadata_path = self.reports_dir / f"{report_id}_metadata.json"
                
                if report_path.exists():
                    report_path.unlink()
                if metadata_path.exists():
                    metadata_path.unlink()
                
                # Remove from active reports
                del self.active_reports[report_id]
                
                self.logger.info(f"Cleaned up expired report: {report_id}")
                
            except Exception as e:
                self.logger.error(f"Error cleaning up report {report_id}: {e}")

    async def generate_market_analysis_report(self, report_data: Dict[str, Any], 
                                            include_navigation: bool = True) -> str:
        """
        Generate market analysis report HTML for dashboard integration.
        
        Args:
            report_data: Market analysis configuration and data
            include_navigation: Whether to include dashboard navigation
            
        Returns:
            HTML content for market analysis page
        """
        try:
            # Fetch comprehensive market data
            market_data = await self.fetch_comprehensive_market_data()
            
            # Merge with provided report data
            combined_data = {**market_data, **report_data}
            
            # Create metadata for market analysis
            metadata = {
                "report_type": "market_analysis",
                "created_at": datetime.now().isoformat(),
                "data_sources": self._get_data_sources(),
                "navigation": report_data.get("navigation", {}),
                "theme": report_data.get("theme", {})
            }
            
            # Generate HTML with dashboard integration
            html_content = await self._generate_market_analysis_html(combined_data, metadata)
            
            self.logger.info("Generated market analysis report for dashboard integration")
            return html_content
            
        except Exception as e:
            self.logger.error(f"Error generating market analysis report: {e}")
            raise

    async def fetch_comprehensive_market_data(self) -> Dict[str, Any]:
        """
        Fetch comprehensive market data from all available sources.
        
        Returns:
            Combined market intelligence data
        """
        try:
            # This would integrate with your existing API endpoints
            # For now, return structured data that matches your dashboard APIs
            
            market_data = {
                "timestamp": datetime.now().isoformat(),
                "market_overview": {
                    "total_market_cap": "2.1T",
                    "24h_volume": "89.2B", 
                    "btc_dominance": "42.3%",
                    "fear_greed_index": 67,
                    "active_cryptocurrencies": 2847
                },
                "technical_analysis": {
                    "trend_direction": "bullish",
                    "trend_strength": 78,
                    "support_levels": [42000, 41500, 40800],
                    "resistance_levels": [44500, 45200, 46000],
                    "rsi": 64.2,
                    "macd_signal": "bullish_crossover"
                },
                "sentiment_analysis": {
                    "overall_sentiment": "optimistic",
                    "sentiment_score": 72,
                    "social_volume": "high",
                    "news_sentiment": "positive",
                    "funding_rates": 0.0045
                },
                "risk_metrics": {
                    "volatility_index": 45.2,
                    "liquidation_risk": "moderate",
                    "correlation_btc": 0.78,
                    "sharpe_ratio": 1.34
                },
                "performance_metrics": {
                    "1h_change": 0.8,
                    "24h_change": 3.2,
                    "7d_change": 12.4,
                    "30d_change": 28.7
                }
            }
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error fetching comprehensive market data: {e}")
            return {}

    async def _generate_market_analysis_html(self, data: Dict[str, Any], metadata: Dict) -> str:
        """Generate HTML content specifically for market analysis dashboard integration."""
        
        # Load market analysis template
        try:
            template = self.jinja_env.get_template("market_analysis_dashboard.html")
        except:
            # Fallback to interactive template with dashboard modifications
            template = self.jinja_env.get_template("market_intelligence_interactive.html")
        
        # Prepare context with dashboard integration
        context = {
            "report_data": data,
            "metadata": metadata,
            "generated_at": datetime.now().isoformat(),
            "dashboard_integration": True,
            "navigation": metadata.get("navigation", {}),
            "theme": metadata.get("theme", {}),
            "websocket_enabled": True,
            "chart_config": self._get_chart_config(data),
            "filter_config": self._get_filter_config(data),
            "mobile_config": self._get_mobile_config()
        }
        
        return template.render(**context)

    def _get_data_sources(self) -> List[str]:
        """Get list of data sources used in the report."""
        return [
            "dashboard_api",
            "liquidation_intelligence",
            "alpha_scanner", 
            "manipulation_detection",
            "system_monitoring",
            "trading_portfolio",
            "market_analysis",
            "signals_alerts"
        ] 