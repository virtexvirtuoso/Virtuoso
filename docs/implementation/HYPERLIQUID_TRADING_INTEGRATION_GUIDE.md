# Hyperliquid Trading Integration Implementation Guide

## Overview

This guide details the complete implementation for integrating Hyperliquid trading capabilities into the existing Virtuoso trading system. The integration enables automatic trade execution on Hyperliquid when confluence signals are generated.

## Current System Architecture

### Signal Generation Flow
1. **Market Monitor** (`src/monitoring/monitor.py`) - Continuous market analysis
2. **Confluence Analyzer** (`src/core/analysis/confluence.py`) - Multi-dimensional scoring
3. **Signal Generator** (`src/signal_generation/signal_generator.py`) - Buy/sell signal generation
4. **Trade Executor** (`src/trade_execution/trade_executor.py`) - Trade execution with risk management

### Existing Exchange Support
- **Primary**: Bybit (fully implemented)
- **Hyperliquid**: Market data only (needs trading enhancement)

## Implementation Plan

### Phase 1: Core Trading Infrastructure

#### 1.1 Enhanced Hyperliquid Exchange Class

**File**: `src/core/exchanges/hyperliquid.py`

**Enhancements Needed**:

```python
import hmac
import hashlib
import time
from eth_account import Account
from eth_utils import to_hex
import json

class HyperliquidExchange(BaseExchange):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.base_url = "https://api.hyperliquid.xyz"
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        
        # Trading credentials
        self.private_key = config.get('private_key')
        self.vault_address = config.get('vault_address')  # Optional for subaccounts
        
        # Initialize account from private key
        if self.private_key:
            self.account = Account.from_key(self.private_key)
            self.wallet_address = self.account.address
        
        # Trading state
        self.nonce = int(time.time() * 1000)
        self.universe = {}  # Asset universe mapping
        
    def _get_nonce(self) -> int:
        """Generate timestamp-based nonce"""
        self.nonce = max(self.nonce + 1, int(time.time() * 1000))
        return self.nonce
    
    def _sign_l1_action(self, action: Dict) -> Dict:
        """Sign action for L1 transaction"""
        # Construct message for signing
        message = {
            "action": action,
            "nonce": self._get_nonce(),
            "signature": None
        }
        
        if self.vault_address:
            message["vaultAddress"] = self.vault_address
            
        # Create signature
        message_hash = self._hash_action(message)
        signature = self.account.sign_message_hash(message_hash)
        
        message["signature"] = {
            "r": to_hex(signature.r),
            "s": to_hex(signature.s), 
            "v": signature.v
        }
        
        return message
    
    def _hash_action(self, message: Dict) -> bytes:
        """Hash action for signing"""
        # Implement Hyperliquid's message hashing
        # This needs to follow their exact specification
        action_json = json.dumps(message["action"], separators=(',', ':'), sort_keys=True)
        
        # Create EIP-712 style hash
        domain_separator = self._get_domain_separator()
        type_hash = self._get_type_hash()
        
        # Combine according to EIP-712
        encoded = hashlib.keccak(
            b'\x19\x01' + domain_separator + 
            hashlib.keccak(type_hash + action_json.encode()).digest()
        ).digest()
        
        return encoded
    
    async def create_order(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create order on Hyperliquid"""
        
        # Get asset index from universe
        coin = symbol.split('-')[0]
        if coin not in self.universe:
            await self._load_universe()
            
        asset_index = self.universe[coin]['index']
        
        # Prepare order action
        order_action = {
            "type": "order",
            "orders": [{
                "a": asset_index,  # Asset index
                "b": side == "buy",  # True for buy, False for sell
                "p": str(price) if price else "0",  # Price (0 for market orders)
                "s": str(amount),  # Size
                "r": params.get("reduceOnly", False),
                "t": self._get_order_type(type, params)
            }]
        }
        
        # Add optional parameters
        if params:
            if "timeInForce" in params:
                order_action["orders"][0]["f"] = params["timeInForce"]
            if "postOnly" in params:
                order_action["orders"][0]["o"] = params["postOnly"]
                
        # Sign and send
        signed_action = self._sign_l1_action(order_action)
        
        response = await self._post_request("/exchange", signed_action)
        
        if response.get("status") == "ok":
            return {
                "id": response["response"]["data"]["statuses"][0]["resting"]["oid"],
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "type": type,
                "status": "open"
            }
        else:
            raise Exception(f"Order failed: {response}")
    
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel order"""
        coin = symbol.split('-')[0]
        asset_index = self.universe[coin]['index']
        
        cancel_action = {
            "type": "cancel",
            "cancels": [{
                "a": asset_index,
                "o": int(order_id)
            }]
        }
        
        signed_action = self._sign_l1_action(cancel_action)
        response = await self._post_request("/exchange", signed_action)
        
        return {"success": response.get("status") == "ok"}
    
    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance"""
        request = {
            "type": "clearinghouseState",
            "user": self.wallet_address
        }
        
        response = await self._post_request("/info", request)
        
        if response:
            balances = {}
            # Parse balance response
            for balance in response.get("balances", []):
                coin = balance["coin"]
                balances[coin] = {
                    "free": float(balance["hold"]),
                    "used": float(balance["total"]) - float(balance["hold"]),
                    "total": float(balance["total"])
                }
            return balances
        
        return {}
    
    async def fetch_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch open positions"""
        request = {
            "type": "clearinghouseState", 
            "user": self.wallet_address
        }
        
        response = await self._post_request("/info", request)
        
        positions = []
        if response and "assetPositions" in response:
            for pos in response["assetPositions"]:
                if pos["position"]["szi"] != "0":  # Non-zero position
                    coin = self._get_coin_from_index(pos["position"]["coin"])
                    if symbol is None or symbol.startswith(coin):
                        positions.append({
                            "symbol": f"{coin}-PERP",
                            "side": "long" if float(pos["position"]["szi"]) > 0 else "short",
                            "size": abs(float(pos["position"]["szi"])),
                            "entryPrice": float(pos["position"]["entryPx"]),
                            "unrealizedPnl": float(pos["unrealizedPnl"]),
                            "percentage": float(pos["returnOnEquity"]) * 100
                        })
        
        return positions
    
    async def modify_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Modify position leverage"""
        coin = symbol.split('-')[0]
        asset_index = self.universe[coin]['index']
        
        leverage_action = {
            "type": "updateLeverage",
            "asset": asset_index,
            "isCross": True,  # Use cross margin
            "leverage": leverage
        }
        
        signed_action = self._sign_l1_action(leverage_action)
        response = await self._post_request("/exchange", signed_action)
        
        return {"success": response.get("status") == "ok"}
    
    async def _load_universe(self):
        """Load asset universe mapping"""
        response = await self._post_request("/info", {"type": "meta"})
        if response and "universe" in response:
            for i, asset in enumerate(response["universe"]):
                self.universe[asset["name"]] = {
                    "index": i,
                    "name": asset["name"],
                    "szDecimals": asset["szDecimals"]
                }
```

