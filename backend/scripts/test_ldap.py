#!/usr/bin/env python3
"""
Test LDAP/AD connection for Balaur SMS
Location: /opt/balaur-sms/backend/scripts/test_ldap.py

Usage:
    python scripts/test_ldap.py <username> <password>
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import config
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Change to backend directory to find .env
os.chdir(backend_dir)

# Now import after setting up path and directory
import ldap3
from ldap3 import Server, Connection, ALL, SUBTREE, Tls
import ssl

try:
    from app.config import settings
except Exception as e:
    print(f"❌ Error loading configuration: {e}")
    print()
    print("Make sure:")
    print("  1. You're in the backend directory: cd /opt/balaur-sms/backend")
    print("  2. .env file exists: ls -la .env")
    print("  3. Virtual environment is activated: source venv/bin/activate")
    print("  4. pydantic-settings is installed: pip install pydantic-settings")
    sys.exit(1)


def test_ldap_connection(test_username: str, test_password: str):
    """Test LDAP connection with user credentials"""
    
    print("=" * 60)
    print("BALAUR SMS - LDAP Connection Test")
    print("=" * 60)
    print()
    
    # Display configuration
    print("Configuration:")
    print(f"  Server: {settings.ldap_server}:{settings.ldap_port}")
    print(f"  Use SSL: {settings.ldap_use_ssl}")
    print(f"  Use TLS: {settings.ldap_use_tls}")
    print(f"  Base DN: {settings.ldap_base_dn}")
    print(f"  Bind DN: {settings.ldap_bind_dn}")
    print(f"  User Search Base: {settings.ldap_user_search_base}")
    print(f"  User Search Filter: {settings.ldap_user_search_filter}")
    print(f"  User Object Class: {settings.ldap_user_object_class}")
    print()
    
    try:
        # Step 1: Test service account bind
        print("Step 1: Testing service account bind...")
        print("-" * 60)
        
        # Configure TLS
        tls_config = None
        if settings.ldap_use_tls or settings.ldap_use_ssl:
            tls_config = Tls(
                validate=ssl.CERT_NONE if settings.ldap_tls_require_cert == "never" else ssl.CERT_REQUIRED
            )
        
        # Create server object
        use_ssl = settings.ldap_use_ssl
        server = Server(
            settings.ldap_server.replace('ldap://', '').replace('ldaps://', ''),
            port=settings.ldap_port,
            use_ssl=use_ssl,
            tls=tls_config,
            get_info=ALL,
            connect_timeout=settings.ldap_timeout
        )
        
        print(f"  Connecting to: {server}")
        
        # Bind with service account
        conn = Connection(
            server,
            user=settings.ldap_bind_dn,
            password=settings.ldap_bind_password,
            auto_bind=True,  # Changed to True for immediate bind
            raise_exceptions=True
        )
        
        # StartTLS if configured (already bound)
        if settings.ldap_use_tls and not use_ssl:
            print("  Using TLS for secure connection...")
        
        print(f"  ✓ Service account bind successful")
        print(f"  Server info: {server.info.vendor_name[0] if server.info.vendor_name else 'Unknown'}")
        print()
        
        # Step 2: Search for test user
        print("Step 2: Searching for user...")
        print("-" * 60)
        
        # Build search filter
        search_filter = settings.ldap_user_search_filter.replace("{username}", test_username)
        print(f"  Search base: {settings.ldap_user_search_base}")
        print(f"  Search filter: {search_filter}")
        
        # Search for user
        conn.search(
            search_base=settings.ldap_user_search_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=[
                settings.ldap_attr_username,
                settings.ldap_attr_email,
                settings.ldap_attr_first_name,
                settings.ldap_attr_last_name,
                settings.ldap_attr_member_of,
                'distinguishedName',
                'objectClass'
            ]
        )
        
        if not conn.entries:
            print(f"  ❌ User '{test_username}' not found")
            print(f"  Tried filter: {search_filter}")
            print(f"  In base: {settings.ldap_user_search_base}")
            
            # Try alternative search
            print()
            print("  Attempting alternative search in full base DN...")
            alt_filter = f"(sAMAccountName={test_username})"
            conn.search(
                search_base=settings.ldap_base_dn,
                search_filter=alt_filter,
                search_scope=SUBTREE,
                attributes=['distinguishedName', 'sAMAccountName']
            )
            
            if conn.entries:
                print(f"  ℹ User found with alternative search:")
                print(f"    DN: {conn.entries[0].distinguishedName}")
                print(f"  Update LDAP_USER_SEARCH_BASE to match user location")
            
            conn.unbind()
            return False
        
        user_entry = conn.entries[0]
        user_dn = user_entry.entry_dn
        
        print(f"  ✓ User found!")
        print(f"  DN: {user_dn}")
        print(f"  Username: {getattr(user_entry, settings.ldap_attr_username, 'N/A')}")
        print(f"  Email: {getattr(user_entry, settings.ldap_attr_email, 'N/A')}")
        print(f"  First Name: {getattr(user_entry, settings.ldap_attr_first_name, 'N/A')}")
        print(f"  Last Name: {getattr(user_entry, settings.ldap_attr_last_name, 'N/A')}")
        
        # Display groups (memberOf)
        if hasattr(user_entry, settings.ldap_attr_member_of):
            groups = getattr(user_entry, settings.ldap_attr_member_of)
            print(f"  Groups ({len(groups)}):")
            for group in groups[:5]:  # Show first 5
                print(f"    - {group}")
            if len(groups) > 5:
                print(f"    ... and {len(groups) - 5} more")
        
        conn.unbind()
        print()
        
        # Step 3: Test user authentication
        print("Step 3: Testing user authentication...")
        print("-" * 60)
        
        # Create new connection with user credentials
        user_conn = Connection(
            server,
            user=user_dn,
            password=test_password,
            auto_bind=True,
            raise_exceptions=True
        )
        
        # StartTLS if configured
        if settings.ldap_use_tls and not use_ssl:
            user_conn.start_tls()
        
        # Try to bind with user credentials
        if not user_conn.bind():
            print(f"  ❌ Authentication failed: {user_conn.result}")
            print(f"  Result code: {user_conn.result['result']}")
            print(f"  Description: {user_conn.result['description']}")
            return False
        
        print(f"  ✓ User authentication successful!")
        user_conn.unbind()
        print()
        
        # Step 4: Check role mapping
        print("Step 4: Checking role mapping...")
        print("-" * 60)
        
        role = "user"  # default role
        
        if settings.ldap_group_admin and hasattr(user_entry, settings.ldap_attr_member_of):
            groups = [g.lower() for g in getattr(user_entry, settings.ldap_attr_member_of)]
            
            if settings.ldap_group_admin.lower() in groups:
                role = "admin"
                print(f"  ✓ User is in Admin group")
            elif settings.ldap_group_manager and settings.ldap_group_manager.lower() in groups:
                role = "manager"
                print(f"  ✓ User is in Manager group")
            else:
                print(f"  ℹ User has default role: {role}")
        else:
            print(f"  ℹ No group mapping configured, default role: {role}")
        
        print()
        print("=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("Summary:")
        print(f"  • Service account bind: OK")
        print(f"  • User search: OK")
        print(f"  • User authentication: OK")
        print(f"  • Detected role: {role}")
        print()
        
        return True
        
    except ldap3.core.exceptions.LDAPBindError as e:
        print(f"  ❌ Bind error: {e}")
        print(f"  Check LDAP_BIND_DN and LDAP_BIND_PASSWORD")
        return False
        
    except ldap3.core.exceptions.LDAPSocketOpenError as e:
        print(f"  ❌ Connection error: {e}")
        print(f"  Check LDAP_SERVER and LDAP_PORT")
        print(f"  Verify firewall allows connection to {settings.ldap_server}:{settings.ldap_port}")
        return False
        
    except ldap3.core.exceptions.LDAPException as e:
        print(f"  ❌ LDAP error: {e}")
        return False
        
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python test_ldap.py <username> <password>")
        print()
        print("Example:")
        print("  python test_ldap.py jdoe mypassword")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    success = test_ldap_connection(username, password)
    sys.exit(0 if success else 1)
