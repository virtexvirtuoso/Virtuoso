#!/usr/bin/env python3
"""
Complete fix for trade parameters in signal generation.
This script patches the alert manager to add trade parameters to all signals.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def create_patch():
    """Create a patch for alert_manager to add trade parameters."""

    patch_code = '''
# Trade Parameters Patch for AlertManager
# This patch adds stop loss and take profit calculation to all signals

def add_trade_parameters_to_signal(self, signal_data):
    """Add trade parameters (stop_loss, take_profit, position_size) to signal data."""

    # Skip if trade_params already exist
    if 'trade_params' in signal_data and signal_data['trade_params']:
        return signal_data

    try:
        # Get signal details
        signal_type = signal_data.get('signal_type', 'NEUTRAL')
        price = signal_data.get('price') or signal_data.get('entry_price', 0)
        confluence_score = signal_data.get('confluence_score', 50)
        reliability = signal_data.get('reliability', 0.5)

        # Skip neutral signals
        if signal_type == 'NEUTRAL' or not price:
            return signal_data

        # Calculate trade parameters
        stop_loss_pct = 3.5  # 3.5% stop loss
        take_profit_pct = 7.0  # 7% take profit (2:1 R/R)

        if signal_type == 'BUY':
            stop_loss = price * (1 - stop_loss_pct / 100)
            take_profit = price * (1 + take_profit_pct / 100)
        elif signal_type == 'SELL':
            stop_loss = price * (1 + stop_loss_pct / 100)
            take_profit = price * (1 - take_profit_pct / 100)
        else:
            return signal_data

        # Calculate position size (simplified)
        account_balance = 10000  # Default account balance
        risk_amount = account_balance * 0.02  # 2% risk
        stop_distance = abs(price - stop_loss)
        position_size = risk_amount / stop_distance if stop_distance > 0 else 0

        # Add trade parameters
        signal_data['trade_params'] = {
            'entry_price': price,
            'stop_loss': round(stop_loss, 8),
            'take_profit': round(take_profit, 8),
            'position_size': round(position_size, 8),
            'risk_reward_ratio': 2.0,
            'risk_percentage': 2.0,
            'confidence': min(confluence_score / 100, 1.0) if confluence_score else 0.5
        }

        # Also add at root level for backward compatibility
        signal_data['stop_loss'] = round(stop_loss, 8)
        signal_data['take_profit'] = round(take_profit, 8)

        self.logger.debug(f"Added trade parameters to {signal_type} signal for {signal_data.get('symbol')}")

    except Exception as e:
        self.logger.error(f"Error adding trade parameters: {str(e)}")

    return signal_data

# Monkey-patch the method
AlertManager.add_trade_parameters_to_signal = add_trade_parameters_to_signal

# Wrap the original send_signal_alert method
original_send_signal_alert = AlertManager.send_signal_alert

async def patched_send_signal_alert(self, signal_data):
    """Patched send_signal_alert that adds trade parameters."""
    # Add trade parameters before sending
    signal_data = self.add_trade_parameters_to_signal(signal_data)
    # Call original method
    return await original_send_signal_alert(signal_data)

# Apply the patch
AlertManager.send_signal_alert = patched_send_signal_alert

print("✅ Trade parameters patch applied to AlertManager")
'''

    return patch_code


def apply_patch_to_alert_manager():
    """Apply the patch directly to alert_manager.py."""

    alert_manager_path = Path("src/monitoring/alert_manager.py")

    # Read the current file
    with open(alert_manager_path, 'r') as f:
        content = f.read()

    # Check if patch already applied
    if "add_trade_parameters_to_signal" in content:
        print("✅ Patch already applied to alert_manager.py")
        return True

    # Find where to insert the patch (after class definition)
    class_line = "class AlertManager:"
    if class_line not in content:
        print("❌ Could not find AlertManager class definition")
        return False

    # Find the __init__ method to insert our patch after it
    init_end = content.find("        self.logger.info('AlertManager initialized')")
    if init_end == -1:
        init_end = content.find("        logger.info('AlertManager initialized')")

    if init_end == -1:
        print("⚠️ Could not find ideal patch location, adding at end of file")
        # Add at the end of file
        content += "\n\n" + create_patch()
    else:
        # Find the end of __init__ method
        init_end = content.find("\n\n", init_end)
        if init_end == -1:
            init_end = len(content)

        # Insert the patch method after __init__
        patch_method = '''
    def add_trade_parameters_to_signal(self, signal_data):
        """Add trade parameters (stop_loss, take_profit, position_size) to signal data."""

        # Skip if trade_params already exist
        if 'trade_params' in signal_data and signal_data['trade_params']:
            return signal_data

        try:
            # Get signal details
            signal_type = signal_data.get('signal_type', 'NEUTRAL')
            price = signal_data.get('price') or signal_data.get('entry_price', 0)
            confluence_score = signal_data.get('confluence_score', 50)
            reliability = signal_data.get('reliability', 0.5)

            # Skip neutral signals
            if signal_type == 'NEUTRAL' or not price:
                return signal_data

            # Calculate trade parameters
            stop_loss_pct = 3.5  # 3.5% stop loss
            take_profit_pct = 7.0  # 7% take profit (2:1 R/R)

            if signal_type == 'BUY':
                stop_loss = price * (1 - stop_loss_pct / 100)
                take_profit = price * (1 + take_profit_pct / 100)
            elif signal_type == 'SELL':
                stop_loss = price * (1 + stop_loss_pct / 100)
                take_profit = price * (1 - take_profit_pct / 100)
            else:
                return signal_data

            # Calculate position size (simplified)
            account_balance = self.config.get('trading', {}).get('account_balance', 10000)
            risk_amount = account_balance * 0.02  # 2% risk
            stop_distance = abs(price - stop_loss)
            position_size = risk_amount / stop_distance if stop_distance > 0 else 0

            # Add trade parameters
            signal_data['trade_params'] = {
                'entry_price': price,
                'stop_loss': round(stop_loss, 8),
                'take_profit': round(take_profit, 8),
                'position_size': round(position_size, 8),
                'risk_reward_ratio': 2.0,
                'risk_percentage': 2.0,
                'confidence': min(confluence_score / 100, 1.0) if confluence_score else 0.5
            }

            # Also add at root level for backward compatibility
            signal_data['stop_loss'] = round(stop_loss, 8)
            signal_data['take_profit'] = round(take_profit, 8)

            self.logger.debug(f"Added trade parameters to {signal_type} signal for {signal_data.get('symbol')}")

        except Exception as e:
            self.logger.error(f"Error adding trade parameters: {str(e)}")

        return signal_data
'''

        content = content[:init_end] + patch_method + content[init_end:]

    # Now wrap the send_signal_alert method
    send_alert_line = "async def send_signal_alert(self, signal_data):"
    if send_alert_line in content:
        # Find the start of the method
        method_start = content.find(send_alert_line)
        # Find the actual implementation (after docstring if any)
        impl_start = content.find("try:", method_start)
        if impl_start == -1:
            impl_start = content.find("if ", method_start)

        if impl_start != -1:
            # Insert trade params calculation at the beginning
            indent = "        "  # 2 levels of indentation
            patch_call = f"\n{indent}# Add trade parameters to signal\n{indent}signal_data = self.add_trade_parameters_to_signal(signal_data)\n"
            content = content[:impl_start] + patch_call + content[impl_start:]
            print("✅ Patched send_signal_alert method")

    # Write the patched file
    with open(alert_manager_path, 'w') as f:
        f.write(content)

    print("✅ Trade parameters patch applied to alert_manager.py")
    return True


if __name__ == "__main__":
    print("🔧 Applying Trade Parameters Fix")
    print("="*50)

    if apply_patch_to_alert_manager():
        print("\n✅ Fix applied successfully!")
        print("\nNext steps:")
        print("1. Deploy to VPS: scp src/monitoring/alert_manager.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/")
        print("2. Restart service: ssh vps 'sudo systemctl restart virtuoso-trading.service'")
        sys.exit(0)
    else:
        print("\n❌ Failed to apply fix")
        sys.exit(1)