#### 1.2 Authentication & Security

**Environment Variables to Add**:
```bash
# Hyperliquid Trading Credentials
HYPERLIQUID_PRIVATE_KEY=your_private_key_here
HYPERLIQUID_VAULT_ADDRESS=optional_vault_address
HYPERLIQUID_TESTNET=true  # Set to false for mainnet
```

**Security Considerations**:
- Private keys stored securely in environment variables
- Nonce management to prevent replay attacks
- Proper EIP-712 message signing
- Optional vault/subaccount support

#### 1.3 Configuration Updates

**File**: `config/config.yaml`

**Add Hyperliquid Section**:
```yaml
exchanges:
  # ... existing exchanges ...
  
  hyperliquid:
    enabled: true
    primary: false  # Set to true to make primary exchange
    testnet: ${HYPERLIQUID_TESTNET:true}
    api_credentials:
      private_key: ${HYPERLIQUID_PRIVATE_KEY}
      vault_address: ${HYPERLIQUID_VAULT_ADDRESS:}
    rest_endpoint: https://api.hyperliquid.xyz
    testnet_endpoint: https://api.hyperliquid-testnet.xyz
    websocket:
      enabled: true
      public: wss://api.hyperliquid.xyz/ws
      testnet_public: wss://api.hyperliquid-testnet.xyz/ws
      channels:
        - ticker
        - trades
        - orderbook
        - userEvents
      reconnect_attempts: 3
      ping_interval: 30
    rate_limits:
      requests_per_second: 10
      requests_per_minute: 1200
    trading:
      default_leverage: 1
      max_leverage: 50
      order_types:
        - market
        - limit
        - trigger
        - twap
      post_only: false
      reduce_only: false
    market_types:
      - perpetual
    data_preferences:
      min_24h_volume: 100000
      preferred_quote_currencies:
        - USD
```

### Phase 2: Trading Integration

#### 2.1 Extended Trade Executor

**File**: `src/trade_execution/trade_executor.py`

**Key Enhancements**:

