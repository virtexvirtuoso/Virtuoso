#!/usr/bin/env python3
"""
Test Chain-of-Command Protocol Implementation
Tests agent handoffs and coordination using the structured protocol
"""

import json
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import argparse
import re

class AgentChainExecutor:
    def __init__(self, verbose: bool = False):
        self.chain_history = []
        self.max_chain_depth = 10
        self.verbose = verbose
        self.start_time = datetime.now()
        
    def extract_json_from_response(self, text: str) -> Optional[Dict]:
        """Extract JSON protocol response from agent output"""
        # Look for JSON blocks in the response
        json_patterns = [
            r'```json\n(.*?)\n```',  # JSON in code blocks
            r'\{[^{}]*"status"[^{}]*\}',  # Simple JSON object with status
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                try:
                    # Take the last match (most likely the protocol response)
                    json_str = matches[-1]
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def execute_agent(self, agent_name: str, task: str, context: Dict = None) -> Dict:
        """Execute an agent with Chain-of-Command protocol"""
        
        # Build the prompt
        prompt = f"Use the {agent_name} agent to complete this task:\n\n"
        prompt += f"Task: {task}\n\n"
        
        if context:
            prompt += f"Context from previous agent:\n```json\n{json.dumps(context, indent=2)}\n```\n\n"
        
        prompt += "Follow the Chain-of-Command protocol and return a JSON response with your results."
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Executing: {agent_name}")
            print(f"Task: {task[:100]}...")
            if context:
                print(f"Context keys: {list(context.keys())}")
        
        # Execute via Claude CLI (mock for testing)
        # In production, this would call: claude -p "{prompt}"
        
        # For testing, simulate agent responses
        simulated_response = self.simulate_agent_response(agent_name, task, context)
        
        return simulated_response
    
    def simulate_agent_response(self, agent_name: str, task: str, context: Dict = None) -> Dict:
        """Simulate agent responses for testing without Claude CLI"""
        
        # Simulated responses based on agent type
        responses = {
            "python-trading-expert": {
                "status": "needs_help",
                "result": "Implemented Bybit WebSocket connection for BTC/USDT with 30-second candle aggregation. Core trading logic complete.",
                "next_agent": "api-expert",
                "context_forward": {
                    "exchange": "bybit",
                    "symbols": ["BTC/USDT", "ETH/USDT"],
                    "rate_limit": "100/min",
                    "connections": 5
                },
                "confidence": 0.85,
                "reasoning": "Need API rate limiting for multiple connections"
            },
            "api-expert": {
                "status": "needs_help",
                "result": "Configured sliding window rate limiter: 100 req/min per connection. Added connection pooling.",
                "next_agent": "cache-implementation-reviewer",
                "context_forward": {
                    "cache_needed": "market_data",
                    "expected_qps": 50,
                    "data_size": "~100KB per symbol"
                },
                "confidence": 0.9,
                "reasoning": "Performance optimization needed for high-frequency data"
            },
            "cache-implementation-reviewer": {
                "status": "needs_help",
                "result": "Implemented 2-tier cache: Memcached (30s TTL) for hot data, Redis (5min) for warm. Hit ratio: 92%.",
                "next_agent": "trading-logic-validator",
                "context_forward": {
                    "position_sizing": "kelly_criterion",
                    "max_risk": 0.02,
                    "calculations_to_validate": ["sharpe", "sortino", "max_drawdown"]
                },
                "confidence": 0.88,
                "reasoning": "Risk calculations need mathematical validation"
            },
            "trading-logic-validator": {
                "status": "complete",
                "result": "All calculations validated. Kelly Criterion correctly capped at 2%. Sharpe ratio annualized. Risk metrics accurate.",
                "next_agent": None,
                "context_forward": {},
                "confidence": 0.98,
                "reasoning": "Trading system fully implemented and validated"
            },
            "webhook-expert": {
                "status": "complete",
                "result": "Webhook system configured with HMAC-SHA256, exponential backoff, and Discord integration.",
                "next_agent": None,
                "context_forward": {},
                "confidence": 0.95,
                "reasoning": "Webhook system operational"
            }
        }
        
        # Return appropriate response or default
        return responses.get(agent_name, {
            "status": "complete",
            "result": f"Task completed by {agent_name}",
            "next_agent": None,
            "context_forward": {},
            "confidence": 0.9,
            "reasoning": "Task within agent's expertise"
        })
    
    def run_chain(self, initial_agent: str, task: str) -> None:
        """Execute a chain of agents following the protocol"""
        
        print(f"\n{'='*60}")
        print(f"Starting Agent Chain Execution")
        print(f"Initial Agent: {initial_agent}")
        print(f"Task: {task}")
        print(f"{'='*60}")
        
        current_agent = initial_agent
        current_task = task
        context = {}
        depth = 0
        
        while current_agent and depth < self.max_chain_depth:
            # Execute current agent
            response = self.execute_agent(current_agent, current_task, context)
            
            # Store in history
            self.chain_history.append({
                "depth": depth,
                "agent": current_agent,
                "status": response.get("status", "unknown"),
                "confidence": response.get("confidence", 0),
                "result_preview": response.get("result", "")[:100] + "..." 
                    if len(response.get("result", "")) > 100 else response.get("result", "")
            })
            
            # Display progress
            self.display_step(depth, current_agent, response)
            
            # Check for next agent
            next_agent = response.get("next_agent")
            if next_agent:
                context = response.get("context_forward", {})
                current_agent = next_agent
                current_task = "Continue the workflow with the provided context"
                depth += 1
                time.sleep(0.5)  # Small delay for readability
            else:
                current_agent = None
        
        # Display summary
        self.display_summary()
    
    def display_step(self, depth: int, agent: str, response: Dict):
        """Display current step in the chain"""
        indent = "  " * depth
        status_emoji = {
            "success": "✅",
            "needs_help": "🔄",
            "blocked": "🚫",
            "complete": "✨"
        }.get(response.get("status"), "❓")
        
        print(f"\n{indent}[Step {depth + 1}] {agent}")
        print(f"{indent}{status_emoji} Status: {response.get('status', 'unknown')}")
        print(f"{indent}📊 Confidence: {response.get('confidence', 0):.0%}")
        
        if response.get("next_agent"):
            print(f"{indent}➡️  Next: {response.get('next_agent')}")
            print(f"{indent}💭 Reason: {response.get('reasoning', 'N/A')}")
    
    def display_summary(self):
        """Display execution summary"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n{'='*60}")
        print(f"Chain Execution Summary")
        print(f"{'='*60}")
        print(f"Total Steps: {len(self.chain_history)}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"\nExecution Path:")
        
        for i, step in enumerate(self.chain_history):
            arrow = "→" if i < len(self.chain_history) - 1 else "✓"
            print(f"  {i+1}. {step['agent']} ({step['status']}) {arrow}")
        
        # Calculate average confidence
        avg_confidence = sum(s['confidence'] for s in self.chain_history) / len(self.chain_history)
        print(f"\nAverage Confidence: {avg_confidence:.0%}")
        
        # Final status
        final_status = self.chain_history[-1]['status'] if self.chain_history else "unknown"
        if final_status == "complete":
            print(f"\n✅ Chain completed successfully!")
        else:
            print(f"\n⚠️  Chain ended with status: {final_status}")

def main():
    parser = argparse.ArgumentParser(description="Test Agent Chain-of-Command Protocol")
    parser.add_argument(
        "--agents",
        type=str,
        help="Comma-separated list of agents to test (e.g., 'python-trading-expert,api-expert')"
    )
    parser.add_argument(
        "--task",
        type=str,
        default="Implement a high-frequency trading strategy with proper rate limiting and caching",
        help="Task to execute"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Create executor
    executor = AgentChainExecutor(verbose=args.verbose)
    
    # Determine starting agent
    if args.agents:
        agents = args.agents.split(",")
        initial_agent = agents[0].strip()
    else:
        initial_agent = "python-trading-expert"
    
    # Run the chain
    try:
        executor.run_chain(initial_agent, args.task)
    except KeyboardInterrupt:
        print("\n\n⚠️  Chain execution interrupted by user")
        executor.display_summary()
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        executor.display_summary()

if __name__ == "__main__":
    main()