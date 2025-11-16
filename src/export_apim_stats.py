#!/usr/bin/env python3
"""
Script to export APIM statistics from the Gravitee Management API.
Fetches API data and exports statistics in JSON format.
Uses a configuration file for connection parameters.
"""

import json
import sys
import argparse
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional, Tuple
import yaml
import os
from datetime import datetime, timedelta


def load_spec_v1(spec_path: str = "apim/spec/spec.v1.json") -> Optional[Dict]:
    """
    Load API specification v1 from a JSON file.
    
    Args:
        spec_path: Path to the v1 specification file (JSON)
        
    Returns:
        Dictionary containing the API specification v1, or None if file cannot be loaded
    """
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec = json.load(f)
        return spec
    except FileNotFoundError:
        print(f"Warning: Specification file '{spec_path}' not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Warning: Specification file is not valid JSON: {e}")
        return None
    except Exception as e:
        print(f"Warning: Error loading specification v1: {e}")
        return None


def load_spec_v2(spec_path: str = "apim/spec/spec.v2.yaml") -> Optional[Dict]:
    """
    Load API specification v2 from a YAML file.
    
    Args:
        spec_path: Path to the v2 specification file (YAML)
        
    Returns:
        Dictionary containing the API specification v2, or None if file cannot be loaded
    """
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        return spec
    except FileNotFoundError:
        print(f"Warning: Specification file '{spec_path}' not found.")
        return None
    except yaml.YAMLError as e:
        print(f"Warning: Specification file is not valid YAML: {e}")
        return None
    except Exception as e:
        print(f"Warning: Error loading specification v2: {e}")
        return None


def get_auth_headers(config: Dict) -> Tuple[Optional[HTTPBasicAuth], Dict[str, str]]:
    """
    Get authentication object and headers based on configuration.
    Supports both Basic Auth and Bearer Token authentication.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple of (auth_object, headers_dict)
        - For Basic Auth: (HTTPBasicAuth object, {})
        - For Bearer Token: (None, {'Authorization': 'Bearer <token>'})
    """
    auth_type = config.get('auth_type', 'basic').lower()
    
    if auth_type == 'bearer':
        token = config.get('token') or config.get('bearer_token')
        if not token:
            raise ValueError("Bearer token authentication requires 'token' or 'bearer_token' in configuration")
        headers = {'Authorization': f'Bearer {token}'}
        return None, headers
    else:
        # Default to Basic Auth
        username = config.get('username')
        password = config.get('password')
        if not username or not password:
            raise ValueError("Basic authentication requires 'username' and 'password' in configuration")
        auth = HTTPBasicAuth(username, password)
        return auth, {}


def load_config(config_path: str = None) -> Dict:
    """
    Load configuration from a JSON file or environment variables and load API specifications.
    
    Args:
        config_path: Path to the configuration file. If None, tries to find config.json in project root.
        
    Returns:
        Dictionary containing the configuration and API specifications
    """
    config = {}
    
    # If no config path provided, try to find config.json in project root
    if config_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # Go up from src/ to project root
        config_path = os.path.join(project_root, "config.json")
    elif not os.path.isabs(config_path):
        # If relative path, try to resolve from project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        config_path = os.path.join(project_root, config_path)
    
    # Try to load from file first
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Configuration file is not valid JSON: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading configuration file: {e}")
            sys.exit(1)
    
    # Override with environment variables if they exist
    config['server_url'] = os.getenv('GRAVITEE_SERVER_URL', config.get('server_url', ''))
    config['auth_type'] = os.getenv('GRAVITEE_AUTH_TYPE', config.get('auth_type', 'basic')).lower()
    config['username'] = os.getenv('GRAVITEE_USERNAME', config.get('username', ''))
    config['password'] = os.getenv('GRAVITEE_PASSWORD', config.get('password', ''))
    config['token'] = os.getenv('GRAVITEE_TOKEN', config.get('token', config.get('bearer_token', '')))
    config['org_id'] = os.getenv('GRAVITEE_ORG_ID', config.get('org_id', 'DEFAULT'))
    config['env_id'] = os.getenv('GRAVITEE_ENV_ID', config.get('env_id', 'DEFAULT'))
    
    # Check required fields based on auth type
    auth_type = config.get('auth_type', 'basic').lower()
    required_fields = ['server_url', 'org_id', 'env_id']
    
    if auth_type == 'bearer':
        if not config.get('token'):
            required_fields.append('token')
    else:
        # Basic auth
        required_fields.extend(['username', 'password'])
    
    missing_fields = [field for field in required_fields if not config.get(field)]
    
    if missing_fields:
        raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}. "
                        f"Please provide them via config file or environment variables.")
    
    # Load API specifications v1 and v2
    # Try to find spec files relative to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Go up from src/ to project root
    spec_v1_path = os.path.join(project_root, "apim", "spec", "spec.v1.json")
    spec_v2_path = os.path.join(project_root, "apim", "spec", "spec.v2.yaml")
    config['spec_v1'] = load_spec_v1(spec_v1_path)
    config['spec_v2'] = load_spec_v2(spec_v2_path)
    
    return config


