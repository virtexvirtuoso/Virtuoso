#!/usr/bin/env python3
"""
Test admin dashboard URL patterns and accessibility.
"""

from pathlib import Path

# URL patterns that should be available
ADMIN_URLS = {
    "HTML Pages": [
        "/api/dashboard/admin/login",
        "/api/dashboard/admin/dashboard"
    ],
    "Authentication": [
        "/api/dashboard/admin/auth/login",
        "/api/dashboard/admin/auth/logout", 
        "/api/dashboard/admin/auth/verify"
    ],
    "Configuration": [
        "/api/dashboard/admin/config/files",
        "/api/dashboard/admin/config/file/{filename}",
        "/api/dashboard/admin/config/backups/{filename}",
        "/api/dashboard/admin/config/restore/{backup_filename}"
    ],
    "System": [
        "/api/dashboard/admin/system/status",
        "/api/dashboard/admin/logs/recent"
    ]
}

def test_urls():
    """Display all admin dashboard URLs."""
    print("🌐 Admin Dashboard URL Reference")
    print("=" * 60)
    print("Base URL: http://localhost:8003")
    print("=" * 60)
    
    for category, urls in ADMIN_URLS.items():
        print(f"\n📌 {category}:")
        for url in urls:
            method = "POST" if "auth/login" in url or "auth/logout" in url or "/restore/" in url or "/config/file/" in url and "POST" in url else "GET"
            auth = " (🔐 Auth Required)" if not "login" in url else ""
            print(f"   {method:4} {url}{auth}")
    
    print("\n" + "=" * 60)
    print("📝 Example Usage:")
    print("=" * 60)
    print("\n1. First, login to get a session token:")
    print('   curl -X POST http://localhost:8003/api/dashboard/admin/auth/login \\')
    print('        -F "password=your_password"')
    print("\n2. Then use the token for authenticated requests:")
    print('   curl -H "Authorization: Bearer YOUR_TOKEN" \\')
    print('        http://localhost:8003/api/dashboard/admin/system/status')
    print("\n3. Or simply visit the web interface:")
    print('   http://localhost:8003/api/dashboard/admin/login')
    
    print("\n" + "=" * 60)
    print("🔒 Security Notes:")
    print("=" * 60)
    print("- All endpoints except /login require authentication")
    print("- Sessions expire after 24 hours by default")
    print("- Use HTTPS in production")
    print("- Set ADMIN_PASSWORD_HASH environment variable")

if __name__ == "__main__":
    test_urls()