```python
class TradeExecutor:
    def __init__(self, config: Dict[str, Any], alert_manager: Optional['AlertManager'] = None):
        # ... existing initialization ...
        
        # Multi-exchange support
        self.exchanges = {}
        self.primary_exchange = None
        self.exchange_preferences = config.get('trading', {}).get('exchange_preferences', {})
        
        # Initialize exchanges
        self._initialize_exchanges(config)
    
    def _initialize_exchanges(self, config: Dict[str, Any]):
        """Initialize all enabled exchanges"""
        exchange_configs = config.get('exchanges', {})
        
        for exchange_name, exchange_config in exchange_configs.items():
            if exchange_config.get('enabled', False):
                if exchange_name == 'bybit':
                    # Existing Bybit initialization
                    self.exchanges['bybit'] = self._init_bybit(exchange_config)
                elif exchange_name == 'hyperliquid':
                    # New Hyperliquid initialization
                    self.exchanges['hyperliquid'] = self._init_hyperliquid(exchange_config)
                
                # Set primary exchange
                if exchange_config.get('primary', False):
                    self.primary_exchange = exchange_name
    
    def _init_hyperliquid(self, config: Dict[str, Any]) -> 'HyperliquidExchange':
        """Initialize Hyperliquid exchange"""
        from src.core.exchanges.hyperliquid import HyperliquidExchange
        
        exchange = HyperliquidExchange(config)
        return exchange
    
    async def execute_trade_multi_exchange(
        self,
        symbol: str,
        side: str,
        quantity: float,
        exchange_preference: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute trade with exchange selection logic"""
        
        # Determine target exchange
        target_exchange = self._select_exchange(symbol, side, quantity, exchange_preference)
        
        if target_exchange == 'hyperliquid':
            return await self._execute_hyperliquid_trade(symbol, side, quantity, **kwargs)
        elif target_exchange == 'bybit':
            return await self.execute_trade(symbol, side, quantity, **kwargs)  # Existing method
        else:
            raise ValueError(f"Unsupported exchange: {target_exchange}")
    
    def _select_exchange(
        self,
        symbol: str,
        side: str,
        quantity: float,
        preference: Optional[str] = None
    ) -> str:
        """Select optimal exchange for trade execution"""
        
        if preference and preference in self.exchanges:
            return preference
        
        # Exchange selection logic
        selection_criteria = {
            'fees': self._compare_fees(symbol),
            'liquidity': self._compare_liquidity(symbol),
            'latency': self._compare_latency(),
            'reliability': self._get_reliability_scores()
        }
        
        # Simple scoring system
        scores = {}
        for exchange in self.exchanges.keys():
            scores[exchange] = (
                selection_criteria['fees'].get(exchange, 0) * 0.3 +
                selection_criteria['liquidity'].get(exchange, 0) * 0.4 +
                selection_criteria['latency'].get(exchange, 0) * 0.2 +
                selection_criteria['reliability'].get(exchange, 0) * 0.1
            )
        
        # Return highest scoring exchange
        return max(scores.items(), key=lambda x: x[1])[0]
    
    async def _execute_hyperliquid_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        confluence_score: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute trade on Hyperliquid"""
        
        try:
            hyperliquid = self.exchanges['hyperliquid']
            
            # Get current market price
            ticker = await hyperliquid.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Create market order
            order_result = await hyperliquid.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=quantity,
                params={
                    'postOnly': False,
                    'reduceOnly': False
                }
            )
            
            if order_result:
                # Set stop loss if specified
                if stop_loss_pct:
                    await self._set_hyperliquid_stop_loss(
                        symbol, side, current_price, stop_loss_pct, quantity
                    )
                
                # Set take profit if specified  
                if take_profit_pct:
                    await self._set_hyperliquid_take_profit(
                        symbol, side, current_price, take_profit_pct, quantity
                    )
                
                # Send alert
                await self._send_trade_alert(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=current_price,
                    exchange="Hyperliquid",
                    order_id=order_result['id'],
                    confluence_score=confluence_score
                )
                
                return {
                    'success': True,
                    'exchange': 'hyperliquid',
                    'order_id': order_result['id'],
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': current_price
                }
            
        except Exception as e:
            logger.error(f"Hyperliquid trade execution failed: {str(e)}")
            return {'success': False, 'error': str(e), 'exchange': 'hyperliquid'}
```

#### 2.2 Signal Routing Logic

**Exchange Selection Criteria**:

1. **Fee Optimization**: Compare maker/taker fees
2. **Liquidity Analysis**: Order book depth and spread
3. **Latency Considerations**: Regional proximity and response times
4. **Reliability Scores**: Historical uptime and error rates

