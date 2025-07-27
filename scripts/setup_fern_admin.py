#!/usr/bin/env python3
"""
Setup admin dashboard with specific credentials for Fern.
"""

import hashlib
import os

def hash_password(password):
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def main():
    print("🔐 Setting up Admin Dashboard for Fern")
    print("=" * 50)
    
    # Set specific password
    password = "xrpsuxcock"
    password_hash = hash_password(password)
    
    print(f"\n✅ Admin setup for user: fern")
    print(f"🔑 Password hash generated: {password_hash}")
    
    # Check if .env file exists
    env_file = ".env"
    env_lines = []
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_lines = f.readlines()
        
        # Remove existing ADMIN_PASSWORD_HASH line
        env_lines = [line for line in env_lines if not line.startswith('ADMIN_PASSWORD_HASH=')]
        print(f"\n💾 Updating existing {env_file} file")
    else:
        print(f"\n💾 Creating new {env_file} file")
        env_lines = ["# Virtuoso Trading System Environment Variables\n\n"]
    
    # Add admin password hash
    if not any("Admin Dashboard" in line for line in env_lines):
        env_lines.append("\n# Admin Dashboard Authentication\n")
    env_lines.append(f"ADMIN_PASSWORD_HASH={password_hash}\n")
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.writelines(env_lines)
    
    print("✅ Admin password configured in .env file")
    
    print("\n🚀 Admin Dashboard Setup Complete!")
    print("=" * 50)
    print("📍 URL: http://localhost:8003/api/dashboard/admin/login")
    print("👤 Username: fern (not required for login)")
    print("🔐 Password: xrpsuxcock")
    print("\n⚠️  Security Notes:")
    print("   - Change this password for production use")
    print("   - Use HTTPS in production")
    print("   - Monitor admin access logs")
    
    # Create a reminder file
    reminder_file = "ADMIN_SETUP_COMPLETE.txt"
    with open(reminder_file, 'w') as f:
        f.write("VIRTUOSO ADMIN DASHBOARD - SETUP COMPLETE\n")
        f.write("=" * 40 + "\n\n")
        f.write("URL: http://localhost:8003/api/dashboard/admin/login\n")
        f.write("Username: fern (display only, not required for login)\n")
        f.write("Password: xrpsuxcock\n\n")
        f.write("The password has been hashed and stored in .env file\n")
        f.write("Start your application and visit the URL above to access the admin dashboard.\n")
    
    print(f"\n📄 Setup details saved to: {reminder_file}")

if __name__ == "__main__":
    main()