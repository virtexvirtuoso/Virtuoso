# Agent Communication Protocol (Chain-of-Command)

## Overview
This protocol enables agents to coordinate tasks by returning structured recommendations for the next agent to invoke. The main Claude instance interprets these recommendations and automatically chains agent calls.

## Protocol Structure

All agents MUST return responses in this JSON structure when coordination is needed:

```json
{
  "status": "success|needs_help|blocked|complete",
  "result": "The actual work output or analysis",
  "next_agent": "agent-name-to-invoke|null",
  "context_forward": {
    "key": "value pairs to pass to next agent"
  },
  "confidence": 0.0-1.0,
  "reasoning": "Why this agent is needed next"
}
```

## Field Definitions

- **status**: Current task status
  - `success`: Task completed successfully, may need follow-up
  - `needs_help`: Requires another agent's expertise
  - `blocked`: Cannot proceed without external input
  - `complete`: Entire workflow finished

- **result**: The actual output from this agent's work

- **next_agent**: Name of agent to invoke next (null if complete)
  - Must match exact agent filename without `.md`
  - Examples: `api-expert`, `python-trading-expert`

- **context_forward**: Data to pass to the next agent
  - Include only essential information
  - Avoid token bloat by summarizing when possible

- **confidence**: Float 0.0-1.0 indicating certainty in the recommendation

- **reasoning**: Brief explanation for the handoff decision

## Usage Examples

### Example 1: Simple Handoff
```json
{
  "status": "needs_help",
  "result": "Implemented Bybit WebSocket connection",
  "next_agent": "api-expert",
  "context_forward": {
    "exchange": "bybit",
    "connection_type": "websocket",
    "issue": "rate limiting needed"
  },
  "confidence": 0.95,
  "reasoning": "WebSocket rate limiting requires API expertise"
}
```

### Example 2: Workflow Complete
```json
{
  "status": "complete",
  "result": "Trading strategy fully implemented and validated",
  "next_agent": null,
  "context_forward": {},
  "confidence": 1.0,
  "reasoning": "All components implemented and tested"
}
```

### Example 3: Parallel Recommendations (Advanced)
```json
{
  "status": "needs_help",
  "result": "Core trading logic implemented",
  "next_agent": "trading-logic-validator",
  "parallel_agents": ["cache-implementation-reviewer", "api-expert"],
  "context_forward": {
    "strategy": "momentum_breakout",
    "symbols": ["BTC/USDT", "ETH/USDT"]
  },
  "confidence": 0.85,
  "reasoning": "Need validation while optimizing performance"
}
```

## Agent Handoff Matrix

| From Agent | To Agent | Trigger Condition |
|------------|----------|-------------------|
| python-trading-expert | api-expert | API integration, rate limiting, authentication |
| python-trading-expert | trading-logic-validator | Math validation, risk calculations |
| api-expert | webhook-expert | Webhook setup, callback handling |
| api-expert | cache-implementation-reviewer | Performance optimization needed |
| trading-logic-validator | fintech-ux-designer | UI updates for new features |
| Any Agent | pepe | Complex orchestration needed |

## Implementation Guidelines

1. **Always include protocol response** when task extends beyond single agent scope
2. **Be specific** in context_forward to avoid ambiguity
3. **Chain depth limit**: Maximum 10 agents in sequence
4. **Token management**: Keep context_forward under 500 tokens
5. **Error handling**: Include error details in result when status is "blocked"

## Testing Protocol Compliance

Agents should be tested with:
```bash
# Test single agent protocol response
claude -p "Use python-trading-expert to implement a trading strategy and follow Chain-of-Command protocol"

# Test chain execution
./scripts/test_agent_chaining.py --agents "python-trading-expert,api-expert"
```