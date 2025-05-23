# Configuration Structure

This document outlines the configuration structure of the Virtuoso trading system and explains the relationship between different configuration files.

## Configuration Files

The system uses the following configuration files:

- `config/config.yaml`: The main configuration file and single source of truth for core settings
- `config/demo_trading.json`: Trading-specific configuration for the demo environment

## Single Source of Truth for Weights

For consistency and to avoid configuration conflicts, the following guidelines should be followed:

### Confluence Weights

The **confluence component weights** are defined in a single location:

```yaml
# In config/config.yaml
confluence:
  weights:
    components:
      orderbook: 0.2     # Order book analysis weight
      orderflow: 0.25    # Order flow dynamics weight
      price_structure: 0.15  # Price structure weight
      sentiment: 0.1     # Market sentiment indicators weight
      technical: 0.17     # Technical analysis indicators weight
      volume: 0.12       # Volume analysis weight
```

These weights determine how different analysis components contribute to the final confluence score. Having them defined in a single location ensures consistency across the application.

> **Important**: Do not define duplicate confluence weights in other configuration files (like demo_trading.json). Only the weights in config.yaml will be used.

## Configuration Precedence

When a setting appears in multiple configuration files:

1. More specific configurations override general ones
2. Values in trade-specific configurations take precedence
3. Environment variables override file-based configurations

## Environment Variables

Sensitive information like API keys should be stored in environment variables:

- `BYBIT_API_KEY`: Your Bybit API key
- `BYBIT_API_SECRET`: Your Bybit API secret
- `DISCORD_WEBHOOK_URL`: Discord webhook URL for alerts

See `docs/development/environment_setup.md` for details on setting up environment variables. 