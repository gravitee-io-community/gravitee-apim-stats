#!/usr/bin/env python3
"""
Script to read JSON output from export_apim_stats.py and display statistics.
"""

import json
import sys
import argparse
from typing import Dict, List
from datetime import datetime, timedelta


def load_json_data(input_file: str = None) -> Dict:
    """
    Load JSON data from file or stdin.
    
    Args:
        input_file: Path to JSON file. If None, reads from stdin.
        
    Returns:
        Dictionary containing the JSON data
    """
    try:
        if input_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = json.load(sys.stdin)
        
        return data
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading JSON data: {e}", file=sys.stderr)
        sys.exit(1)


def display_statistics(data: Dict) -> None:
    """
    Display statistics from JSON data.
    
    Args:
        data: Dictionary containing APIs, users, dictionaries and statistics
    """
    total_apis = data.get('total_apis', 0)
    statistics = data.get('statistics', {})
    
    print(f"\n{'='*80}")
    print(f"API Statistics (Total: {total_apis} APIs)")
    print(f"{'='*80}\n")
    
    # Statistics by status
    if 'by_status' in statistics:
        print("Statistics by status:")
        for status, count in sorted(statistics['by_status'].items()):
            percentage = (count / total_apis * 100) if total_apis > 0 else 0
            print(f"  - {status}: {count} ({percentage:.1f}%)")
        print()
    
    # Statistics by definition version
    if 'by_definition_version' in statistics:
        print("Statistics by definition version:")
        for version, count in sorted(statistics['by_definition_version'].items()):
            percentage = (count / total_apis * 100) if total_apis > 0 else 0
            print(f"  - {version}: {count} ({percentage:.1f}%)")
        print()
    
    # Statistics by type
    if 'by_type' in statistics:
        print("Statistics by type:")
        for api_type, count in sorted(statistics['by_type'].items()):
            percentage = (count / total_apis * 100) if total_apis > 0 else 0
            print(f"  - {api_type}: {count} ({percentage:.1f}%)")
        print()
    
    # Statistics by execution mode
    if 'by_execution_mode' in statistics:
        print("Statistics by execution mode:")
        for mode, count in sorted(statistics['by_execution_mode'].items()):
            percentage = (count / total_apis * 100) if total_apis > 0 else 0
            print(f"  - {mode}: {count} ({percentage:.1f}%)")
        print()
    
    # Users statistics
    total_users = data.get('total_users', 0)
    users = data.get('users', [])
    if total_users > 0:
        print(f"{'='*80}")
        print(f"Users Statistics (Total: {total_users} users)")
        print(f"{'='*80}\n")
        
        # Get current time
        now = datetime.now()
        
        # Initialize counters
        never_connected = 0
        last_7_days = 0
        last_30_days = 0
        last_90_days = 0
        last_180_days = 0
        more_than_180_days = 0
        
        # Calculate time thresholds
        threshold_7_days = now - timedelta(days=7)
        threshold_30_days = now - timedelta(days=30)
        threshold_90_days = now - timedelta(days=90)
        threshold_180_days = now - timedelta(days=180)
        
        # Categorize users by last connection date (cumulative counts)
        for user in users:
            last_connection = user.get('last_connection')
            
            if last_connection is None:
                never_connected += 1
            else:
                # Convert timestamp (milliseconds) to datetime
                try:
                    # Timestamp is in milliseconds, convert to seconds
                    connection_date = datetime.fromtimestamp(last_connection / 1000)
                    
                    # Count cumulatively (users in last 7 days are also in last 30, 90, 180 days)
                    if connection_date >= threshold_7_days:
                        last_7_days += 1
                        last_30_days += 1
                        last_90_days += 1
                        last_180_days += 1
                    elif connection_date >= threshold_30_days:
                        last_30_days += 1
                        last_90_days += 1
                        last_180_days += 1
                    elif connection_date >= threshold_90_days:
                        last_90_days += 1
                        last_180_days += 1
                    elif connection_date >= threshold_180_days:
                        last_180_days += 1
                    else:
                        more_than_180_days += 1
                except (ValueError, OSError, TypeError):
                    # Invalid timestamp, count as never connected
                    never_connected += 1
        
        # Display statistics
        print("Users by last connection period:")
        print(f"  - Last 7 days: {last_7_days} ({last_7_days/total_users*100:.1f}%)")
        print(f"  - Last 30 days: {last_30_days} ({last_30_days/total_users*100:.1f}%)")
        print(f"  - Last 90 days: {last_90_days} ({last_90_days/total_users*100:.1f}%)")
        print(f"  - Last 180 days: {last_180_days} ({last_180_days/total_users*100:.1f}%)")
        print(f"  - More than 180 days: {more_than_180_days} ({more_than_180_days/total_users*100:.1f}%)")
        print(f"  - Never connected: {never_connected} ({never_connected/total_users*100:.1f}%)")
        print()
    
    # Dictionaries statistics
    total_dictionaries = data.get('total_dictionaries', 0)
    dictionaries = data.get('dictionaries', [])
    if total_dictionaries > 0:
        print(f"{'='*80}")
        print(f"Dictionaries Statistics (Total: {total_dictionaries} dictionaries)")
        print(f"{'='*80}\n")
        
        # Count by type
        manual_count = sum(1 for d in dictionaries if d.get('type') == 'manual')
        dynamic_count = sum(1 for d in dictionaries if d.get('type') == 'dynamic')
        
        print("Statistics by type:")
        if manual_count > 0:
            percentage = (manual_count / total_dictionaries * 100) if total_dictionaries > 0 else 0
            print(f"  - manual: {manual_count} ({percentage:.1f}%)")
        if dynamic_count > 0:
            percentage = (dynamic_count / total_dictionaries * 100) if total_dictionaries > 0 else 0
            print(f"  - dynamic: {dynamic_count} ({percentage:.1f}%)")
        print()
        
        # Total properties count
        total_properties = sum(d.get('propertiesCount', 0) for d in dictionaries)
        avg_properties = total_properties / total_dictionaries if total_dictionaries > 0 else 0
        print(f"Total properties across all dictionaries: {total_properties}")
        print(f"Average properties per dictionary: {avg_properties:.1f}")
        print()
    
    # Policies statistics
    apis = data.get('apis', [])
    if apis:
        print(f"{'='*80}")
        print(f"Policies Statistics")
        print(f"{'='*80}\n")
        
        # Collect all policies
        all_policies = []
        policies_count_by_api = {}
        apis_with_policies = 0
        
        for api in apis:
            policies = api.get('policies', [])
            
            if policies:
                apis_with_policies += 1
                for policy in policies:
                    if policy not in all_policies:
                        all_policies.append(policy)
                    # Count usage
                    if policy not in policies_count_by_api:
                        policies_count_by_api[policy] = 0
                    policies_count_by_api[policy] += 1
        
        print(f"APIs with policies: {apis_with_policies} ({apis_with_policies/len(apis)*100:.1f}%)")
        print(f"APIs without policies: {len(apis) - apis_with_policies} ({(len(apis) - apis_with_policies)/len(apis)*100:.1f}%)")
        print()
        
        if all_policies:
            print(f"Total unique policies: {len(all_policies)}")
            print()
            print("Policies usage:")
            for policy in sorted(all_policies):
                count = policies_count_by_api.get(policy, 0)
                percentage = (count / len(apis) * 100) if apis else 0
                print(f"  - {policy}: used in {count} API(s) ({percentage:.1f}%)")
            print()
        else:
            print("No policies found in any API.")
            print()
    
    # Resources statistics
    if apis:
        print(f"{'='*80}")
        print(f"Resources Statistics")
        print(f"{'='*80}\n")
        
        # Collect all resources
        all_resources = []
        resources_count_by_api = {}
        apis_with_resources = 0
        
        for api in apis:
            resources = api.get('resources', [])
            
            if resources:
                apis_with_resources += 1
                for resource in resources:
                    if resource not in all_resources:
                        all_resources.append(resource)
                    # Count usage
                    if resource not in resources_count_by_api:
                        resources_count_by_api[resource] = 0
                    resources_count_by_api[resource] += 1
        
        print(f"APIs with resources: {apis_with_resources} ({apis_with_resources/len(apis)*100:.1f}%)")
        print(f"APIs without resources: {len(apis) - apis_with_resources} ({(len(apis) - apis_with_resources)/len(apis)*100:.1f}%)")
        print()
        
        if all_resources:
            print(f"Total unique resources: {len(all_resources)}")
            print()
            print("Resources usage:")
            for resource in sorted(all_resources):
                count = resources_count_by_api.get(resource, 0)
                percentage = (count / len(apis) * 100) if apis else 0
                print(f"  - {resource}: used in {count} API(s) ({percentage:.1f}%)")
            print()
        else:
            print("No resources found in any API.")
            print()
    
    # TOP 10 APIs by request count
    if apis:
        print(f"{'='*80}")
        print(f"TOP 10 APIs by Request Count (Last 30 Days)")
        print(f"{'='*80}\n")
        
        # Calculate total request count per API (sum of all plans)
        api_request_counts = []
        for api in apis:
            api_id = api.get('id', 'N/A')
            total_requests = 0
            
            # Sum request counts from all plans
            plans = api.get('plans', [])
            for plan in plans:
                request_count = plan.get('requestCount30Days', 0)
                total_requests += request_count
            
            api_request_counts.append({
                'id': api_id,
                'total_requests': total_requests,
                'plan_count': len(plans)
            })
        
        # Sort by total requests (descending) and take top 10
        api_request_counts.sort(key=lambda x: x['total_requests'], reverse=True)
        top_10 = api_request_counts[:10]
        
        if top_10:
            print("Rank | API ID                            | Total Requests | Plans")
            print("-" * 80)
            for idx, api_info in enumerate(top_10, 1):
                api_id_short = api_info['id'][:30] + "..." if len(api_info['id']) > 30 else api_info['id']
                print(f"{idx:4d} | {api_id_short:32s} | {api_info['total_requests']:14d} | {api_info['plan_count']}")
            print()
        else:
            print("No request data available.")
            print()
    
    print(f"{'='*80}\n")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Display statistics from JSON output of export_apim_stats.py"
    )
    parser.add_argument(
        '-i', '--input',
        help='Input JSON file. If not specified, reads from stdin.'
    )
    args = parser.parse_args()
    
    # Load JSON data
    data = load_json_data(args.input)
    
    # Display statistics
    display_statistics(data)


if __name__ == "__main__":
    main()

