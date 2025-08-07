#!/usr/bin/env python3
"""
Diagnose Bybit API issues from logs and live testing.

This script analyzes logs, tests API connectivity, and provides
a comprehensive report of Bybit API issues.
"""

import asyncio
import aiohttp
import json
import time
import re
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BybitDiagnostics:
    """Comprehensive Bybit API diagnostics."""
    
    def __init__(self):
        self.errors = defaultdict(list)
        self.error_patterns = {
            'rate_limit': [
                r'429',
                r'rate.?limit',
                r'too.?many.?requests',
                r'exceeded.?limit',
                r'throttl'
            ],
            'timeout': [
                r'timeout',
                r'timed?.?out',
                r'deadline.?exceeded',
                r'read.?timeout',
                r'connect.?timeout'
            ],
            'connection': [
                r'connection.?refused',
                r'connection.?reset',
                r'connection.?error',
                r'ECONNREFUSED',
                r'ECONNRESET',
                r'socket.?error'
            ],
            'authentication': [
                r'invalid.?api.?key',
                r'authentication.?failed',
                r'unauthorized',
                r'invalid.?signature',
                r'api.?key.?not.?found'
            ],
            'invalid_symbol': [
                r'invalid.?symbol',
                r'symbol.?not.?found',
                r'unknown.?symbol',
                r'contract.?not.?exist'
            ],
            'server_error': [
                r'500',
                r'502',
                r'503',
                r'504',
                r'internal.?server.?error',
                r'service.?unavailable'
            ],
            'network': [
                r'network.?error',
                r'dns.?resolution',
                r'EHOSTUNREACH',
                r'ENETUNREACH',
                r'getaddrinfo.?failed'
            ]
        }
        
        self.log_files = []
        self.api_test_results = {}
        
    async def scan_log_files(self):
        """Scan all log files for Bybit-related errors."""
        logger.info("Scanning log files for Bybit API issues...")
        
        # Find all log files
        log_patterns = [
            'logs/*.log',
            '*.log',
            'logs/**/*.log',
            'tests/**/*.log'
        ]
        
        for pattern in log_patterns:
            for log_file in Path('.').glob(pattern):
                if log_file.is_file():
                    self.log_files.append(log_file)
        
        logger.info(f"Found {len(self.log_files)} log files to analyze")
        
        # Analyze each log file
        for log_file in self.log_files:
            try:
                self._analyze_log_file(log_file)
            except Exception as e:
                logger.error(f"Error analyzing {log_file}: {e}")
        
        return self.errors
    
    def _analyze_log_file(self, log_file: Path):
        """Analyze a single log file for errors."""
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                # Check if line mentions Bybit or exchange
                if any(keyword in line.lower() for keyword in ['bybit', 'exchange', 'api']):
                    # Check for error patterns
                    for error_type, patterns in self.error_patterns.items():
                        for pattern in patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                self.errors[error_type].append({
                                    'file': str(log_file),
                                    'line': line_num,
                                    'content': line.strip(),
                                    'timestamp': self._extract_timestamp(line)
                                })
                                break
        except Exception as e:
            logger.debug(f"Could not read {log_file}: {e}")
    
    def _extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from log line."""
        # Common timestamp patterns
        patterns = [
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            r'\d{2}:\d{2}:\d{2}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group()
        return None
    
    async def test_bybit_endpoints(self):
        """Test various Bybit API endpoints."""
        logger.info("Testing Bybit API endpoints...")
        
        endpoints = {
            'server_time': 'https://api.bybit.com/v5/market/time',
            'symbols': 'https://api.bybit.com/v5/market/instruments-info?category=spot',
            'ticker_btc': 'https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT',
            'orderbook': 'https://api.bybit.com/v5/market/orderbook?category=spot&symbol=BTCUSDT',
            'kline': 'https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=1',
            'trades': 'https://api.bybit.com/v5/market/recent-trade?category=spot&symbol=BTCUSDT'
        }
        
        async with aiohttp.ClientSession() as session:
            for name, url in endpoints.items():
                result = await self._test_endpoint(session, name, url)
                self.api_test_results[name] = result
        
        return self.api_test_results
    
    async def _test_endpoint(self, session: aiohttp.ClientSession, name: str, url: str) -> Dict:
        """Test a single API endpoint."""
        result = {
            'name': name,
            'url': url,
            'status': 'unknown',
            'response_time': None,
            'error': None,
            'rate_limit_info': {}
        }
        
        try:
            start_time = time.time()
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response_time = (time.time() - start_time) * 1000  # ms
                result['response_time'] = round(response_time, 2)
                result['status'] = response.status
                
                # Extract rate limit headers
                headers = response.headers
                rate_limit_headers = {
                    'limit': headers.get('X-Bapi-Limit'),
                    'remaining': headers.get('X-Bapi-Limit-Status'),
                    'reset': headers.get('X-Bapi-Limit-Reset-Timestamp')
                }
                result['rate_limit_info'] = {k: v for k, v in rate_limit_headers.items() if v}
                
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        result['status'] = 'success'
                    else:
                        result['status'] = 'api_error'
                        result['error'] = data.get('retMsg', 'Unknown API error')
                elif response.status == 429:
                    result['status'] = 'rate_limited'
                    result['error'] = 'Rate limit exceeded'
                else:
                    result['status'] = f'http_{response.status}'
                    result['error'] = f'HTTP {response.status}'
                    
        except asyncio.TimeoutError:
            result['status'] = 'timeout'
            result['error'] = 'Request timed out'
        except aiohttp.ClientError as e:
            result['status'] = 'connection_error'
            result['error'] = str(e)
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    async def test_connection_stability(self, duration: int = 30):
        """Test connection stability over time."""
        logger.info(f"Testing connection stability for {duration} seconds...")
        
        url = 'https://api.bybit.com/v5/market/time'
        results = []
        
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < duration:
                try:
                    request_start = time.time()
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        latency = (time.time() - request_start) * 1000
                        results.append({
                            'timestamp': time.time(),
                            'latency': latency,
                            'status': response.status,
                            'success': response.status == 200
                        })
                        request_count += 1
                except Exception as e:
                    results.append({
                        'timestamp': time.time(),
                        'latency': None,
                        'status': None,
                        'success': False,
                        'error': str(e)
                    })
                
                # Wait 1 second between requests
                await asyncio.sleep(1)
        
        # Analyze results
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        latencies = [r['latency'] for r in results if r['latency']]
        
        stability_report = {
            'duration': duration,
            'total_requests': len(results),
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / len(results) * 100) if results else 0,
            'avg_latency': sum(latencies) / len(latencies) if latencies else None,
            'min_latency': min(latencies) if latencies else None,
            'max_latency': max(latencies) if latencies else None,
            'errors': [r.get('error') for r in results if not r['success']]
        }
        
        return stability_report
    
    async def check_rate_limits(self):
        """Check current rate limit status."""
        logger.info("Checking rate limit status...")
        
        url = 'https://api.bybit.com/v5/market/time'
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    headers = response.headers
                    
                    rate_limit_info = {
                        'endpoint': '/v5/market/time',
                        'limit': headers.get('X-Bapi-Limit'),
                        'current_usage': headers.get('X-Bapi-Limit-Status'),
                        'reset_timestamp': headers.get('X-Bapi-Limit-Reset-Timestamp'),
                        'server_time': None
                    }
                    
                    if response.status == 200:
                        data = await response.json()
                        if data.get('retCode') == 0:
                            rate_limit_info['server_time'] = data.get('result', {}).get('timeSecond')
                    
                    return rate_limit_info
                    
            except Exception as e:
                logger.error(f"Failed to check rate limits: {e}")
                return {'error': str(e)}
    
    def analyze_error_patterns(self) -> Dict:
        """Analyze error patterns from logs."""
        analysis = {
            'total_errors': sum(len(errors) for errors in self.errors.values()),
            'error_types': {},
            'most_common_errors': [],
            'time_distribution': defaultdict(int),
            'affected_files': set()
        }
        
        # Count by error type
        for error_type, errors in self.errors.items():
            analysis['error_types'][error_type] = {
                'count': len(errors),
                'percentage': 0
            }
            
            # Track affected files
            for error in errors:
                analysis['affected_files'].add(error['file'])
                
                # Time distribution (hourly)
                if error['timestamp']:
                    try:
                        # Extract hour from timestamp
                        hour = error['timestamp'].split(':')[0][-2:]
                        analysis['time_distribution'][hour] += 1
                    except:
                        pass
        
        # Calculate percentages
        if analysis['total_errors'] > 0:
            for error_type in analysis['error_types']:
                count = analysis['error_types'][error_type]['count']
                analysis['error_types'][error_type]['percentage'] = round(
                    count / analysis['total_errors'] * 100, 2
                )
        
        # Find most common error messages
        all_errors = []
        for errors in self.errors.values():
            all_errors.extend([e['content'] for e in errors])
        
        if all_errors:
            error_counter = Counter(all_errors)
            analysis['most_common_errors'] = error_counter.most_common(5)
        
        analysis['affected_files'] = list(analysis['affected_files'])
        
        return analysis
    
    def generate_report(self) -> str:
        """Generate comprehensive diagnostic report."""
        report = []
        report.append("=" * 80)
        report.append("BYBIT API DIAGNOSTICS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Log Analysis Section
        report.append("📋 LOG ANALYSIS")
        report.append("-" * 40)
        
        if self.errors:
            analysis = self.analyze_error_patterns()
            
            report.append(f"Total Errors Found: {analysis['total_errors']}")
            report.append(f"Log Files Analyzed: {len(self.log_files)}")
            report.append(f"Affected Files: {len(analysis['affected_files'])}")
            report.append("")
            
            report.append("Error Types Distribution:")
            for error_type, info in sorted(
                analysis['error_types'].items(),
                key=lambda x: x[1]['count'],
                reverse=True
            ):
                report.append(f"  • {error_type}: {info['count']} ({info['percentage']}%)")
            
            if analysis['most_common_errors']:
                report.append("")
                report.append("Most Common Errors:")
                for error, count in analysis['most_common_errors']:
                    truncated = error[:100] + "..." if len(error) > 100 else error
                    report.append(f"  • [{count}x] {truncated}")
        else:
            report.append("No Bybit API errors found in logs")
        
        report.append("")
        
        # API Test Results Section
        report.append("🌐 API ENDPOINT TESTS")
        report.append("-" * 40)
        
        if self.api_test_results:
            working = sum(1 for r in self.api_test_results.values() if r['status'] == 'success')
            total = len(self.api_test_results)
            
            report.append(f"Endpoints Tested: {total}")
            report.append(f"Working: {working}/{total} ({working/total*100:.1f}%)")
            report.append("")
            
            for name, result in self.api_test_results.items():
                status_icon = "✅" if result['status'] == 'success' else "❌"
                report.append(f"{status_icon} {name}:")
                report.append(f"   Status: {result['status']}")
                if result['response_time']:
                    report.append(f"   Response Time: {result['response_time']}ms")
                if result['error']:
                    report.append(f"   Error: {result['error']}")
                if result['rate_limit_info']:
                    report.append(f"   Rate Limit: {result['rate_limit_info']}")
        
        report.append("")
        
        # Recommendations Section
        report.append("💡 RECOMMENDATIONS")
        report.append("-" * 40)
        
        recommendations = self._generate_recommendations()
        for i, rec in enumerate(recommendations, 1):
            report.append(f"{i}. {rec}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on findings."""
        recommendations = []
        
        if not self.errors and all(r['status'] == 'success' for r in self.api_test_results.values()):
            recommendations.append("✅ No issues detected - Bybit API is functioning normally")
            return recommendations
        
        # Check for specific error types
        error_types = self.errors.keys()
        
        if 'rate_limit' in error_types:
            recommendations.append(
                "Implement exponential backoff and reduce API call frequency. "
                "Consider caching responses and batching requests."
            )
        
        if 'timeout' in error_types:
            recommendations.append(
                "Increase timeout values and implement retry logic with circuit breakers. "
                "Check network latency to Bybit servers."
            )
        
        if 'connection' in error_types:
            recommendations.append(
                "Check network connectivity and firewall settings. "
                "Implement connection pooling and keep-alive mechanisms."
            )
        
        if 'authentication' in error_types:
            recommendations.append(
                "Verify API keys are correctly configured and have proper permissions. "
                "Check if keys are expired or rate-limited."
            )
        
        if 'server_error' in error_types:
            recommendations.append(
                "Implement fallback mechanisms for Bybit server outages. "
                "Monitor Bybit status page and use alternative data sources when available."
            )
        
        # Check API test results
        if self.api_test_results:
            slow_endpoints = [
                name for name, result in self.api_test_results.items()
                if result['response_time'] and result['response_time'] > 1000
            ]
            if slow_endpoints:
                recommendations.append(
                    f"Optimize or cache slow endpoints: {', '.join(slow_endpoints)}. "
                    "Consider using WebSocket for real-time data."
                )
        
        return recommendations if recommendations else ["Continue monitoring for issues"]


