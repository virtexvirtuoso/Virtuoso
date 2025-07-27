#!/usr/bin/env python3
"""
Auto setup script for admin dashboard password.
Generates a secure password and displays setup instructions.
"""

import hashlib
import secrets
import string
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
    print("🔐 Virtuoso Admin Dashboard Password Setup (Auto)")
    print("=" * 50)
    
    # Generate secure password
    password = generate_password()
    password_hash = hash_password(password)
    
    print(f"\n✅ Generated secure password: {password}")
    print("⚠️  SAVE THIS PASSWORD - it won't be displayed again!")
    
    print(f"\n🔑 Password hash: {password_hash}")
    
    print("\n📝 To set up the admin dashboard:")
    print("1. Add this to your environment variables:")
    print(f"   export ADMIN_PASSWORD_HASH='{password_hash}'")
    
    print("\n2. Or add to your .env file:")
    print(f"   ADMIN_PASSWORD_HASH={password_hash}")
    
    # Check if .env file exists
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"\n💾 Found existing {env_file} file")
        
        # Read existing .env file
        with open(env_file, 'r') as f:
            env_content = f.read()
        
        if 'ADMIN_PASSWORD_HASH' in env_content:
            print("⚠️  ADMIN_PASSWORD_HASH already exists in .env file")
            print("   To update it, replace the existing line with the new hash above")
        else:
            # Add to .env file
            with open(env_file, 'a') as f:
                f.write(f"\n# Admin Dashboard Authentication\n")
                f.write(f"ADMIN_PASSWORD_HASH={password_hash}\n")
            print("✅ Added ADMIN_PASSWORD_HASH to .env file")
    else:
        # Create new .env file
        with open(env_file, 'w') as f:
            f.write("# Virtuoso Trading System Environment Variables\n\n")
            f.write("# Admin Dashboard Authentication\n")
            f.write(f"ADMIN_PASSWORD_HASH={password_hash}\n")
        print(f"✅ Created {env_file} with ADMIN_PASSWORD_HASH")
    
    print("\n🚀 Admin dashboard setup complete!")
    print("   URL: http://localhost:8003/api/dashboard/admin/login")
    print(f"   Username: (not required)")
    print(f"   Password: {password}")
    
    print("\n🛡️  Security Notes:")
    print("   - Use HTTPS in production")
    print("   - Store this password securely")
    print("   - Consider using a password manager")
    print("   - Monitor admin access logs")
    
    # Save credentials to a secure file (optional)
    creds_file = "admin_credentials.txt"
    with open(creds_file, 'w') as f:
        f.write("VIRTUOSO ADMIN DASHBOARD CREDENTIALS\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"URL: http://localhost:8003/api/dashboard/admin/login\n")
        f.write(f"Password: {password}\n")
        f.write(f"Password Hash: {password_hash}\n\n")
        f.write("⚠️  DELETE THIS FILE AFTER SAVING THE PASSWORD!\n")
    
    print(f"\n📄 Credentials also saved to: {creds_file}")
    print("   ⚠️  DELETE THIS FILE after saving the password!")

if __name__ == "__main__":
    main()