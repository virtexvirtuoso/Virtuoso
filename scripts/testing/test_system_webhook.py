import os
import requests
import json
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def send_test_alert(alert_type="general"):
    """Send a test alert to the system webhook.
    
    Args:
        alert_type: Type of alert to send (general, cpu, memory, disk, database, api, network, market_report)
    """
    # Get the system alerts webhook URL from environment
    webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')

    if not webhook_url:
        print("Error: SYSTEM_ALERTS_WEBHOOK_URL not found in .env file")
        return False

    print(f"Using webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
    print(f"Sending test {alert_type} alert...")

    # Alert details based on type
    alert_details = {
        "general": {
            "title": "System Webhook Test",
            "description": "This is a test message sent to verify the system alerts webhook is working correctly.",
            "color": 0xf39c12,  # Orange
            "source": "test",
            "level": "info"
        },
        "cpu": {
            "title": "CPU Usage Alert",
            "description": "CPU usage is high: 95%",
            "color": 0xe74c3c,  # Red
            "source": "system",
            "level": "critical"
        },
        "memory": {
            "title": "Memory Usage Alert",
            "description": "Memory usage is high: 88% (7.1GB/8GB)",
            "color": 0xf39c12,  # Orange
            "source": "system",
            "level": "warning"
        },
        "disk": {
            "title": "Disk Space Alert",
            "description": "Disk usage is high: 92% (18GB free)",
            "color": 0xe74c3c,  # Red
            "source": "system",
            "level": "critical"
        },
        "database": {
            "title": "Database Connection Issue",
            "description": "Failed to connect to InfluxDB: Connection timeout",
            "color": 0xe74c3c,  # Red
            "source": "database",
            "level": "critical"
        },
        "api": {
            "title": "API Connectivity Issue",
            "description": "API communication with bybit is degraded. Success rate: 68.5%",
            "color": 0xf39c12,  # Orange
            "source": "api:bybit",
            "level": "warning"
        },
        "network": {
            "title": "Network Connectivity Issue",
            "description": "Network latency is high: 850ms",
            "color": 0xf39c12,  # Orange
            "source": "network",
            "level": "warning"
        },
        "market_report": {
            "title": "Market Report Generated",
            "description": "Market report generated for June 01, 2025 - 16:01 UTC",
            "color": 0x3498db,  # Blue
            "source": "market_report",
            "level": "info"
        }
    }
    
    # Use general if specified type doesn't exist
    if alert_type not in alert_details:
        alert_type = "general"
    
    details = alert_details[alert_type]
    
    # Create webhook payload
    payload = {
        'username': 'Virtuoso System Monitor',
        'content': f'⚠️ **{alert_type.upper()} ALERT TEST** ⚠️\n{details["description"]}',
        'embeds': [{
            'title': details["title"],
            'color': details["color"],
            'description': details["description"],
            'fields': [
                {
                    'name': 'Test Type',
                    'value': 'Configuration Verification',
                    'inline': True
                },
                {
                    'name': 'Environment',
                    'value': 'development',
                    'inline': True
                },
                {
                    'name': 'Source',
                    'value': details["source"],
                    'inline': True
                },
                {
                    'name': 'Level',
                    'value': details["level"],
                    'inline': True
                }
            ],
            'footer': {
                'text': 'Virtuoso System Monitoring'
            }
        }]
    }

    # Send the webhook request
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        # Check response status
        if response.status_code >= 200 and response.status_code < 300:
            print(f"Success! Webhook delivered (Status: {response.status_code})")
            return True
        else:
            print(f"Error: Webhook failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending webhook: {str(e)}")
        return False

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test system alerts webhook')
    parser.add_argument('--type', choices=['general', 'cpu', 'memory', 'disk', 'database', 'api', 'network', 'market_report'], 
                        default='general', help='Type of alert to test')
    parser.add_argument('--all', action='store_true', help='Test all alert types')
    
    args = parser.parse_args()
    
    if args.all:
        print("Testing all alert types...")
        alert_types = ['general', 'cpu', 'memory', 'disk', 'database', 'api', 'network', 'market_report']
        results = []
        
        for alert_type in alert_types:
            print(f"\n--- Testing {alert_type} alert ---")
            result = send_test_alert(alert_type)
            results.append((alert_type, result))
            
        # Print summary
        print("\n--- Test Summary ---")
        for alert_type, result in results:
            status = "✅ Passed" if result else "❌ Failed"
            print(f"{alert_type}: {status}")
    else:
        send_test_alert(args.type) 