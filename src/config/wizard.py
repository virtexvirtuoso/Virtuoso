"""
Minimal configuration wizard stub used by quick_start.sh
Phase 1 target: reduce setup errors and ensure CCXT flag is enabled for Bybit.
"""
from __future__ import annotations

import os
import yaml
from typing import Any, Dict

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'config.yaml')


def run_wizard(non_interactive: bool = False) -> None:
    try:
        with open(CONFIG_PATH, 'r') as f:
            cfg: Dict[str, Any] = yaml.safe_load(f) or {}
    except Exception:
        return

    ex = cfg.setdefault('exchanges', {}).setdefault('bybit', {})
    # Ensure CCXT is enabled as a quick win
    ex['use_ccxt'] = True

    # Ensure API keys exist with empty defaults to avoid KeyError
    creds = ex.setdefault('api_credentials', {})
    creds.setdefault('api_key', os.getenv('BYBIT_API_KEY', ''))
    creds.setdefault('api_secret', os.getenv('BYBIT_API_SECRET', ''))

    with open(CONFIG_PATH, 'w') as f:
        yaml.safe_dump(cfg, f, sort_keys=False)


