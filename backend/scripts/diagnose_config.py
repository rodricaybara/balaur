#!/usr/bin/env python3
"""
Diagnose configuration issues
Location: /opt/balaur-sms/backend/scripts/diagnose_config.py
"""

import os
import sys
from pathlib import Path

# Get backend directory (parent of scripts/)
backend_dir = Path(__file__).parent.parent.resolve()

# Change to backend directory
os.chdir(backend_dir)

# Add backend directory to Python path
sys.path.insert(0, str(backend_dir))

print(f"Working directory: {os.getcwd()}")
print(f"Python path includes: {backend_dir}")
print()

print("=" * 60)
print("BALAUR SMS - Configuration Diagnostics")
print("=" * 60)
print()

# Check .env file exists
env_file = backend_dir / ".env"
if not env_file.exists():
    print("❌ .env file not found!")
    print(f"   Expected location: {env_file}")
    sys.exit(1)

print(f"✓ .env file found: {env_file}")
print()

# Read .env and check format
print("Checking .env format...")
print("-" * 60)

with open(env_file, 'r') as f:
    lines = f.readlines()

issues = []
valid_vars = []

for i, line in enumerate(lines, 1):
    line = line.rstrip('\n')
    
    # Skip comments and empty lines
    if not line or line.startswith('#'):
        continue
    
    # Check for leading spaces
    if line.startswith(' ') or line.startswith('\t'):
        issues.append(f"Line {i}: Leading whitespace: '{line[:20]}...'")
        continue
    
    # Check for valid format
    if '=' not in line:
        issues.append(f"Line {i}: No '=' found: '{line[:40]}...'")
        continue
    
    key, value = line.split('=', 1)
    
    # Check key format
    if not key.strip():
        issues.append(f"Line {i}: Empty key")
        continue
    
    valid_vars.append(key.strip())

if issues:
    print("❌ Format issues found:")
    for issue in issues:
        print(f"   • {issue}")
    print()
else:
    print("✓ No format issues found")
    print()

print(f"Valid variables found: {len(valid_vars)}")
print()

# Try to import pydantic-settings
print("Checking dependencies...")
print("-" * 60)

try:
    import pydantic_settings
    print(f"✓ pydantic-settings: {pydantic_settings.__version__}")
except ImportError:
    print("❌ pydantic-settings not installed")
    print("   Run: pip install pydantic-settings")
    sys.exit(1)

try:
    import pydantic
    print(f"✓ pydantic: {pydantic.__version__}")
except ImportError:
    print("❌ pydantic not installed")
    sys.exit(1)

print()

# Try to load settings
print("Attempting to load settings...")
print("-" * 60)

try:
    from app.config import Settings
    
    # Try to create instance
    settings = Settings()
    
    print("✓ Settings loaded successfully!")
    print()
    print("Key configuration values:")
    print(f"  App Name: {settings.app_name}")
    print(f"  Environment: {settings.environment}")
    print(f"  Debug: {settings.debug}")
    print(f"  LDAP Enabled: {settings.ldap_enabled}")
    print(f"  LDAP Server: {settings.ldap_server}")
    print(f"  Database URL: {settings.database_url[:50]}...")
    print()
    print("=" * 60)
    print("✓ ALL CHECKS PASSED")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error loading settings: {e}")
    print()
    
    # Show which variables are defined in Settings class
    print("Expected variables in Settings class:")
    print("-" * 60)
    try:
        from app.config import Settings
        import inspect
        
        # Get all attributes
        annotations = Settings.__annotations__
        print(f"Total expected: {len(annotations)}")
        print()
        
        # Compare with .env
        env_vars_lower = [v.lower() for v in valid_vars]
        missing_in_env = []
        
        for field in sorted(annotations.keys()):
            if field.lower() not in env_vars_lower:
                # Check if it has a default value
                if hasattr(Settings, field):
                    default = getattr(Settings, field)
                    if default is not None and not callable(default):
                        continue
                missing_in_env.append(field)
        
        if missing_in_env:
            print("Variables missing in .env (but may have defaults):")
            for var in missing_in_env[:10]:
                print(f"  • {var}")
            if len(missing_in_env) > 10:
                print(f"  ... and {len(missing_in_env) - 10} more")
        
    except Exception as e2:
        print(f"Could not analyze Settings class: {e2}")
    
    print()
    print("Full error:")
    import traceback
    traceback.print_exc()
    
    sys.exit(1)
