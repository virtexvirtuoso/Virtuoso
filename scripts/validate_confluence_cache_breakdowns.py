#!/usr/bin/env python3
import asyncio
import json
from typing import List


async def main(symbols: List[str] = None):
    symbols = symbols or [
        'BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','ADAUSDT'
    ]
    try:
        import aiomcache
    except Exception:
        print(json.dumps({'status': 'error', 'error': 'aiomcache not installed'}))
        return

    client = aiomcache.Client('localhost', 11211, pool_size=2)

    results = {}
    ok = 0
    for s in symbols:
        key = f'confluence:breakdown:{s}'
        data = await client.get(key.encode())
        if data:
            try:
                parsed = json.loads(data.decode())
                has_fields = all(k in parsed for k in (
                    'overall_score','components','sentiment','timestamp','symbol'
                ))
                results[s] = {'present': True, 'valid_shape': has_fields}
                if has_fields:
                    ok += 1
            except Exception:
                results[s] = {'present': True, 'valid_shape': False}
        else:
            results[s] = {'present': False, 'valid_shape': False}

    await client.close()
    report = {
        'test': 'validate_confluence_cache_breakdowns',
        'symbols_checked': len(symbols),
        'valid_count': ok,
        'results': results
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    asyncio.run(main())


