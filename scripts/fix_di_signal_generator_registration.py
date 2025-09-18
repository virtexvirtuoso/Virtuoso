#!/usr/bin/env python3
"""
Fix DI container registration for SignalGenerator.

This script modifies main.py to register the configured SignalGenerator instance
in the DI container so that when monitor.py requests it, it gets the properly
configured instance with all connections.
"""

import sys
import os

def fix_di_registration():
    """Fix the DI registration issue for SignalGenerator."""
    
    main_file = "/home/linuxuser/trading/Virtuoso_ccxt/src/main.py"
    
    print("🔧 Fixing DI container registration for SignalGenerator...")
    
    # Read the main.py file
    try:
        with open(main_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ File not found: {main_file}")
        return False
    
    # Find the line where we connect monitor to signal_generator (around line 660)
    insert_line = None
    for i, line in enumerate(lines):
        if "Connected monitor to signal_generator for direct OHLCV cache access" in line:
            insert_line = i + 1
            break
    
    if not insert_line:
        print("❌ Could not find the marker line for insertion")
        return False
    
    # Check if the fix is already applied
    fix_marker = "Register configured SignalGenerator in DI container"
    for line in lines:
        if fix_marker in line:
            print("✅ Fix already applied to main.py")
            return True
    
    # Add the registration code
    registration_code = """
    # Register configured SignalGenerator in DI container as singleton
    # This ensures that when monitor.py requests SignalGenerator from DI,
    # it gets the configured instance with all connections
    try:
        from src.signal_generation.signal_generator import SignalGenerator
        container.register_instance(SignalGenerator, signal_generator)
        logger.info("✅ Registered configured SignalGenerator in DI container as singleton")
    except Exception as e:
        logger.warning(f"Could not register SignalGenerator in DI container: {e}")
        # This is not critical - the system will still work but might not share OHLCV cache
    
"""
    
    # Insert the registration code
    lines.insert(insert_line, registration_code)
    
    # Write the file back
    try:
        with open(main_file, 'w') as f:
            f.writelines(lines)
        print(f"✅ Successfully updated {main_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to write file: {e}")
        return False

def verify_fix():
    """Verify that the fix was applied correctly."""
    
    main_file = "/home/linuxuser/trading/Virtuoso_ccxt/src/main.py"
    
    try:
        with open(main_file, 'r') as f:
            content = f.read()
        
        checks = [
            ("DI registration added", "container.register_instance(SignalGenerator, signal_generator)" in content),
            ("Logging added", "Registered configured SignalGenerator in DI container" in content),
        ]
        
        all_passed = True
        for check_name, result in checks:
            if result:
                print(f"✅ {check_name}: PASSED")
            else:
                print(f"❌ {check_name}: FAILED")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ Could not verify fix: {e}")
        return False

def main():
    """Main function."""
    
    print("=" * 60)
    print("DI Container SignalGenerator Registration Fix")
    print("=" * 60)
    
    # Apply the fix
    if fix_di_registration():
        print("\n✅ Fix applied successfully!")
        
        # Verify the fix
        print("\n🔍 Verifying the fix...")
        if verify_fix():
            print("\n✅ All verifications passed!")
            print("\n📋 Next steps:")
            print("1. The service should automatically restart via systemd")
            print("2. Monitor the logs to see if SignalGenerator gets registered in DI")
            print("3. Check if OHLCV data and charts start appearing in alerts")
            print("\nMonitor with:")
            print("sudo journalctl -u virtuoso-trading.service -f | grep -E 'Registered configured SignalGenerator|OHLCV|chart'")
            return 0
        else:
            print("\n⚠️ Some verifications failed, but the fix was applied")
            return 1
    else:
        print("\n❌ Failed to apply the fix")
        return 1

if __name__ == "__main__":
    sys.exit(main())