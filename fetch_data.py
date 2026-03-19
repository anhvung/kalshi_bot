#!/usr/bin/env python3
"""
Script to fetch historical Bitcoin data for backtesting
"""

import json
from data.data_feed import BitcoinDataFeed

def main():
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Initialize data feed
    data_feed = BitcoinDataFeed(config['data'])
    
    # Fetch historical data (365 days max for free tier)
    print("Fetching historical data...")
    success = data_feed.refresh_historical_data(days=365)
    
    if success:
        print(f"Successfully fetched {len(data_feed.historical_data)} records")
        print("Data range:", data_feed.historical_data['timestamp'].min(), "to", data_feed.historical_data['timestamp'].max())
        
        # Save the data
        data_feed._save_historical_data()
        print("Data saved to", data_feed.historical_file)
    else:
        print("Failed to fetch historical data")

if __name__ == "__main__":
    main()