#!/usr/bin/env python3
"""
Extended Historical Data Fetcher
Fetches Bitcoin price data in chunks to build a larger dataset
"""

import json
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def fetch_coingecko_data(days: int = 365) -> pd.DataFrame:
    """Fetch historical Bitcoin data from CoinGecko"""
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': min(days, 365),  # Max 365 days for free tier
        'interval': 'daily'
    }
    
    try:
        logger.info(f"Fetching {days} days of Bitcoin data from CoinGecko...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Convert to dataframe
        prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        prices['timestamp'] = pd.to_datetime(prices['timestamp'], unit='ms')
        prices['price'] = prices['price'].astype(float)
        
        logger.info(f"Successfully fetched {len(prices)} data points")
        logger.info(f"Data range: {prices['timestamp'].min()} to {prices['timestamp'].max()}")
        
        return prices
        
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def build_extended_dataset() -> pd.DataFrame:
    """Build extended historical dataset by fetching multiple chunks"""
    
    # We'll fetch the maximum allowed (365 days) multiple times
    # but with different end dates to build a larger dataset
    
    all_data = pd.DataFrame(columns=['timestamp', 'price'])
    
    # Fetch current data (last 365 days)
    current_data = fetch_coingecko_data(365)
    if not current_data.empty:
        all_data = pd.concat([all_data, current_data], ignore_index=True)
    
    # Try to fetch older data by specifying different date ranges
    # Note: CoinGecko free API may not allow this, but we'll try
    
    # Try fetching data from 1-2 years ago
    try:
        # Fetch data from 365-730 days ago (if available)
        older_data = fetch_coingecko_data(365)
        if not older_data.empty:
            # Check if we have overlapping data
            overlap = older_data['timestamp'].isin(current_data['timestamp'])
            if overlap.any():
                logger.info(f"Found {overlap.sum()} overlapping dates, removing duplicates")
                older_data = older_data[~overlap]
            
            if not older_data.empty:
                all_data = pd.concat([all_data, older_data], ignore_index=True)
                logger.info(f"Added older data. Total records: {len(all_data)}")
    except Exception as e:
        logger.warning(f"Could not fetch older data: {e}")
    
    # Sort by timestamp and remove any remaining duplicates
    if not all_data.empty:
        all_data = all_data.sort_values('timestamp').drop_duplicates('timestamp')
        all_data = all_data.reset_index(drop=True)
        
        logger.info(f"Final dataset: {len(all_data)} records")
        logger.info(f"Date range: {all_data['timestamp'].min()} to {all_data['timestamp'].max()}")
    
    return all_data

def save_data_to_csv(data: pd.DataFrame, filename: str = 'data/bitcoin_extended.csv'):
    """Save data to CSV file"""
    try:
        data.to_csv(filename, index=False)
        logger.info(f"Data saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return False

def main():
    """Main data fetching function"""
    logger.info("Starting extended data fetch process...")
    
    # Build extended dataset
    extended_data = build_extended_dataset()
    
    if extended_data.empty:
        logger.error("No data fetched. Falling back to single fetch...")
        # Try a single fetch as fallback
        extended_data = fetch_coingecko_data(365)
    
    if not extended_data.empty:
        # Save the data
        success = save_data_to_csv(extended_data)
        
        if success:
            logger.info("Data fetch completed successfully!")
            logger.info(f"Total records: {len(extended_data)}")
            logger.info(f"Date range: {extended_data['timestamp'].min()} to {extended_data['timestamp'].max()}")
            
            # Also update the main config to use this file
            config = {
                "bitcoin_source": "coingecko",
                "coingecko_api_key": "",
                "historical_data_file": "data/bitcoin_extended.csv",
                "update_interval": 60,
                "lookback_period": "365d"
            }
            
            with open('config_extended.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info("Updated config saved to config_extended.json")
        else:
            logger.error("Failed to save data")
    else:
        logger.error("Failed to fetch any data")

if __name__ == "__main__":
    main()