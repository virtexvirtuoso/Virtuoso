"""
API routes for Interactive Web Reports
Provides endpoints for generating, accessing, and managing shareable interactive reports.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import FileResponse, HTMLResponse
from typing import Dict, List, Any, Optional
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from src.core.config.config_manager import ConfigManager
from src.core.reporting.interactive_web_report import InteractiveWebReportGenerator

router = APIRouter()
logger = logging.getLogger(__name__)

# Global instances
interactive_generator: Optional[InteractiveWebReportGenerator] = None

def get_interactive_generator() -> InteractiveWebReportGenerator:
    """Get or create the interactive report generator."""
    global interactive_generator
    if interactive_generator is None:
        config_manager = ConfigManager()
        interactive_generator = InteractiveWebReportGenerator(config_manager)
    return interactive_generator

@router.post("/generate")
async def generate_interactive_report(
    report_data: Dict[str, Any],
    report_type: str = "market_intelligence",
    share_settings: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Generate a new interactive web report.
    
    Args:
        report_data: The report data (same structure as PDF reports)
        report_type: Type of report to generate
        share_settings: Sharing configuration
        
    Returns:
        Report metadata including share URL and settings
    """
    try:
        generator = get_interactive_generator()
        result = await generator.generate_interactive_report(
            report_data=report_data,
            report_type=report_type,
            share_settings=share_settings
        )
        
        logger.info(f"Generated interactive report: {result['report_id']}")
        return {
            "status": "success",
            "message": "Interactive report generated successfully",
            **result
        }
        
    except Exception as e:
        logger.error(f"Error generating interactive report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{report_id}")
async def get_interactive_report(report_id: str) -> HTMLResponse:
    """
    Serve an interactive report by ID.
    
    Args:
        report_id: Unique report identifier
        
    Returns:
        HTML content of the interactive report
    """
    try:
        generator = get_interactive_generator()
        
        # Check if report exists and is valid
        if report_id not in generator.active_reports:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Check if report has expired
        metadata = generator.active_reports[report_id]
        expires_at = datetime.fromisoformat(metadata["expires_at"])
        if datetime.now() > expires_at:
            raise HTTPException(status_code=410, detail="Report has expired")
        
        # Update access tracking
        metadata["access_count"] += 1
        metadata["last_accessed"] = datetime.now().isoformat()
        
        # Serve the HTML file
        report_path = generator.reports_dir / f"{report_id}.html"
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report file not found")
        
        with open(report_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving interactive report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{report_id}/data")
async def get_report_data(report_id: str) -> Dict[str, Any]:
    """
    Get fresh data for an interactive report (for real-time updates).
    
    Args:
        report_id: Unique report identifier
        
    Returns:
        Fresh report data
    """
    try:
        generator = get_interactive_generator()
        data = await generator.get_report_data_api(report_id)
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting report data for {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{report_id}/metadata")
async def get_report_metadata(report_id: str) -> Dict[str, Any]:
    """
    Get metadata for an interactive report.
    
    Args:
        report_id: Unique report identifier
        
    Returns:
        Report metadata including access stats and settings
    """
    try:
        generator = get_interactive_generator()
        
        if report_id not in generator.active_reports:
            raise HTTPException(status_code=404, detail="Report not found")
        
        metadata = generator.active_reports[report_id]
        
        return {
            "status": "success",
            "report_id": report_id,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Error getting metadata for {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{report_id}/download")
async def download_report_pdf(report_id: str):
    """
    Download the PDF version of an interactive report.
    
    Args:
        report_id: Unique report identifier
        
    Returns:
        PDF file download
    """
    try:
        generator = get_interactive_generator()
        
        if report_id not in generator.active_reports:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Check if PDF exists (would need to be generated)
        pdf_path = generator.reports_dir / f"{report_id}.pdf"
        
        if not pdf_path.exists():
            # Generate PDF from the same data (implementation would go here)
            raise HTTPException(status_code=404, detail="PDF version not available")
        
        return FileResponse(
            path=str(pdf_path),
            filename=f"virtuoso_report_{report_id}.pdf",
            media_type="application/pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading PDF for {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/{report_id}/ws")
async def websocket_endpoint(websocket: WebSocket, report_id: str):
    """
    WebSocket endpoint for real-time updates to an interactive report.
    
    Args:
        websocket: WebSocket connection
        report_id: Unique report identifier
    """
    await websocket.accept()
    
    try:
        generator = get_interactive_generator()
        
        # Verify report exists
        if report_id not in generator.active_reports:
            await websocket.close(code=4004, reason="Report not found")
            return
        
        logger.info(f"WebSocket connected for report: {report_id}")
        
        # Send initial data
        try:
            initial_data = await generator.get_report_data_api(report_id)
            await websocket.send_json({
                "type": "initial_data",
                "data": initial_data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
        
        # Keep connection alive and send periodic updates
        while True:
            try:
                # Send updated data every 15 seconds
                await asyncio.sleep(15)
                
                fresh_data = await generator.get_report_data_api(report_id)
                await websocket.send_json({
                    "type": "market_data",
                    "data": fresh_data,
                    "timestamp": datetime.now().isoformat()
                })
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for report: {report_id}")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop for {report_id}: {e}")
                await asyncio.sleep(5)  # Wait before retrying
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally for report: {report_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {report_id}: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

@router.delete("/{report_id}")
async def delete_interactive_report(report_id: str) -> Dict[str, str]:
    """
    Delete an interactive report.
    
    Args:
        report_id: Unique report identifier
        
    Returns:
        Deletion confirmation
    """
    try:
        generator = get_interactive_generator()
        
        if report_id not in generator.active_reports:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Remove files
        report_path = generator.reports_dir / f"{report_id}.html"
        metadata_path = generator.reports_dir / f"{report_id}_metadata.json"
        
        if report_path.exists():
            report_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()
        
        # Remove from active reports
        del generator.active_reports[report_id]
        
        logger.info(f"Deleted interactive report: {report_id}")
        
        return {
            "status": "success",
            "message": f"Report {report_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def list_active_reports() -> Dict[str, Any]:
    """
    List all active interactive reports.
    
    Returns:
        List of active reports with metadata
    """
    try:
        generator = get_interactive_generator()
        
        # Clean up expired reports first
        generator.cleanup_expired_reports()
        
        reports = []
        for report_id, metadata in generator.active_reports.items():
            reports.append({
                "report_id": report_id,
                "created_at": metadata["created_at"],
                "expires_at": metadata["expires_at"],
                "report_type": metadata["report_type"],
                "access_count": metadata["access_count"],
                "last_accessed": metadata["last_accessed"]
            })
        
        return {
            "status": "success",
            "total_reports": len(reports),
            "reports": reports
        }
        
    except Exception as e:
        logger.error(f"Error listing active reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup")
async def cleanup_expired_reports() -> Dict[str, Any]:
    """
    Manually trigger cleanup of expired reports.
    
    Returns:
        Cleanup results
    """
    try:
        generator = get_interactive_generator()
        
        before_count = len(generator.active_reports)
        generator.cleanup_expired_reports()
        after_count = len(generator.active_reports)
        
        cleaned_count = before_count - after_count
        
        return {
            "status": "success",
            "message": f"Cleaned up {cleaned_count} expired reports",
            "reports_before": before_count,
            "reports_after": after_count,
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 