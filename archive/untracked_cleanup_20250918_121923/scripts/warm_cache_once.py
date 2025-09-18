import asyncio
import time
from typing import Dict, List


async def fetch_real_data(symbols: List[str]) -> Dict:
    from src.core.exchanges.factory import ExchangeFactory
    import yaml, os
    cfg_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
    cfg_path = os.path.abspath(cfg_path)
    with open(cfg_path, 'r') as f:
        cfg = yaml.safe_load(f)
    bybit_cfg = cfg['exchanges']['bybit']
    ex = await ExchangeFactory.create_exchange('bybit', bybit_cfg)
    data = {"tickers": {}, "movers": {"gainers": [], "losers": []}}
    try:
        # Use only supported symbols from exchange
        supported = []
        try:
            supported_all = list(getattr(ex, 'symbols', []) or [])
            # Prefer USDT-quote markets; include CCXT Bybit linear symbols like 'BTC/USDT:USDT'
            for sym in supported_all:
                if sym.endswith('/USDT') or sym.endswith(':USDT'):
                    supported.append(sym)
        except Exception:
            supported = symbols
        if not supported:
            supported = symbols
        target = supported[: min(25, len(supported))]
        # Bulk fetch if available
        tickers = {}
        if hasattr(ex, 'fetch_tickers'):
            try:
                tickers = await ex.fetch_tickers(target)
            except Exception:
                tickers = {}
        if not tickers:
            # Fallback: per-symbol with best-effort
            for s in target:
                try:
                    tickers[s] = await ex.fetch_ticker(s)
                except Exception:
                    continue
        data["tickers"] = tickers or {}
        # Simple movers from 24h percentage field if present
        changes = []
        for s, t in (tickers or {}).items():
            ch = t.get('percentage') or t.get('change', 0)
            try:
                changes.append({"symbol": s, "change_24h": round(float(ch), 2)})
            except Exception:
                continue
        gainers = sorted([c for c in changes if c['change_24h'] > 0], key=lambda x: x['change_24h'], reverse=True)[:10]
        losers = sorted([c for c in changes if c['change_24h'] < 0], key=lambda x: x['change_24h'])[:10]
        data["movers"] = {"gainers": gainers, "losers": losers, "timestamp": int(time.time())}
    finally:
        try:
            await ex.close()
        except Exception:
            pass
    # Placeholder signals derived from movers (until full pipeline hooked)
    signals = [{
        "symbol": g["symbol"],
        "price": data["tickers"].get(g["symbol"], {}).get('last') or data["tickers"].get(g["symbol"], {}).get('close', 0),
        "change_24h": g["change_24h"],
        "score": max(35, min(90, 50 + g["change_24h"]))
    } for g in data["movers"]["gainers"][:10]]
    return {"tickers": data["tickers"], "signals": signals, "movers": data["movers"]}


async def warm_once() -> Dict:
    from src.api.cache_adapter_direct import cache_adapter
    # Choose a representative symbol universe (15 as per config)
    symbols = [
        'BTC/USDT','ETH/USDT','SOL/USDT','XRP/USDT','ADA/USDT',
        'AVAX/USDT','DOT/USDT','LINK/USDT','MATIC/USDT','DOGE/USDT',
        'OP/USDT','ARB/USDT','NEAR/USDT','ATOM/USDT','FTM/USDT'
    ]
    real = await fetch_real_data(symbols)
    # Normalize keys for cache
    tickers_by_symbol = {}
    for s, t in real['tickers'].items():
        sym = s.replace('/', '')
        tickers_by_symbol[sym] = {
            'price': t.get('last') or t.get('close', 0),
            'change_24h': t.get('percentage', 0),
            'volume': t.get('quoteVolume', t.get('baseVolume', 0)),
            'high': t.get('high', 0),
            'low': t.get('low', 0)
        }
    overview = {
        'total_symbols': len(tickers_by_symbol),
        'trend_strength': 0,
        'volatility': 0,
        'total_volume_24h': sum((x.get('volume') or 0) for x in tickers_by_symbol.values()),
        'timestamp': int(time.time())
    }
    # Seed cache with real data
    await cache_adapter.set('market:tickers', tickers_by_symbol, ttl=60)
    await cache_adapter.set('market:movers', real['movers'], ttl=45)
    await cache_adapter.set('analysis:signals', {'signals': real['signals'], 'timestamp': int(time.time())}, ttl=60)
    await cache_adapter.set('market:overview', overview, ttl=30)
    return {"warmed": True, "symbols": len(tickers_by_symbol), "timestamp": int(time.time())}


if __name__ == "__main__":
    print(asyncio.run(warm_once()))


