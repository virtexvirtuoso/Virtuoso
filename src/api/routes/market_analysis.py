from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from src.core.reporting.interactive_web_report import InteractiveWebReportGenerator
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/market-analysis", response_class=HTMLResponse)
async def market_analysis_page(request: Request):
    """
    Serve the interactive web report as the market analysis page.
    This integrates the comprehensive market intelligence report directly
    into the dashboard navigation system.
    """
    try:
        # Initialize the interactive report generator
        report_generator = InteractiveWebReportGenerator()
        
        # Generate market analysis report with dashboard integration
        report_data = {
            "title": "Virtuoso Market Analysis",
            "subtitle": "Real-Time Market Intelligence & Technical Analysis",
            "navigation": {
                "show_back_to_dashboard": True,
                "dashboard_url": "/",
                "dashboard_title": "Trading Dashboard"
            },
            "theme": {
                "primary_color": "#ffbf00",  # Terminal amber
                "secondary_color": "#0c1a2b", # Navy blue
                "accent_color": "#ff9900"
            }
        }
        
        # Generate the interactive report HTML
        report_html = await report_generator.generate_market_analysis_report(
            report_data=report_data,
            include_navigation=True
        )
        
        logger.info("Market analysis page served successfully")
        return HTMLResponse(content=report_html)
        
    except Exception as e:
        logger.error(f"Error serving market analysis page: {e}")
        raise HTTPException(status_code=500, detail="Failed to load market analysis")

@router.get("/market-analysis/data")
async def market_analysis_data():
    """
    API endpoint for real-time market analysis data updates.
    Used by the interactive report for WebSocket-free updates.
    """
    try:
        report_generator = InteractiveWebReportGenerator()
        
        # Fetch latest market data
        market_data = await report_generator.fetch_comprehensive_market_data()
        
        return {
            "status": "success",
            "data": market_data,
            "timestamp": report_generator._get_current_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Error fetching market analysis data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch market data") 