def fetch_apis(config: Dict) -> Optional[List[Dict]]:
    """
    Fetch the list of APIs from the Gravitee Management API v2.
    Handles pagination to retrieve all APIs across all pages.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of APIs or None in case of error
    """
    # Build endpoint URL for API v2
    base_url = config['server_url'].rstrip('/')
    env_id = config['env_id']
    # API v2 endpoint: /management/v2/environments/{envId}/apis
    endpoint = f"{base_url}/v2/environments/{env_id}/apis"
    
    # Get authentication
    auth, headers = get_auth_headers(config)
    
    all_apis = []
    page = 1
    per_page = 100  # Request more items per page to reduce number of requests
    
    try:
        while True:
            # Build request with pagination parameters
            params = {'page': page, 'perPage': per_page}
            print(f"Fetching page {page} from: {endpoint}", file=sys.stderr)
            
            response = requests.get(endpoint, auth=auth, headers=headers, params=params, timeout=30)
            
            # Check response status
            if response.status_code == 200:
                response_data = response.json()
                # API v2 returns paginated response with 'data' field
                if isinstance(response_data, dict) and 'data' in response_data:
                    page_apis = response_data['data']
                    all_apis.extend(page_apis)
                    
                    # Check pagination info
                    pagination = response_data.get('pagination', {})
                    page_count = pagination.get('pageCount', 1)
                    total_count = pagination.get('totalCount', len(page_apis))
                    current_page = pagination.get('page', page)
                    
                    print(f"  Retrieved {len(page_apis)} APIs from page {current_page}/{page_count} (total: {total_count})", file=sys.stderr)
                    
                    # If we've fetched all pages, break
                    if current_page >= page_count or len(page_apis) == 0:
                        break
                    
                    page += 1
                else:
                    # Fallback: if response is already a list (shouldn't happen with v2, but just in case)
                    if isinstance(response_data, list):
                        all_apis.extend(response_data)
                    break
            elif response.status_code == 401:
                print("Error: Authentication failed. Please check your username and password.", file=sys.stderr)
                return None
            elif response.status_code == 403:
                print("Error: Access denied. Please check your user permissions.", file=sys.stderr)
                return None
            elif response.status_code == 404:
                print(f"Error: Endpoint not found. Please check the server URL and environment ID.", file=sys.stderr)
                return None
            else:
                print(f"Error: Server returned status code {response.status_code}", file=sys.stderr)
                print(f"Response: {response.text}", file=sys.stderr)
                return None
        
        print(f"Total APIs retrieved: {len(all_apis)}", file=sys.stderr)
        return all_apis
            
    except requests.exceptions.ConnectionError:
        print(f"Error: Unable to connect to server {base_url}", file=sys.stderr)
        print("Please verify that the server is accessible and the URL is correct.", file=sys.stderr)
        return None
    except requests.exceptions.Timeout:
        print("Error: Request timed out. The server is taking too long to respond.", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Error: Server response is not valid JSON.", file=sys.stderr)
        return None


def display_apis(apis: List[Dict]) -> None:
    """
    Display the list of APIs and their statistics in a formatted way.
    
    Args:
        apis: List of APIs
    """
    if not apis:
        print("No APIs found.")
        return
    
    print(f"\n{'='*80}")
    print(f"List of APIs ({len(apis)} API(s) found)")
    print(f"{'='*80}\n")
    
    # Table headers with new columns
    print(f"{'Name':<35} {'DefVersion':<12} {'Type':<10} {'ExecMode':<15} {'Status':<10} {'ID':<35}")
    print("-" * 117)
    
    # Display each API
    for api in apis:
        name = api.get('name', 'N/A')
        definition_version = api.get('definitionVersion', 'N/A')
        api_type = api.get('type', 'N/A')
        execution_mode = api.get('executionMode', 'N/A')
        state = api.get('state', 'N/A')
        api_id = api.get('id', 'N/A')
        
        # Formatting for display
        name = name[:32] + '...' if len(name) > 35 else name
        api_id = api_id[:32] + '...' if len(api_id) > 35 else api_id
        definition_version = str(definition_version)[:11] if definition_version != 'N/A' else 'N/A'
        api_type = str(api_type)[:9] if api_type != 'N/A' else 'N/A'
        execution_mode = str(execution_mode)[:14] if execution_mode != 'N/A' else 'N/A'
        
        print(f"{name:<35} {definition_version:<12} {api_type:<10} {execution_mode:<15} {state:<10} {api_id:<35}")
    
    print(f"\n{'='*80}\n")
    
    # Statistics by status
    status_counts = {}
    definition_version_counts = {}
    type_counts = {}
    execution_mode_counts = {}
    
    for api in apis:
        state = api.get('state', 'N/A')
        status_counts[state] = status_counts.get(state, 0) + 1
        
        definition_version = api.get('definitionVersion', 'N/A')
        definition_version_counts[definition_version] = definition_version_counts.get(definition_version, 0) + 1
        
        api_type = api.get('type', 'N/A')
        type_counts[api_type] = type_counts.get(api_type, 0) + 1
        
        execution_mode = api.get('executionMode', 'N/A')
        execution_mode_counts[execution_mode] = execution_mode_counts.get(execution_mode, 0) + 1
    
    print("Statistics by status:")
    for status, count in sorted(status_counts.items()):
        print(f"  - {status}: {count}")
    
    print("\nStatistics by definition version:")
    for version, count in sorted(definition_version_counts.items()):
        print(f"  - {version}: {count}")
    
    print("\nStatistics by type:")
    for api_type, count in sorted(type_counts.items()):
        print(f"  - {api_type}: {count}")
    
    print("\nStatistics by execution mode:")
    for mode, count in sorted(execution_mode_counts.items()):
        print(f"  - {mode}: {count}")


def fetch_api_details(api_id: str, config: Dict) -> Optional[Dict]:
    """
    Fetch complete API details including policies from the export endpoint.
    Note: Plans are not included in the export endpoint and must be fetched separately.
    
    Args:
        api_id: ID of the API
        config: Configuration dictionary
        
    Returns:
        Complete API object with all details, or None in case of error
    """
    base_url = config['server_url'].rstrip('/')
    env_id = config['env_id']
    # Use the API export endpoint to get all details
    endpoint = f"{base_url}/v2/environments/{env_id}/apis/{api_id}"
    auth, headers = get_auth_headers(config)
    
    try:
        response = requests.get(endpoint, auth=auth, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"Warning: API {api_id} not found.", file=sys.stderr)
            return None
        else:
            print(f"Warning: Failed to fetch API {api_id}: status {response.status_code}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Warning: Error fetching API {api_id}: {e}", file=sys.stderr)
        return None


def extract_policies_from_flows(flows: List[Dict]) -> List[str]:
    """
    Extract enabled policy names from flows.
    Policies can be in request, response, subscribe, publish, pre, or post sections.
    
    Args:
        flows: List of flow objects
        
    Returns:
        List of unique enabled policy names (from 'policy' attribute)
    """
    policies_set = set()
    
    if not isinstance(flows, list):
        return []
    
    # Sections where policies can be found
    policy_sections = ['request', 'response', 'subscribe', 'publish', 'pre', 'post']
    
    for flow in flows:
        if not isinstance(flow, dict):
            continue
        
        # Check each section for policies
        for section in policy_sections:
            section_policies = flow.get(section, [])
            if isinstance(section_policies, list):
                for policy in section_policies:
                    if isinstance(policy, dict):
                        # Only include enabled policies
                        enabled = policy.get('enabled', True)  # Default to True if not specified
                        if enabled:
                            # Get policy name from 'policy' attribute
                            policy_name = policy.get('policy', policy.get('name', 'N/A'))
                            if policy_name and policy_name != 'N/A':
                                policies_set.add(policy_name)
    
    return sorted(list(policies_set))


def get_api_analytics_by_plan(api_id: str, definition_version: str, config: Dict) -> Dict[str, int]:
    """
    Retrieve request count by plan for the last 30 days using analytics endpoint.
    Uses different endpoints and parameters based on API definition version.
    
    Args:
        api_id: ID of the API
        definition_version: API definition version (V2, V4, etc.)
        config: Configuration dictionary
        
    Returns:
        Dictionary mapping plan_id to request count, or empty dict if error
    """
    base_url = config['server_url'].rstrip('/')
    env_id = config['env_id']
    org_id = config.get('org_id', 'DEFAULT')
    
    # Calculate timestamps for last 30 days (in milliseconds)
    # from = current date minus 30 days, to = now
    now = datetime.now()
    to_timestamp = int(now.timestamp() * 1000)  # Current time in milliseconds
    from_timestamp = int((now - timedelta(days=30)).timestamp() * 1000)  # 30 days ago in milliseconds
    
    # Build analytics endpoint based on definition version
    if definition_version == 'V2':
        # For V2 APIs, use the organizations path
        endpoint = f"{base_url}/organizations/{org_id}/environments/{env_id}/apis/{api_id}/analytics"
        # V2 uses different parameters (lowercase, different field name, different interval)
        params = {
            'type': 'group_by',
            'from': from_timestamp,
            'to': to_timestamp,
            'interval': 43200000,  # 12 hours in milliseconds
            'field': 'plan'
        }
    else:
        # For V4 and other versions, use the v2 API path
        endpoint = f"{base_url}/v2/environments/{env_id}/apis/{api_id}/analytics"
        params = {
            'type': 'GROUP_BY',
            'from': from_timestamp,
            'to': to_timestamp,
            'interval': 86400000,  # 1 day in milliseconds
            'field': 'plan-id',
            'order': '-count:_count'
        }
    
    auth, headers = get_auth_headers(config)
    
    try:
        response = requests.get(endpoint, auth=auth, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            response_data = response.json()
            
            # Parse the response to extract plan_id -> count mapping
            plan_counts = {}
            
            # Both V2 and V4 APIs return the same format: { "values": { "plan_id": count }, "metadata": { "plan_id": {...} } }
            if isinstance(response_data, dict) and 'values' in response_data:
                values = response_data['values']
                if isinstance(values, dict):
                    # values is a dictionary: plan_id -> count
                    for plan_id, count in values.items():
                        if plan_id and count is not None:
                            plan_counts[plan_id] = int(count)
            
            return plan_counts
        elif response.status_code == 404:
            # Analytics endpoint not available for this API
            return {}
        else:
            # Other error, return empty dict
            return {}
    except Exception as e:
        # If any error occurs, return empty dict
        print(f"Warning: Error fetching analytics for API {api_id[:20]}...: {e}", file=sys.stderr)
        return {}


def get_api_plans(api_id: str, config: Dict) -> List[Dict]:
    """
    Retrieve plans for a specific API.
    Plans are not included in the API export endpoint, so we fetch them separately.
    
    Args:
        api_id: ID of the API
        config: Configuration dictionary
        
    Returns:
        List of plans with filtered information (id, status, security type)
    """
    base_url = config['server_url'].rstrip('/')
    env_id = config['env_id']
    endpoint = f"{base_url}/v2/environments/{env_id}/apis/{api_id}/plans"
    auth, headers = get_auth_headers(config)
    
    try:
        response = requests.get(endpoint, auth=auth, headers=headers, timeout=30)
        if response.status_code == 200:
            response_data = response.json()
            # API v2 returns paginated response with 'data' field
            if isinstance(response_data, dict) and 'data' in response_data:
                plans = response_data['data']
                # Filter to only include needed fields
                filtered_plans = []
                for plan in plans:
                    security = plan.get('security', {})
                    security_type = security.get('type', 'N/A') if isinstance(security, dict) else 'N/A'
                    filtered_plan = {
                        'id': plan.get('id', 'N/A'),
                        'status': plan.get('status', 'N/A'),
                        'type': security_type
                    }
                    filtered_plans.append(filtered_plan)
                return filtered_plans
            elif isinstance(response_data, list):
                # Fallback if response is a list
                filtered_plans = []
                for plan in response_data:
                    security = plan.get('security', {})
                    security_type = security.get('type', 'N/A') if isinstance(security, dict) else 'N/A'
                    filtered_plan = {
                        'id': plan.get('id', 'N/A'),
                        'status': plan.get('status', 'N/A'),
                        'type': security_type
                    }
                    filtered_plans.append(filtered_plan)
                return filtered_plans
        # If error or no plans, return empty list
        return []
    except Exception:
        # If any error occurs, return empty list
        return []


def fetch_users(config: Dict) -> Optional[List[Dict]]:
    """
    Fetch the list of users from the Gravitee Management API v2.
    Handles pagination to retrieve all users across all pages.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of users with filtered information (id, last_connection) or None in case of error
    """
    base_url = config['server_url'].rstrip('/')
    org_id = config['org_id']
    # Users endpoint: /management/organizations/{orgId}/users
    endpoint = f"{base_url}/organizations/{org_id}/users"
    
    auth, headers = get_auth_headers(config)
    
    all_users = []
    page = 1
    per_page = 100
    
    try:
        while True:
            params = {'page': page, 'perPage': per_page}
            print(f"Fetching users page {page} from: {endpoint}", file=sys.stderr)
            
            response = requests.get(endpoint, auth=auth, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                if isinstance(response_data, dict) and 'data' in response_data:
                    page_users = response_data['data']
                    
                    # Filter to only include id and lastConnectionAt
                    filtered_users = []
                    for user in page_users:
                        # lastConnectionAt is a timestamp in milliseconds
                        last_connection = user.get('lastConnectionAt', None)
                        filtered_user = {
                            'id': user.get('id', 'N/A'),
                            'last_connection': last_connection
                        }
                        filtered_users.append(filtered_user)
                    
                    all_users.extend(filtered_users)
                    
                    pagination = response_data.get('pagination', {})
                    page_count = pagination.get('pageCount', 1)
                    current_page = pagination.get('page', page)
                    
                    print(f"  Retrieved {len(page_users)} users from page {current_page}/{page_count}", file=sys.stderr)
                    
                    if current_page >= page_count or len(page_users) == 0:
                        break
                    
                    page += 1
                elif isinstance(response_data, list):
                    # Fallback if response is a list
                    filtered_users = []
                    for user in response_data:
                        last_connection = user.get('lastConnectionAt', None)
                        filtered_user = {
                            'id': user.get('id', 'N/A'),
                            'last_connection': last_connection
                        }
                        filtered_users.append(filtered_user)
                    all_users.extend(filtered_users)
                    break
            elif response.status_code == 401:
                print("Error: Authentication failed when fetching users.", file=sys.stderr)
                return None
            elif response.status_code == 403:
                print("Error: Access denied when fetching users.", file=sys.stderr)
                return None
            elif response.status_code == 404:
                print(f"Warning: Users endpoint not found. Skipping users export.", file=sys.stderr)
                return []
            else:
                print(f"Warning: Server returned status code {response.status_code} when fetching users. Skipping.", file=sys.stderr)
                return []
        
        print(f"Total users retrieved: {len(all_users)}", file=sys.stderr)
        return all_users
            
    except requests.exceptions.RequestException as e:
        print(f"Warning: Error fetching users: {e}. Skipping users export.", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Warning: Unexpected error fetching users: {e}. Skipping users export.", file=sys.stderr)
        return []


def fetch_dictionaries(config: Dict) -> Optional[List[Dict]]:
    """
    Fetch the list of dictionaries from the Gravitee Management API v2.
    Handles pagination to retrieve all dictionaries across all pages.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of dictionaries with filtered information (id, type, propertiesCount) or None in case of error
    """
    base_url = config['server_url'].rstrip('/')
    env_id = config['env_id']
    # API v2 endpoint: /management/v2/environments/{envId}/dictionaries
    endpoint = f"{base_url}/v2/environments/{env_id}/dictionaries"
    
    auth, headers = get_auth_headers(config)
    
    all_dictionaries = []
    page = 1
    per_page = 100
    
    try:
        while True:
            params = {'page': page, 'perPage': per_page}
            print(f"Fetching dictionaries page {page} from: {endpoint}", file=sys.stderr)
            
            response = requests.get(endpoint, auth=auth, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                if isinstance(response_data, dict) and 'data' in response_data:
                    page_dictionaries = response_data['data']
                    
                    # Filter to only include id, type (manual/dynamic), and properties count
                    filtered_dictionaries = []
                    for dictionary in page_dictionaries:
                        # Determine if dictionary is manual or dynamic
                        dictionary_type = dictionary.get('type', 'MANUAL')
                        # Type can be 'MANUAL' or 'DYNAMIC' (or similar)
                        is_dynamic = dictionary_type.upper() in ['DYNAMIC', 'DYNAMIC_CONFIGURATION']
                        type_str = 'dynamic' if is_dynamic else 'manual'
                        
                        # Count properties
                        properties = dictionary.get('properties', {})
                        properties_count = len(properties) if isinstance(properties, dict) else 0
                        
                        filtered_dictionary = {
                            'id': dictionary.get('id', 'N/A'),
                            'type': type_str,
                            'propertiesCount': properties_count
                        }
                        filtered_dictionaries.append(filtered_dictionary)
                    
                    all_dictionaries.extend(filtered_dictionaries)
                    
                    pagination = response_data.get('pagination', {})
                    page_count = pagination.get('pageCount', 1)
                    current_page = pagination.get('page', page)
                    
                    print(f"  Retrieved {len(page_dictionaries)} dictionaries from page {current_page}/{page_count}", file=sys.stderr)
                    
                    if current_page >= page_count or len(page_dictionaries) == 0:
                        break
                    
                    page += 1
                elif isinstance(response_data, list):
                    # Fallback if response is a list
                    filtered_dictionaries = []
                    for dictionary in response_data:
                        dictionary_type = dictionary.get('type', 'MANUAL')
                        is_dynamic = dictionary_type.upper() in ['DYNAMIC', 'DYNAMIC_CONFIGURATION']
                        type_str = 'dynamic' if is_dynamic else 'manual'
                        
                        properties = dictionary.get('properties', {})
                        properties_count = len(properties) if isinstance(properties, dict) else 0
                        
                        filtered_dictionary = {
                            'id': dictionary.get('id', 'N/A'),
                            'type': type_str,
                            'propertiesCount': properties_count
                        }
                        filtered_dictionaries.append(filtered_dictionary)
                    all_dictionaries.extend(filtered_dictionaries)
                    break
            elif response.status_code == 401:
                print("Error: Authentication failed when fetching dictionaries.", file=sys.stderr)
                return None
            elif response.status_code == 403:
                print("Error: Access denied when fetching dictionaries.", file=sys.stderr)
                return None
            elif response.status_code == 404:
                print(f"Warning: Dictionaries endpoint not found. Skipping dictionaries export.", file=sys.stderr)
                return []
            else:
                print(f"Warning: Server returned status code {response.status_code} when fetching dictionaries. Skipping.", file=sys.stderr)
                return []
        
        print(f"Total dictionaries retrieved: {len(all_dictionaries)}", file=sys.stderr)
        return all_dictionaries
            
    except requests.exceptions.RequestException as e:
        print(f"Warning: Error fetching dictionaries: {e}. Skipping dictionaries export.", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Warning: Unexpected error fetching dictionaries: {e}. Skipping dictionaries export.", file=sys.stderr)
        return []


def generate_statistics(apis: List[Dict]) -> Dict:
    """
    Generate statistics from the list of APIs.
    
    Args:
        apis: List of APIs
        
    Returns:
        Dictionary containing statistics
    """
    status_counts = {}
    definition_version_counts = {}
    type_counts = {}
    execution_mode_counts = {}
    
    for api in apis:
        state = api.get('state', 'N/A')
        status_counts[state] = status_counts.get(state, 0) + 1
        
        definition_version = api.get('definitionVersion', 'N/A')
        definition_version_counts[definition_version] = definition_version_counts.get(definition_version, 0) + 1
        
        api_type = api.get('type', 'N/A')
        type_counts[api_type] = type_counts.get(api_type, 0) + 1
        
        execution_mode = api.get('executionMode', 'N/A')
        execution_mode_counts[execution_mode] = execution_mode_counts.get(execution_mode, 0) + 1
    
    return {
        'by_status': status_counts,
        'by_definition_version': definition_version_counts,
        'by_type': type_counts,
        'by_execution_mode': execution_mode_counts
    }


def output_json(apis: List[Dict], config: Dict, output_file: Optional[str] = None) -> None:
    """
    Export APIM statistics and API data in JSON format.
    Only stores the data needed for statistics calculation.
    Uses the export endpoint for each API to get complete details including plans and policies.
    
    Args:
        apis: List of APIs (from list endpoint, contains only basic info)
        config: Configuration dictionary (needed to fetch API details)
        output_file: Optional output file path. If None, outputs to stdout.
    """
    # Filter APIs to only include fields needed for statistics
    filtered_apis = []
    total_apis = len(apis)
    
    print(f"Fetching detailed information for {total_apis} APIs...", file=sys.stderr)
    
    for idx, api in enumerate(apis):
        api_id = api.get('id', 'N/A')
        
        if api_id == 'N/A':
            # Skip APIs without valid ID
            continue
        
        # Fetch complete API details from export endpoint (includes flows, policies, resources)
        api_details = fetch_api_details(api_id, config)
        
        if api_details is None:
            # If we can't fetch details, use basic info from list
            print(f"  Warning: Could not fetch details for API {api_id}, using basic info", file=sys.stderr)
            api_details = api
        
        # Get plans separately (plans are not in the export endpoint)
        plans = get_api_plans(api_id, config)
        
        # Get analytics by plan for the last 30 days
        definition_version = api_details.get('definitionVersion', 'V4')
        analytics_by_plan = get_api_analytics_by_plan(api_id, definition_version, config)
        
        # Add request count to each plan based on analytics
        for plan in plans:
            plan_id = plan.get('id')
            if plan_id and plan_id in analytics_by_plan:
                plan['requestCount30Days'] = analytics_by_plan[plan_id]
            else:
                plan['requestCount30Days'] = 0
        
        # Extract policies from API flows
        api_flows = api_details.get('flows', [])
        policies_list = extract_policies_from_flows(api_flows)
        
        # Also extract policies from plan flows
        for plan in plans:
            plan_flows = plan.get('flows', [])
            if plan_flows:
                plan_policies = extract_policies_from_flows(plan_flows)
                # Add plan policies to the list (avoid duplicates)
                for policy in plan_policies:
                    if policy not in policies_list:
                        policies_list.append(policy)
        
        # Count properties
        properties = api_details.get('properties', [])
        properties_count = len(properties) if isinstance(properties, list) else 0
        
        # Count dynamic properties
        dynamic_properties_count = 0
        if isinstance(properties, list):
            dynamic_properties_count = sum(1 for p in properties if p.get('dynamic', False))
        
        # Count response templates (nested structure: {key: {statusCode: template}})
        response_templates = api_details.get('responseTemplates', {})
        response_templates_count = 0
        if isinstance(response_templates, dict):
            for key, value in response_templates.items():
                if isinstance(value, dict):
                    response_templates_count += len(value)
                else:
                    response_templates_count += 1
        
        # Check if API was created via GKO (Gravitee Kubernetes Operator)
        origin_context = api_details.get('originContext', {})
        is_gko = False
        if isinstance(origin_context, dict):
            is_gko = origin_context.get('origin') == 'KUBERNETES'
        
        # Extract resources
        resources_list = []
        resources = api_details.get('resources', [])
        if isinstance(resources, list):
            for resource in resources:
                if isinstance(resource, dict):
                    resource_type = resource.get('type', 'N/A')
                    # Only add unique resource types
                    if resource_type and resource_type != 'N/A' and resource_type not in resources_list:
                        resources_list.append(resource_type)
        
        filtered_api = {
            'id': api_id,
            'definitionVersion': api_details.get('definitionVersion', 'N/A'),
            'type': api_details.get('type', 'N/A'),
            'executionMode': api_details.get('executionMode', 'N/A'),
            'state': api_details.get('state', 'N/A'),
            'propertiesCount': properties_count,
            'dynamicPropertiesCount': dynamic_properties_count,
            'responseTemplatesCount': response_templates_count,
            'isGKO': is_gko,
            'plans': plans,
            'policies': policies_list,
            'resources': resources_list
        }
        filtered_apis.append(filtered_api)
        
        # Progress indicator
        if (idx + 1) % 10 == 0:
            print(f"  Processed {idx + 1}/{total_apis} APIs...", file=sys.stderr)
    
    statistics = generate_statistics(apis)
    
    # Fetch users
    print("Fetching users...", file=sys.stderr)
    users = fetch_users(config)
    if users is None:
        users = []  # Set to empty list if error occurred
    
    # Fetch dictionaries
    print("Fetching dictionaries...", file=sys.stderr)
    dictionaries = fetch_dictionaries(config)
    if dictionaries is None:
        dictionaries = []  # Set to empty list if error occurred
    
    output_data = {
        'total_apis': len(apis),
        'apis': filtered_apis,
        'statistics': statistics,
        'total_users': len(users) if users else 0,
        'users': users if users else [],
        'total_dictionaries': len(dictionaries) if dictionaries else 0,
        'dictionaries': dictionaries if dictionaries else []
    }
    
    json_output = json.dumps(output_data, indent=2, ensure_ascii=False)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"JSON output written to: {output_file}", file=sys.stderr)
    else:
        print(json_output)


def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Export APIM statistics from the Gravitee Management API"
    )
    parser.add_argument(
        '-c', '--config',
        default=None,
        help='Path to configuration file (default: config.json in project root)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path for JSON format. If not specified, outputs to stdout.'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format instead of formatted table'
    )
    args = parser.parse_args()
    
    # Load configuration (includes API specifications)
    config = load_config(args.config)
    
    # Display loaded API specifications info (only if not JSON output)
    if not args.json:
        if config.get('spec_v1'):
            print(f"✅ API specification v1 loaded (version: {config['spec_v1'].get('info', {}).get('version', 'N/A')})", file=sys.stderr)
        if config.get('spec_v2'):
            print(f"✅ API specification v2 loaded (version: {config['spec_v2'].get('info', {}).get('version', 'N/A')})", file=sys.stderr)
    
    # Fetch APIs from the management API
    apis = fetch_apis(config)
    
    if apis is not None:
        if args.json:
            # Output in JSON format
            output_json(apis, config, args.output)
        else:
            # Display results in formatted table
            display_apis(apis)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