**Implementation**:
```python
def _compare_fees(self, symbol: str) -> Dict[str, float]:
    """Compare trading fees across exchanges"""
    return {
        'bybit': 0.001,  # 0.1% taker fee
        'hyperliquid': 0.0002  # 0.02% taker fee (example)
    }

def _compare_liquidity(self, symbol: str) -> Dict[str, float]:
    """Compare liquidity metrics"""
    # Implement real-time liquidity comparison
    # Return normalized scores 0-1
    return {
        'bybit': 0.8,
        'hyperliquid': 0.9
    }
```

#### 2.3 Risk Management Integration

**Position Sizing Across Exchanges**:
```python
def calculate_multi_exchange_position_size(
    self,
    symbol: str,
    side: str,
    total_balance: float,
    confluence_score: float,
    exchange_allocation: Dict[str, float]
) -> Dict[str, float]:
    """Calculate position sizes across multiple exchanges"""
    
    base_position = total_balance * self.max_position_size
    
    # Scale based on confluence score
    scaled_position = self._scale_position_by_score(base_position, confluence_score, side)
    
    # Allocate across exchanges
    exchange_positions = {}
    for exchange, allocation_pct in exchange_allocation.items():
        exchange_positions[exchange] = scaled_position * allocation_pct
    
    return exchange_positions
```

### Phase 3: Advanced Features

#### 3.1 Hyperliquid-Specific Features

**Builder Fee Optimization**:
```python
async def optimize_builder_fee(self, symbol: str, side: str, amount: float) -> Dict[str, Any]:
    """Optimize builder fee for better execution"""
    # Implement builder fee calculation
    # Return optimized order parameters
    pass
```

**Advanced Order Types**:
```python
async def create_twap_order(
    self,
    symbol: str,
    side: str,
    amount: float,
    duration_minutes: int
) -> Dict[str, Any]:
    """Create TWAP (Time-Weighted Average Price) order"""
    
    twap_action = {
        "type": "twapOrder",
        "twap": {
            "a": self._get_asset_index(symbol),
            "b": side == "buy",
            "s": str(amount),
            "m": duration_minutes,
            "t": True  # randomize timing
        }
    }
    
    return await self._execute_signed_action(twap_action)
```

#### 3.2 Multi-Exchange Portfolio Management

**Unified Position Tracking**:
```python
async def get_unified_portfolio(self) -> Dict[str, Any]:
    """Get unified view of positions across all exchanges"""
    
    unified_positions = {}
    
    for exchange_name, exchange in self.exchanges.items():
        positions = await exchange.fetch_positions()
        
        for position in positions:
            symbol = position['symbol']
            if symbol not in unified_positions:
                unified_positions[symbol] = {
                    'total_size': 0,
                    'weighted_entry': 0,
                    'exchanges': {}
                }
            
            unified_positions[symbol]['exchanges'][exchange_name] = position
            unified_positions[symbol]['total_size'] += position['size']
    
    return unified_positions
```

#### 3.3 Monitoring & Alerts Integration

**Enhanced Alert System**:
```python
async def send_hyperliquid_alert(
    self,
    alert_type: str,
    symbol: str,
    data: Dict[str, Any]
) -> None:
    """Send Hyperliquid-specific alerts"""
    
    alert_data = {
        'exchange': 'Hyperliquid',
        'type': alert_type,
        'symbol': symbol,
        'timestamp': time.time(),
        'data': data
    }
    
    await self.alert_manager.send_custom_alert(
        title=f"Hyperliquid {alert_type.title()}",
        message=self._format_hyperliquid_alert(alert_data),
        priority='high' if alert_type in ['error', 'liquidation'] else 'medium'
    )
```

## Testing & Validation

### Integration Testing Script

**File**: `scripts/testing/test_hyperliquid_integration.py`

