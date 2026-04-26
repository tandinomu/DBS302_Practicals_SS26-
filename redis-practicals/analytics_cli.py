#!/usr/bin/env python3
"""
Exercise 3: CLI Script for Daily Active Users and Unique Visitors
Usage: python analytics_cli.py YYYY-MM-DD
Example: python analytics_cli.py 2026-03-17
"""

import sys
import redis
from datetime import datetime


def get_analytics_for_date(date_str: str):
    """
    Get DAU and UV for a given date from Redis.
    """
    try:
        # Validate date format
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Invalid date format. Please use YYYY-MM-DD")
        return
    
    # Connect to Redis
    r = redis.Redis(
        host="127.0.0.1",
        port=6379,
        db=0,
        decode_responses=True,
    )
    
    # Build keys
    dau_key = f"analytics:dau:{date_str}"
    uv_key = f"analytics:uv:{date_str}"
    
    # Get DAU from bitmap
    dau = r.bitcount(dau_key)
    
    # Get UV from HyperLogLog
    uv = r.pfcount(uv_key)
    
    # Display results
    print("\n" + "="*50)
    print(f"Analytics Report for {date_str}")
    print("="*50)
    print(f"Daily Active Users (DAU): {dau}")
    print(f"Unique Visitors (UV):     {uv}")
    print("="*50)
    
    # Show some sample active users if any
    if dau > 0:
        print("\nNote: DAU is exact count from bitmap")
        print("UV is approximate from HyperLogLog (error rate ~0.81%)")


def main():
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python analytics_cli.py YYYY-MM-DD")
        print("Example: python analytics_cli.py 2026-03-17")
        sys.exit(1)
    
    date_str = sys.argv[1]
    get_analytics_for_date(date_str)


if __name__ == "__main__":
    main()