async def main():
    """Main diagnostic execution."""
    print("=" * 80)
    print("🔍 BYBIT API DIAGNOSTICS")
    print("=" * 80)
    print()
    
    diagnostics = BybitDiagnostics()
    
    # Step 1: Scan logs
    print("📋 Scanning log files...")
    await diagnostics.scan_log_files()
    
    # Step 2: Test API endpoints
    print("🌐 Testing API endpoints...")
    await diagnostics.test_bybit_endpoints()
    
    # Step 3: Check rate limits
    print("⚡ Checking rate limits...")
    rate_limits = await diagnostics.check_rate_limits()
    
    # Step 4: Test connection stability
    print("📊 Testing connection stability (30 seconds)...")
    stability = await diagnostics.test_connection_stability(duration=30)
    
    # Generate and save report
    report = diagnostics.generate_report()
    
    # Add stability report
    report += "\n\n📊 CONNECTION STABILITY TEST\n"
    report += "-" * 40 + "\n"
    report += f"Duration: {stability['duration']}s\n"
    report += f"Success Rate: {stability['success_rate']:.1f}%\n"
    report += f"Avg Latency: {stability['avg_latency']:.2f}ms\n" if stability['avg_latency'] else ""
    report += f"Min/Max Latency: {stability['min_latency']:.2f}ms / {stability['max_latency']:.2f}ms\n" if stability['min_latency'] else ""
    
    # Add rate limit info
    report += "\n\n⚡ RATE LIMIT STATUS\n"
    report += "-" * 40 + "\n"
    if 'error' in rate_limits:
        report += f"Error: {rate_limits['error']}\n"
    else:
        for key, value in rate_limits.items():
            if value:
                report += f"{key}: {value}\n"
    
    # Save report
    report_path = Path("logs/bybit_diagnostics_report.txt")
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    print("\n" + report)
    print(f"\n✅ Report saved to: {report_path}")
    
    # Quick summary
    print("\n" + "=" * 80)
    print("📈 QUICK SUMMARY")
    print("-" * 40)
    
    if diagnostics.errors:
        total_errors = sum(len(errors) for errors in diagnostics.errors.values())
        print(f"⚠️ Found {total_errors} errors in logs")
        
        # Most common error type
        if diagnostics.errors:
            most_common = max(diagnostics.errors.items(), key=lambda x: len(x[1]))
            print(f"   Most common: {most_common[0]} ({len(most_common[1])} occurrences)")
    else:
        print("✅ No errors found in logs")
    
    # API health
    if diagnostics.api_test_results:
        working = sum(1 for r in diagnostics.api_test_results.values() if r['status'] == 'success')
        total = len(diagnostics.api_test_results)
        print(f"{'✅' if working == total else '⚠️'} API Health: {working}/{total} endpoints working")
    
    print(f"📊 Connection Stability: {stability['success_rate']:.1f}% success rate")
    
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())