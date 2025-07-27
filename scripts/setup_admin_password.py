#!/usr/bin/env python3
"""
Setup script for admin dashboard password.
Generates a secure password hash for the admin dashboard.
"""

import hashlib
import secrets
import string
import getpass
import os

def generate_password(length=16):
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def hash_password(password):
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def main():
    print("🔐 Virtuoso Admin Dashboard Password Setup")
    print("=" * 50)
    
    choice = input("\n1. Generate random password\n2. Use custom password\nChoose option (1 or 2): ").strip()
    
    if choice == "1":
        password = generate_password()
        print(f"\n✅ Generated secure password: {password}")
        print("⚠️  SAVE THIS PASSWORD - it won't be displayed again!")
    elif choice == "2":
        password = getpass.getpass("\nEnter your admin password: ")
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long!")
            return
    else:
        print("❌ Invalid choice!")
        return
    
    password_hash = hash_password(password)
    
    print(f"\n🔑 Password hash: {password_hash}")
    print("\n📝 To set up the admin dashboard:")
    print("1. Add this to your environment variables:")
    print(f"   export ADMIN_PASSWORD_HASH='{password_hash}'")
    print("\n2. Or add to your .env file:")
    print(f"   ADMIN_PASSWORD_HASH={password_hash}")
    
    # Optionally write to .env file
    env_choice = input("\n💾 Add to .env file automatically? (y/n): ").strip().lower()
    if env_choice == 'y':
        env_file = ".env"
        
        # Read existing .env file
        env_lines = []
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Remove existing ADMIN_PASSWORD_HASH line
        env_lines = [line for line in env_lines if not line.startswith('ADMIN_PASSWORD_HASH=')]
        
        # Add new hash
        env_lines.append(f"ADMIN_PASSWORD_HASH={password_hash}\n")
        
        # Write back to file
        with open(env_file, 'w') as f:
            f.writelines(env_lines)
        
        print(f"✅ Added ADMIN_PASSWORD_HASH to {env_file}")
    
    print("\n🚀 Admin dashboard will be available at:")
    print("   http://localhost:8003/api/dashboard/admin/login")
    print("\n🛡️  Security Notes:")
    print("   - Use HTTPS in production")
    print("   - Change the default session timeout if needed")
    print("   - Consider using a reverse proxy with additional security")
    print("   - Monitor admin access logs")

if __name__ == "__main__":
    main()