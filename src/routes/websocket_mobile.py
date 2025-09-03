"""
Enhanced WebSocket Routes for Phase 3 Real-time Mobile Streaming
Provides mobile-optimized WebSocket endpoints with intelligent streaming
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
import json
import logging
from typing import Dict, List, Any, Optional
import time
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/mobile")
async def mobile_websocket_endpoint(websocket: WebSocket):
    """
    Phase 3: Enhanced mobile WebSocket endpoint with real-time streaming
    Features:
    - Auto-subscription to mobile-relevant channels
    - Adaptive update rates based on connection quality
    - Progressive data loading
    - Connection resilience
    """
    client_id = None
    try:
        # Import Phase 3 components
        from src.api.websocket.mobile_stream_manager import mobile_stream_manager, StreamChannel
        
        # Connect client through mobile stream manager
        client_id = await mobile_stream_manager.connect_client(websocket)
        logger.info(f"📱 Mobile WebSocket client {client_id} connected")
        
        # Auto-subscribe mobile clients to relevant channels
        await mobile_stream_manager.subscribe_client(
            client_id=client_id,
            channels=[
                StreamChannel.CONFLUENCE_LIVE.value,
                StreamChannel.MARKET_PULSE.value, 
                StreamChannel.SIGNAL_STREAM.value,
                StreamChannel.DASHBOARD_SYNC.value
            ],
            filters={
                StreamChannel.CONFLUENCE_LIVE.value: {"min_score": 60},  # Only scores > 60%
                StreamChannel.MARKET_PULSE.value: {"severity": ["high", "critical"]},
                StreamChannel.SIGNAL_STREAM.value: {"min_confidence": 0.65}
            }
        )
        
        # Send initial data snapshot
        await _send_initial_mobile_snapshot(client_id)
        
        # Handle incoming messages from client
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle client requests
                await _handle_mobile_client_message(client_id, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from mobile client {client_id}")
                await _send_error_to_client(client_id, "Invalid JSON format")
            except Exception as e:
                logger.error(f"Error handling mobile client message: {e}")
                await _send_error_to_client(client_id, f"Message processing error: {str(e)}")
                
    except WebSocketDisconnect:
        logger.info(f"📱 Mobile client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Mobile WebSocket error: {e}")
    finally:
        if client_id:
            try:
                from src.api.websocket.mobile_stream_manager import mobile_stream_manager
                await mobile_stream_manager.disconnect_client(client_id)
            except Exception as e:
                logger.error(f"Error disconnecting client {client_id}: {e}")

async def _send_initial_mobile_snapshot(client_id: str):
    """Send initial dashboard snapshot to new mobile client"""
    try:
        from src.api.websocket.mobile_stream_manager import mobile_stream_manager
        from src.api.services.mobile_optimization_service import mobile_optimization_service
        
        # Get current mobile data
        mobile_data = await mobile_optimization_service.get_mobile_data_with_performance_tracking()
        
        if mobile_data:
            snapshot = {
                'type': 'initial_snapshot',
                'phase': 3,
                'data': mobile_data,
                'features': {
                    'real_time_streaming': True,
                    'adaptive_updates': True,
                    'progressive_loading': True,
                    'connection_resilience': True
                },
                'timestamp': time.time()
            }
            
            await mobile_stream_manager._send_to_client(client_id, snapshot)
            logger.info(f"📱 Sent initial snapshot to client {client_id}")
        
    except Exception as e:
        logger.error(f"Error sending initial snapshot to {client_id}: {e}")

async def _handle_mobile_client_message(client_id: str, message: Dict[str, Any]):
    """Handle messages from mobile clients"""
    try:
        from src.api.websocket.mobile_stream_manager import mobile_stream_manager, StreamChannel
        
        msg_type = message.get('type')
        
        if msg_type == 'subscribe':
            # Handle subscription changes
            channels = message.get('channels', [])
            filters = message.get('filters', {})
            await mobile_stream_manager.subscribe_client(client_id, channels, filters)
            
            response = {
                'type': 'subscription_updated',
                'channels': channels,
                'filters': filters,
                'timestamp': time.time()
            }
            await mobile_stream_manager._send_to_client(client_id, response)
            
        elif msg_type == 'unsubscribe':
            # Handle unsubscription
            channels = message.get('channels', [])
            if client_id in mobile_stream_manager.clients:
                client = mobile_stream_manager.clients[client_id]
                for channel in channels:
                    client.subscribed_channels.discard(channel)
                    if channel in mobile_stream_manager.channels:
                        mobile_stream_manager.channels[channel].discard(client_id)
            
            response = {
                'type': 'unsubscription_confirmed',
                'channels': channels,
                'timestamp': time.time()
            }
            await mobile_stream_manager._send_to_client(client_id, response)
            
        elif msg_type == 'heartbeat':
            # Update client heartbeat
            if client_id in mobile_stream_manager.clients:
                mobile_stream_manager.clients[client_id].last_heartbeat = time.time()
                
            response = {
                'type': 'heartbeat_ack',
                'server_time': time.time(),
                'client_id': client_id
            }
            await mobile_stream_manager._send_to_client(client_id, response)
            
        elif msg_type == 'request_snapshot':
            # Send current dashboard snapshot
            await _send_dashboard_snapshot(client_id)
            
        elif msg_type == 'set_connection_quality':
            # Client reporting connection quality
            quality = message.get('quality', 'unknown')
            if client_id in mobile_stream_manager.clients:
                mobile_stream_manager.clients[client_id].connection_quality = quality
                logger.info(f"📱 Client {client_id} connection quality: {quality}")
            
        elif msg_type == 'request_progressive_load':
            # Request progressive data loading
            connection_quality = message.get('connection_quality', 'unknown')
            await _handle_progressive_load_request(client_id, connection_quality)
            
        else:
            logger.warning(f"Unknown message type from client {client_id}: {msg_type}")
            
    except Exception as e:
        logger.error(f"Error handling message from client {client_id}: {e}")
        await _send_error_to_client(client_id, f"Message handling error: {str(e)}")

async def _send_dashboard_snapshot(client_id: str):
    """Send current dashboard state to mobile client"""
    try:
        from src.api.websocket.mobile_stream_manager import mobile_stream_manager
        from src.api.services.mobile_optimization_service import mobile_optimization_service
        
        # Get comprehensive dashboard data
        mobile_data = await mobile_optimization_service.get_mobile_data_with_performance_tracking()
        
        if mobile_data:
            snapshot = {
                'type': 'dashboard_snapshot',
                'data': mobile_data,
                'timestamp': time.time(),
                'phase': 3
            }
            
            await mobile_stream_manager._send_to_client(client_id, snapshot)
            logger.debug(f"📱 Sent dashboard snapshot to client {client_id}")
        
    except Exception as e:
        logger.error(f"Error sending dashboard snapshot to {client_id}: {e}")

async def _handle_progressive_load_request(client_id: str, connection_quality: str):
    """Handle progressive loading request"""
    try:
        from src.api.websocket.mobile_stream_manager import mobile_stream_manager
        
        # Simulate progressive loading stages
        stages = [
            {'name': 'critical', 'data': {'system_status': 'healthy', 'btc_price': 45000}},
            {'name': 'primary', 'data': {'top_symbols': ['BTC', 'ETH', 'SOL']}},
            {'name': 'secondary', 'data': {'market_overview': {'regime': 'BULLISH'}}},
        ]
        
        total_stages = len(stages)
        
        for i, stage in enumerate(stages):
            progress_data = {
                'type': 'progressive_update',
                'stage': stage['name'],
                'progress': (i + 1) / total_stages,
                'data': stage['data'],
                'loading_complete': i == total_stages - 1,
                'timestamp': time.time()
            }
            
            await mobile_stream_manager._send_to_client(client_id, progress_data)
            
            # Add delay based on connection quality
            delay_map = {'excellent': 0.1, 'good': 0.2, 'fair': 0.5, 'slow': 1.0, 'poor': 2.0}
            delay = delay_map.get(connection_quality, 0.3)
            await asyncio.sleep(delay)
            
        logger.info(f"📱 Completed progressive loading for client {client_id}")
        
    except Exception as e:
        logger.error(f"Error in progressive loading for client {client_id}: {e}")

async def _send_error_to_client(client_id: str, error_message: str):
    """Send error message to client"""
    try:
        from src.api.websocket.mobile_stream_manager import mobile_stream_manager
        
        error_data = {
            'type': 'error',
            'message': error_message,
            'timestamp': time.time(),
            'client_id': client_id
        }
        
        await mobile_stream_manager._send_to_client(client_id, error_data)
        
    except Exception as e:
        logger.error(f"Error sending error message to client {client_id}: {e}")

# REST endpoints for Phase 3 management
@router.get("/api/phase3/mobile/status")
async def get_mobile_streaming_status():
    """Get mobile streaming status and statistics"""
    try:
        from src.api.websocket.mobile_stream_manager import mobile_stream_manager
        from src.core.streaming.realtime_pipeline import realtime_pipeline
        
        return JSONResponse({
            'phase': 3,
            'status': 'active',
            'features': ['real_time_streaming', 'adaptive_updates', 'progressive_loading', 'connection_resilience'],
            'streaming_manager': mobile_stream_manager.get_statistics(),
            'realtime_pipeline': realtime_pipeline.get_pipeline_stats(),
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting Phase 3 status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/phase3/mobile/clients")
async def get_connected_clients():
    """Get information about connected mobile clients"""
    try:
        from src.api.websocket.mobile_stream_manager import mobile_stream_manager
        
        clients_info = []
        for client_id, client in mobile_stream_manager.clients.items():
            clients_info.append({
                'client_id': client_id,
                'connected_at': client.connected_at,
                'last_heartbeat': client.last_heartbeat,
                'subscribed_channels': list(client.subscribed_channels),
                'connection_quality': client.connection_quality,
                'messages_sent': client.messages_sent,
                'bytes_sent': client.bytes_sent,
                'uptime': time.time() - client.connected_at
            })
        
        return JSONResponse({
            'total_clients': len(clients_info),
            'clients': clients_info,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting client information: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/phase3/mobile/broadcast")
async def broadcast_test_message(message: Dict[str, Any]):
    """Broadcast test message to mobile clients (development only)"""
    try:
        from src.api.websocket.mobile_stream_manager import mobile_stream_manager, StreamChannel, MessageType, Priority
        
        # Extract message parameters
        channel = message.get('channel', StreamChannel.DASHBOARD_SYNC.value)
        data = message.get('data', {'test': 'message', 'timestamp': time.time()})
        msg_type = MessageType.DASHBOARD_SYNC  # Default message type
        priority = Priority.NORMAL
        
        # Broadcast to all clients in channel
        await mobile_stream_manager.broadcast_update(
            channel=channel,
            data=data,
            message_type=msg_type,
            priority=priority
        )
        
        return JSONResponse({
            'status': 'success',
            'message': 'Test message broadcasted',
            'channel': channel,
            'data': data,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error broadcasting test message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/phase3/mobile/channels")
async def get_channel_info():
    """Get information about streaming channels"""
    try:
        from src.api.websocket.mobile_stream_manager import mobile_stream_manager, StreamChannel
        
        channels_info = {}
        for channel_enum in StreamChannel:
            channel_name = channel_enum.value
            subscribers = mobile_stream_manager.channels.get(channel_name, set())
            channels_info[channel_name] = {
                'name': channel_name,
                'description': _get_channel_description(channel_name),
                'subscribers': len(subscribers),
                'subscriber_ids': list(subscribers)
            }
        
        return JSONResponse({
            'total_channels': len(channels_info),
            'channels': channels_info,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting channel information: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_channel_description(channel_name: str) -> str:
    """Get description for a streaming channel"""
    descriptions = {
        'confluence_live': 'Real-time confluence score updates',
        'market_pulse': 'Critical market movements and events',
        'signal_stream': 'New trading signals as they are generated',
        'alert_priority': 'High-priority system and market alerts',
        'dashboard_sync': 'Dashboard state synchronization'
    }
    return descriptions.get(channel_name, 'Unknown channel')