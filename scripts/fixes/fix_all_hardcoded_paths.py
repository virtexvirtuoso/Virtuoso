#!/usr/bin/env python3
"""Fix all hardcoded paths in the project for VPS deployment."""

import os
import re
from pathlib import Path

def fix_python_files():
    """Fix hardcoded paths in Python files."""
    print("🔧 Fixing hardcoded paths in Python files...")
    
    # Pattern to match hardcoded paths
    patterns = [
        (r"sys\.path\.append\('os.path.dirname(os.path.dirname(os.path.abspath(__file__)))/src'\)", 
         "sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))"),
        (r"os.path.dirname(os.path.dirname(os.path.abspath(__file__)))", 
         "os.path.dirname(os.path.dirname(os.path.abspath(__file__)))")
    ]
    
    # Find all Python files
    fixed_count = 0
    for root, dirs, files in os.walk('scripts'):
        # Skip the fixes directory
        if 'fixes' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    original_content = content
                    for pattern, replacement in patterns:
                        content = re.sub(pattern, replacement, content)
                    
                    if content != original_content:
                        # Add import if needed
                        if 'os.path' in content and 'import os' not in content:
                            lines = content.split('\n')
                            # Find where to insert import
                            import_index = 0
                            for i, line in enumerate(lines):
                                if line.startswith('import ') or line.startswith('from '):
                                    import_index = i + 1
                                elif line.strip() and not line.startswith('#'):
                                    break
                            lines.insert(import_index, 'import os')
                            content = '\n'.join(lines)
                        
                        with open(filepath, 'w') as f:
                            f.write(content)
                        print(f"✅ Fixed: {filepath}")
                        fixed_count += 1
                except Exception as e:
                    print(f"❌ Error processing {filepath}: {e}")
    
    return fixed_count

def fix_shell_scripts():
    """Fix platform-specific issues in shell scripts."""
    print("\n🔧 Fixing shell scripts for Linux compatibility...")
    
    fixes = {
        'scripts/launch_virtuoso.sh': [
            ('lsof -Pi :8001', 'ss -tlnp | grep :8001 2>/dev/null || netstat -tlnp 2>/dev/null | grep :8001'),
            ('source venv311/bin/activate', '. ./venv311/bin/activate')
        ],
        'scripts/restart_with_fixed_db.sh': [
            ('lsof -Pi :8001', 'ss -tlnp | grep :8001 2>/dev/null || netstat -tlnp 2>/dev/null | grep :8001'),
            ('source venv311/bin/activate', '. ./venv311/bin/activate')
        ]
    }
    
    fixed_count = 0
    for script, replacements in fixes.items():
        if os.path.exists(script):
            try:
                with open(script, 'r') as f:
                    content = f.read()
                
                original_content = content
                for old, new in replacements:
                    content = content.replace(old, new)
                
                if content != original_content:
                    with open(script, 'w') as f:
                        f.write(content)
                    print(f"✅ Fixed: {script}")
                    fixed_count += 1
            except Exception as e:
                print(f"❌ Error processing {script}: {e}")
    
    return fixed_count

def fix_report_manager():
    """Fix Windows-specific path handling in report_manager.py."""
    print("\n🔧 Fixing platform-specific path handling...")
    
    filepath = 'src/core/reporting/report_manager.py'
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Fix the Windows backslash check
            original = "if current_dir.endswith('/src') or current_dir.endswith('\\\\src'):"
            replacement = "if current_dir.endswith(os.path.sep + 'src'):"
            
            if original in content:
                content = content.replace(original, replacement)
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"✅ Fixed: {filepath}")
                return 1
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
    
    return 0

def check_gpu_dependency():
    """Check and report on GPU dependency."""
    print("\n⚠️  GPU Dependency Check:")
    print("   GPUtil is listed in requirements.txt but requires NVIDIA drivers")
    print("   Consider moving it to optional dependencies or handling ImportError")
    print("   The code already handles ImportError properly in:")
    print("   - scripts/diagnostics/run_diagnostics.py")

def main():
    """Main function to run all fixes."""
    print("🚀 VPS Deployment Path Fixes")
    print("=" * 50)
    
    total_fixed = 0
    
    # Fix Python files
    total_fixed += fix_python_files()
    
    # Fix shell scripts
    total_fixed += fix_shell_scripts()
    
    # Fix report manager
    total_fixed += fix_report_manager()
    
    # Check GPU dependency
    check_gpu_dependency()
    
    print(f"\n✅ Total files fixed: {total_fixed}")
    print("\n📋 Next steps:")
    print("1. Review the changes with: git diff")
    print("2. Test the application locally")
    print("3. Commit the fixes: git add -A && git commit -m 'Fix hardcoded paths for VPS deployment'")
    print("4. Consider removing GPUtil from requirements.txt")
    print("5. Deploy to VPS using Docker or manual installation")

if __name__ == "__main__":
    main()