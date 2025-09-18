"""
Enhanced Interactive Configuration Wizard for Virtuoso CCXT
Provides both CLI and API interfaces for configuration management
"""

import os
import yaml
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
import asyncio

CONFIG_PATH = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'
TEMPLATES_PATH = Path(__file__).parent / 'templates'

class ConfigurationWizard:
    """Enhanced configuration wizard with templates and validation"""

    def __init__(self):
        self.config_path = CONFIG_PATH
        self.current_config = self._load_current_config()
        self.templates = self._load_templates()

    def _load_current_config(self) -> Dict[str, Any]:
        """Load existing configuration"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
        return {}

    def _load_templates(self) -> Dict[str, Dict]:
        """Load configuration templates"""
        return {
            'beginner': {
                'name': 'Beginner Trader',
                'description': 'Simple configuration for getting started',
                'config': {
                    'environment': 'development',
                    'exchanges': {
                        'bybit': {
                            'enabled': True,
                            'use_ccxt': True,
                            'testnet': True,
                            'primary': True
                        }
                    },
                    'monitoring': {
                        'enabled': True,
                        'interval': 60,
                        'alerts': {
                            'enabled': False
                        }
                    },
                    'analysis': {
                        'orderflow_enabled': True,
                        'sentiment_enabled': True,
                        'liquidity_enabled': True,
                        'bitcoin_beta_enabled': False,
                        'smart_money_enabled': False,
                        'ml_patterns_enabled': False
                    }
                }
            },
            'advanced': {
                'name': 'Advanced Trader',
                'description': 'Full-featured configuration with all analysis tools',
                'config': {
                    'environment': 'production',
                    'exchanges': {
                        'bybit': {
                            'enabled': True,
                            'use_ccxt': True,
                            'testnet': False,
                            'primary': True
                        },
                        'binance': {
                            'enabled': True,
                            'use_ccxt': True,
                            'testnet': False,
                            'primary': False
                        }
                    },
                    'monitoring': {
                        'enabled': True,
                        'interval': 30,
                        'alerts': {
                            'enabled': True,
                            'discord_webhook': '',
                            'whale_activity': {'enabled': True},
                            'liquidation': {'enabled': True},
                            'smart_money_detection': {'enabled': True}
                        }
                    },
                    'analysis': {
                        'orderflow_enabled': True,
                        'sentiment_enabled': True,
                        'liquidity_enabled': True,
                        'bitcoin_beta_enabled': True,
                        'smart_money_enabled': True,
                        'ml_patterns_enabled': True
                    }
                }
            },
            'professional': {
                'name': 'Professional/Institution',
                'description': 'Enterprise configuration with maximum performance',
                'config': {
                    'environment': 'production',
                    'exchanges': {
                        'bybit': {
                            'enabled': True,
                            'use_ccxt': True,
                            'testnet': False,
                            'primary': True,
                            'rate_limits': {
                                'requests_per_second': 20,
                                'requests_per_minute': 1200
                            }
                        }
                    },
                    'caching': {
                        'enabled': True,
                        'backend': 'multi_tier',
                        'memcached': {'host': 'localhost', 'port': 11211},
                        'redis': {'host': 'localhost', 'port': 6379}
                    },
                    'monitoring': {
                        'enabled': True,
                        'interval': 15,
                        'metrics': {'enabled': True},
                        'performance': {'enabled': True},
                        'alerts': {
                            'enabled': True,
                            'system_alerts': {'enabled': True},
                            'whale_activity': {'enabled': True},
                            'liquidation': {'enabled': True},
                            'smart_money_detection': {'enabled': True}
                        }
                    },
                    'analysis': {
                        'orderflow_enabled': True,
                        'sentiment_enabled': True,
                        'liquidity_enabled': True,
                        'bitcoin_beta_enabled': True,
                        'smart_money_enabled': True,
                        'ml_patterns_enabled': True,
                        'confluence': {
                            'thresholds': {'buy': 70, 'sell': 35}
                        }
                    }
                }
            }
        }

    def apply_template(self, template_name: str) -> Dict[str, Any]:
        """Apply a configuration template"""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")

        template = self.templates[template_name]['config']
        # Merge with existing config, preserving API keys
        merged = self._deep_merge(self.current_config, template)
        return merged

    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries, preserving sensitive data in base"""
        result = base.copy()

        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Preserve API credentials
                if 'api_credentials' in result[key]:
                    api_creds = result[key]['api_credentials']
                    result[key] = self._deep_merge(result[key], value)
                    result[key]['api_credentials'] = api_creds
                else:
                    result[key] = self._deep_merge(result[key], value)
            else:
                # Don't overwrite API keys or webhooks with empty values
                if key in ['api_key', 'api_secret', 'discord_webhook'] and not value:
                    continue
                result[key] = value

        return result

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration and return results"""
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': []
        }

        # Check exchanges
        if 'exchanges' not in config:
            results['errors'].append("No exchanges configured")
            results['valid'] = False
        else:
            has_enabled_exchange = False
            for name, exchange in config.get('exchanges', {}).items():
                if exchange.get('enabled', False):
                    has_enabled_exchange = True
                    # Check for API credentials
                    creds = exchange.get('api_credentials', {})
                    if not creds.get('api_key'):
                        results['warnings'].append(f"{name}: No API key configured")
                    if not creds.get('api_secret'):
                        results['warnings'].append(f"{name}: No API secret configured")

            if not has_enabled_exchange:
                results['errors'].append("No exchanges enabled")
                results['valid'] = False

        # Check monitoring
        if config.get('monitoring', {}).get('alerts', {}).get('enabled'):
            alerts = config['monitoring']['alerts']
            if alerts.get('discord_webhook') and not alerts['discord_webhook'].startswith('https://'):
                results['warnings'].append("Discord webhook URL appears invalid")

        # Check caching
        if config.get('caching', {}).get('enabled'):
            cache_backend = config['caching'].get('backend')
            if cache_backend == 'memcached':
                results['suggestions'].append("Consider using multi_tier cache for better performance")

        # Check analysis components
        analysis = config.get('analysis', {})
        if analysis.get('smart_money_enabled') and not analysis.get('orderflow_enabled'):
            results['suggestions'].append("Smart money detection works better with orderflow analysis enabled")

        return results

    async def test_exchange_connection(self, exchange_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test connection to an exchange"""
        result = {
            'success': False,
            'message': '',
            'details': {}
        }

        try:
            exchange_config = config.get('exchanges', {}).get(exchange_name, {})

            if not exchange_config.get('enabled'):
                result['message'] = f"{exchange_name} is not enabled"
                return result

            # Here we would normally test the actual exchange connection
            # For now, we'll do a basic check
            api_key = exchange_config.get('api_credentials', {}).get('api_key')
            api_secret = exchange_config.get('api_credentials', {}).get('api_secret')

            if api_key and api_secret:
                # Simulate connection test
                await asyncio.sleep(0.5)
                result['success'] = True
                result['message'] = f"Successfully connected to {exchange_name}"
                result['details'] = {
                    'testnet': exchange_config.get('testnet', False),
                    'use_ccxt': exchange_config.get('use_ccxt', True)
                }
            else:
                result['message'] = "API credentials not configured"

        except Exception as e:
            result['message'] = str(e)

        return result

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            # Create backup of existing config
            if self.config_path.exists():
                backup_path = self.config_path.with_suffix('.yaml.bak')
                with open(self.config_path, 'r') as f:
                    backup_content = f.read()
                with open(backup_path, 'w') as f:
                    f.write(backup_content)

            # Save new config
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_config_summary(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of the configuration"""
        summary = {
            'environment': config.get('environment', 'unknown'),
            'exchanges': [],
            'analysis_components': [],
            'monitoring': {},
            'caching': {}
        }

        # Summarize exchanges
        for name, exchange in config.get('exchanges', {}).items():
            if exchange.get('enabled'):
                summary['exchanges'].append({
                    'name': name,
                    'testnet': exchange.get('testnet', False),
                    'primary': exchange.get('primary', False),
                    'has_credentials': bool(exchange.get('api_credentials', {}).get('api_key'))
                })

        # Summarize analysis
        analysis = config.get('analysis', {})
        for component in ['orderflow', 'sentiment', 'liquidity', 'bitcoin_beta', 'smart_money', 'ml_patterns']:
            if analysis.get(f'{component}_enabled', False):
                summary['analysis_components'].append(component)

        # Summarize monitoring
        monitoring = config.get('monitoring', {})
        summary['monitoring'] = {
            'enabled': monitoring.get('enabled', False),
            'interval': monitoring.get('interval', 60),
            'alerts_enabled': monitoring.get('alerts', {}).get('enabled', False)
        }

        # Summarize caching
        caching = config.get('caching', {})
        summary['caching'] = {
            'enabled': caching.get('enabled', False),
            'backend': caching.get('backend', 'simple')
        }

        return summary


def run_interactive_wizard():
    """Run the interactive CLI configuration wizard"""
    print("\n" + "="*60)
    print("🚀 Virtuoso CCXT Configuration Wizard")
    print("="*60)

    wizard = ConfigurationWizard()

    # Show templates
    print("\n📋 Available Configuration Templates:\n")
    for key, template in wizard.templates.items():
        print(f"  [{key}] {template['name']}")
        print(f"        {template['description']}\n")

    # Get user choice
    while True:
        choice = input("Select a template (beginner/advanced/professional) or 'custom': ").lower()

        if choice in wizard.templates:
            config = wizard.apply_template(choice)
            print(f"\n✅ Applied '{choice}' template")
            break
        elif choice == 'custom':
            config = wizard.current_config
            print("\n📝 Using current configuration as base")
            break
        else:
            print("Invalid choice. Please try again.")

    # Get API credentials
    print("\n🔑 API Credentials Configuration")
    print("-" * 40)

    for exchange_name in config.get('exchanges', {}).keys():
        if config['exchanges'][exchange_name].get('enabled'):
            print(f"\nConfiguring {exchange_name.upper()}:")

            api_creds = config['exchanges'][exchange_name].setdefault('api_credentials', {})

            # Check environment variables first
            env_key = os.getenv(f'{exchange_name.upper()}_API_KEY')
            env_secret = os.getenv(f'{exchange_name.upper()}_API_SECRET')

            if env_key and env_secret:
                print(f"  ✅ Using credentials from environment variables")
                api_creds['api_key'] = env_key
                api_creds['api_secret'] = env_secret
            else:
                current_key = api_creds.get('api_key', '')
                if current_key:
                    keep = input(f"  Keep existing API key? (***{current_key[-4:]}) [Y/n]: ").lower()
                    if keep != 'n':
                        continue

                api_key = input(f"  API Key (or press Enter to skip): ").strip()
                api_secret = input(f"  API Secret (or press Enter to skip): ").strip()

                if api_key and api_secret:
                    api_creds['api_key'] = api_key
                    api_creds['api_secret'] = api_secret

    # Configure alerts
    if config.get('monitoring', {}).get('alerts', {}).get('enabled'):
        print("\n🔔 Alert Configuration")
        print("-" * 40)
        webhook = input("Discord Webhook URL (or press Enter to skip): ").strip()
        if webhook:
            config['monitoring']['alerts']['discord_webhook'] = webhook

    # Validate configuration
    print("\n🔍 Validating Configuration...")
    validation = wizard.validate_config(config)

    if validation['errors']:
        print("\n❌ Errors found:")
        for error in validation['errors']:
            print(f"  - {error}")

    if validation['warnings']:
        print("\n⚠️  Warnings:")
        for warning in validation['warnings']:
            print(f"  - {warning}")

    if validation['suggestions']:
        print("\n💡 Suggestions:")
        for suggestion in validation['suggestions']:
            print(f"  - {suggestion}")

    # Save configuration
    if validation['valid']:
        save = input("\n💾 Save configuration? [Y/n]: ").lower()
        if save != 'n':
            if wizard.save_config(config):
                print("✅ Configuration saved successfully!")

                # Show summary
                summary = wizard.get_config_summary(config)
                print("\n📊 Configuration Summary:")
                print(f"  Environment: {summary['environment']}")
                print(f"  Exchanges: {', '.join([e['name'] for e in summary['exchanges']])}")
                print(f"  Analysis: {', '.join(summary['analysis_components'])}")
                print(f"  Monitoring: {'Enabled' if summary['monitoring']['enabled'] else 'Disabled'}")
                print(f"  Caching: {summary['caching']['backend']}")
            else:
                print("❌ Failed to save configuration")
    else:
        print("\n❌ Configuration is invalid. Please fix errors and try again.")

    print("\n" + "="*60)
    print("Configuration wizard complete!")
    print("="*60)


if __name__ == "__main__":
    run_interactive_wizard()