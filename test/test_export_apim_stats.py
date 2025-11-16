#!/usr/bin/env python3
"""
Test script to verify the connection and functionality of export_apim_stats.py
with the Gravitee Management API.
"""

import json
import sys
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Optional


def load_test_config(config_path: str = "config.master-env.json") -> Dict:
    """
    Load test configuration from a JSON file.
    
    Args:
        config_path: Path to the test configuration file
        
    Returns:
        Dictionary containing the configuration
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Check required fields
        required_fields = ['server_url', 'username', 'password', 'org_id', 'env_id']
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise ValueError(f"Missing fields in configuration: {', '.join(missing_fields)}")
        
        return config
    except FileNotFoundError:
        print(f"❌ Error: Configuration file '{config_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Configuration file is not valid JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)


def test_connection(config: Dict) -> bool:
    """
    Test connection to the server and authentication using API v2.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if connection succeeds, False otherwise
    """
    base_url = config['server_url'].rstrip('/')
    env_id = config['env_id']
    # API v2 endpoint: /management/v2/environments/{envId}/apis
    endpoint = f"{base_url}/v2/environments/{env_id}/apis"
    
    auth = HTTPBasicAuth(config['username'], config['password'])
    
    print(f"🔍 Testing connection to: {endpoint}")
    print(f"   User: {config['username']}")
    print()
    
    try:
        # Test with pagination - request first page
        params = {'page': 1, 'perPage': 10}
        response = requests.get(endpoint, auth=auth, params=params, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Connection successful! (Code: {response.status_code})")
            response_data = response.json()
            # API v2 returns paginated response with 'data' field
            if isinstance(response_data, dict) and 'data' in response_data:
                apis = response_data['data']
                pagination = response_data.get('pagination', {})
                total_count = pagination.get('totalCount', len(apis))
                page_count = pagination.get('pageCount', 1)
                print(f"✅ {len(apis)} API(s) found on page 1/{page_count} (total: {total_count})")
            else:
                apis = response_data if isinstance(response_data, list) else []
                print(f"✅ {len(apis)} API(s) found")
            return True
        elif response.status_code == 401:
            print(f"❌ Authentication failed (Code: {response.status_code})")
            print("   Please check your username and password.")
            return False
        elif response.status_code == 403:
            print(f"❌ Access denied (Code: {response.status_code})")
            print("   Please check your user permissions.")
            return False
        elif response.status_code == 404:
            print(f"❌ Endpoint not found (Code: {response.status_code})")
            print(f"   Please check the server URL and environment ID.")
            print(f"   Tested URL: {endpoint}")
            return False
        else:
            print(f"❌ Server error (Code: {response.status_code})")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL error: {e}")
        print("   The SSL certificate might be invalid or self-signed.")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Unable to connect to server {base_url}")
        print("   Please verify that the server is accessible and the URL is correct.")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out. The server is taking too long to respond.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during request: {e}")
        return False
    except json.JSONDecodeError:
        print("❌ Server response is not valid JSON.")
        return False


def test_export_apim_stats_script():
    """
    Test the export_apim_stats.py script by executing it with the test config.
    """
    print("=" * 80)
    print("Testing export_apim_stats.py script")
    print("=" * 80)
    print()
    
    # Import export_apim_stats module
    try:
        import sys
        import os
        # Add src directory to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        import export_apim_stats
    except ImportError as e:
        print(f"❌ Unable to import export_apim_stats.py: {e}")
        return False
    
    try:
        # Execute script with test config (path relative to project root)
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.master-env.json')
        config = load_test_config(config_path)
        apis = export_apim_stats.fetch_apis(config)
        
        if apis is not None:
            export_apim_stats.display_apis(apis)
            return True
        else:
            return False
    except Exception as e:
        print(f"❌ Error during script execution: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("=" * 80)
    print("GRAVITEE MANAGEMENT API CONNECTION TESTS")
    print("=" * 80)
    print()
    
    # Load test configuration
    config = load_test_config()
    print(f"✅ Configuration loaded from config.master-env.json")
    print()
    
    # Test 1: Simple connection
    print("TEST 1: Connection and authentication test")
    print("-" * 80)
    connection_ok = test_connection(config)
    print()
    
    if not connection_ok:
        print("❌ Tests failed. Please check your configuration.")
        sys.exit(1)
    
    # Test 2: Full script execution
    print("TEST 2: export_apim_stats.py script execution")
    print("-" * 80)
    script_ok = test_export_apim_stats_script()
    print()
    
    if connection_ok and script_ok:
        print("=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("=" * 80)
        print("❌ SOME TESTS FAILED")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()

