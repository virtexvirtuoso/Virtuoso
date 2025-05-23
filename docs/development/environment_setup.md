# Environment Setup Guide

This guide explains how to set up your environment for running the trading system.

## API Credentials

The trading system uses environment variables to manage API credentials securely. This avoids hardcoding sensitive information in configuration files.

### Setting Up Environment Variables

There are two main ways to set up your API credentials:

#### 1. Using a .env File (Recommended)

1. Copy the sample .env file from the template:

   ```bash
   cp config/env/.env.example config/env/.env
   ```

2. Edit the .env file and add your actual API credentials:

   ```bash
   # config/env/.env
   BYBIT_API_KEY=your_actual_api_key
   BYBIT_API_SECRET=your_actual_api_secret
   ```

3. The configuration manager will automatically load these variables when the application starts.

#### 2. Setting Environment Variables Directly

You can also set the environment variables directly in your shell:

```bash
export BYBIT_API_KEY=your_actual_api_key
export BYBIT_API_SECRET=your_actual_api_secret
```

For persistent configuration, add these lines to your shell profile (e.g., `~/.bash_profile`, `~/.zshrc`).

## Switching Between Demo and Production

The trading system can operate in either demo or production mode. To switch:

1. For demo mode, use:
   ```json
   "endpoint": "https://api-demo.bybit.com"
   ```

2. For production mode, use:
   ```json
   "endpoint": "https://api.bybit.com"
   ```

### Important Notes

- **Never commit your actual API credentials** to version control
- Using environment variables helps keep your credentials secure
- The demo environment is recommended for testing before going live
- In production, secure your .env files appropriately (limited permissions)

## Verifying Your Setup

You can verify that your environment variables are loaded correctly by running:

```bash
python tests/config/test_env_loading.py
```

This will check if all the required environment variables are properly set. 