```python
#!/usr/bin/env python3
"""
Test script for Hyperliquid trading integration
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.exchanges.hyperliquid import HyperliquidExchange
from src.trade_execution.trade_executor import TradeExecutor
import yaml

async def test_hyperliquid_integration():
    """Test complete Hyperliquid integration"""
    
    # Load configuration
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    print("🧪 Testing Hyperliquid Integration")
    print("=" * 50)
    
    # Test 1: Exchange Initialization
    print("1. Testing Exchange Initialization...")
    try:
        hyperliquid = HyperliquidExchange(config['exchanges']['hyperliquid'])
        await hyperliquid.initialize()
        print("✅ Exchange initialized successfully")
    except Exception as e:
        print(f"❌ Exchange initialization failed: {e}")
        return
    
    # Test 2: Market Data
    print("\n2. Testing Market Data...")
    try:
        ticker = await hyperliquid.fetch_ticker('BTC-PERP')
        print(f"✅ Market data: BTC-PERP @ ${ticker['last']}")
    except Exception as e:
        print(f"❌ Market data failed: {e}")
    
    # Test 3: Account Balance
    print("\n3. Testing Account Balance...")
    try:
        balance = await hyperliquid.fetch_balance()
        print(f"✅ Balance fetched: {list(balance.keys())}")
    except Exception as e:
        print(f"❌ Balance fetch failed: {e}")
    
    # Test 4: Simulated Order (if testnet)
    if config['exchanges']['hyperliquid']['testnet']:
        print("\n4. Testing Order Placement (Testnet)...")
        try:
            # Small test order
            order = await hyperliquid.create_order(
                symbol='BTC-PERP',
                type='limit',
                side='buy',
                amount=0.001,
                price=ticker['last'] * 0.9,  # 10% below market
                params={'postOnly': True}
            )
            print(f"✅ Test order placed: {order['id']}")
            
            # Cancel the order
            cancel_result = await hyperliquid.cancel_order(order['id'], 'BTC-PERP')
            print(f"✅ Test order cancelled: {cancel_result['success']}")
            
        except Exception as e:
            print(f"❌ Order test failed: {e}")
    
    # Test 5: Multi-Exchange Trade Executor
    print("\n5. Testing Multi-Exchange Trade Executor...")
    try:
        executor = TradeExecutor(config)
        await executor.initialize()
        
        # Test exchange selection
        selected = executor._select_exchange('BTC-PERP', 'buy', 0.001)
        print(f"✅ Exchange selection: {selected}")
        
    except Exception as e:
        print(f"❌ Trade executor test failed: {e}")
    
    print("\n🎉 Integration testing complete!")

if __name__ == "__main__":
    asyncio.run(test_hyperliquid_integration())
```

## Deployment Checklist

### Pre-Deployment
- [ ] Set up Hyperliquid testnet account
- [ ] Configure environment variables
- [ ] Test authentication and signing
- [ ] Validate order placement on testnet
- [ ] Test WebSocket connections
- [ ] Verify risk management parameters

### Production Deployment
- [ ] Switch to mainnet configuration
- [ ] Set up production API keys
- [ ] Configure exchange allocation percentages
- [ ] Set up monitoring and alerts
- [ ] Test with small position sizes
- [ ] Monitor performance and slippage

### Monitoring
- [ ] Exchange connection health
- [ ] Order execution latency
- [ ] Fee optimization effectiveness
- [ ] Risk management compliance
- [ ] Portfolio balance across exchanges

## Security Considerations

1. **Private Key Management**
   - Store private keys in secure environment variables
   - Use hardware wallets for production
   - Implement key rotation policies

2. **API Security**
   - Rate limiting compliance
   - Proper error handling
   - Request signing validation

3. **Risk Management**
   - Position size limits
   - Maximum daily loss limits
   - Exchange exposure limits
   - Emergency stop mechanisms

## Performance Optimization

1. **Latency Reduction**
   - Connection pooling
   - WebSocket for real-time data
   - Regional API endpoints

2. **Fee Optimization**
   - Dynamic exchange selection
   - Maker vs taker optimization
   - Volume-based fee tiers

3. **Execution Quality**
   - Smart order routing
   - Liquidity optimization
   - Slippage minimization

## Troubleshooting Guide

### Common Issues

1. **Authentication Errors**
   - Verify private key format
   - Check nonce generation
   - Validate signature creation

2. **Order Failures**
   - Check asset universe mapping
   - Verify position sizing
   - Validate order parameters

3. **WebSocket Issues**
   - Monitor connection health
   - Implement reconnection logic
   - Handle rate limiting

### Debugging Tools

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Test specific components
python scripts/testing/test_hyperliquid_auth.py
python scripts/testing/test_hyperliquid_orders.py
python scripts/testing/test_multi_exchange.py
```

## Conclusion

This implementation guide provides a comprehensive framework for integrating Hyperliquid trading into the existing Virtuoso system. The modular approach ensures seamless integration while maintaining the sophisticated signal generation and risk management already in place.

Key benefits:
- **Diversified Execution**: Reduced counterparty risk
- **Optimized Costs**: Dynamic fee optimization
- **Enhanced Liquidity**: Access to multiple venues
- **Advanced Features**: Hyperliquid-specific capabilities

The implementation maintains backward compatibility while extending capabilities for multi-exchange trading strategies.