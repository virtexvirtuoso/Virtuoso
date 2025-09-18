#!/usr/bin/env python3
import asyncio
import json


async def main(symbol: str = 'BTCUSDT'):
    # Attempt to locate analyzer via app state or DI-lite paths
    health = {'test': 'validate_analyzer_health', 'symbol': symbol}
    try:
        from src.core.simple_registry import register_core_services
        from src.config.manager import ConfigManager
        config = ConfigManager().to_dict() if hasattr(ConfigManager(), 'to_dict') else {}
        registry = register_core_services(config)
        # Some environments may not put analyzer directly in registry; try monitor
        monitor = registry.get('market_monitor') if hasattr(registry, 'get') else None
        analyzer = None
        mdm = None
        if monitor and hasattr(monitor, 'confluence_analyzer'):
            analyzer = monitor.confluence_analyzer
        if monitor and hasattr(monitor, 'market_data_manager'):
            mdm = monitor.market_data_manager
        if analyzer is None:
            # Fallback: try direct import factory
            from src.core.analysis.confluence import ConfluenceAnalyzer
            analyzer = ConfluenceAnalyzer(config)
        if mdm is None:
            # Minimal market data attempt
            from src.core.exchanges.manager import ExchangeManager
            em = ExchangeManager(config)
            await em.initialize()
            mdm = type('MDM', (), {'get_market_data': lambda self, s: em.fetch_market_data(s)})()

        # Fetch market data and analyze
        data = await mdm.get_market_data(symbol)
        res = await analyzer.analyze(data)
        ok = bool(res and 'confluence_score' in res)
        health.update({
            'ready': ok,
            'confluence_score': res.get('confluence_score', None) if isinstance(res, dict) else None,
            'has_components': isinstance(res, dict) and 'components' in res
        })
    except Exception as e:
        health.update({'ready': False, 'error': str(e)})
    print(json.dumps(health, indent=2))


if __name__ == '__main__':
    asyncio.run(main())


