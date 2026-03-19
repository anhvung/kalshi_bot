#!/usr/bin/env python3
"""
Alternative Data Source Fetcher
Tries multiple free APIs to get extended historical Bitcoin data
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
        logging.FileHandler('alternative_data_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def fetch_binance_data(symbol: str = 'BTCUSDT', interval: str = '1d', limit: int = 1000) -> pd.DataFrame:
    """Fetch historical data from Binance API"""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    
    try:
        logger.info(f"Fetching {limit} {interval} candles from Binance for {symbol}...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Convert to dataframe
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convert timestamps and prices
        df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
        df['price'] = df['close'].astype(float)
        
        # Select relevant columns
        result = df[['timestamp', 'price']].copy()
        
        logger.info(f"Successfully fetched {len(result)} data points from Binance")
        logger.info(f"Data range: {result['timestamp'].min()} to {result['timestamp'].max()}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching Binance data: {e}")
        return pd.DataFrame()

def fetch_yahoo_finance_data() -> pd.DataFrame:
    """Fetch historical data from Yahoo Finance"""
    # Note: This would normally use yfinance library, but we'll try a direct approach
    try:
        logger.info("Attempting to fetch data from Yahoo Finance...")
        
        # Yahoo Finance requires a different approach - this is a placeholder
        # In practice, you would use the yfinance library:
        # import yfinance as yf
        # data = yf.download("BTC-USD", period="2y", interval="1d")
        
        logger.warning("Yahoo Finance requires yfinance library. Skipping.")
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error fetching Yahoo Finance data: {e}")
        return pd.DataFrame()

def fetch_cryptocompare_data() -> pd.DataFrame:
    """Fetch historical data from CryptoCompare"""
    url = "https://min-api.cryptocompare.com/data/v2/histoday"
    params = {
        'fsym': 'BTC',
        'tsym': 'USD',
        'limit': 2000,  # Max allowed by free tier
        'api_key': ''  # Add your API key if available
    }
    
    try:
        logger.info("Fetching data from CryptoCompare...")
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if data.get('Response') == 'Success':
            df = pd.DataFrame(data['Data'])
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            df['price'] = df['close']
            result = df[['timestamp', 'price']].copy()
            
            logger.info(f"Successfully fetched {len(result)} data points from CryptoCompare")
            logger.info(f"Data range: {result['timestamp'].min()} to {result['timestamp'].max()}")
            return result
        else:
            logger.error(f"CryptoCompare API error: {data.get('Message', 'Unknown error')}")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error fetching CryptoCompare data: {e}")
        return pd.DataFrame()

def combine_data_sources() -> pd.DataFrame:
    """Try multiple data sources and combine results"""
    all_data = pd.DataFrame(columns=['timestamp', 'price'])
    
    # Try Binance first (usually most reliable)
    binance_data = fetch_binance_data()
    if not binance_data.empty:
        all_data = binance_data.copy()
    
    # Try CryptoCompare if Binance didn't work or we want more data
    if len(all_data) < 1000:  # If we have less than 1000 records
        cryptocompare_data = fetch_cryptocompare_data()
        if not cryptocompare_data.empty:
            # Combine and remove duplicates
            combined = pd.concat([all_data, cryptocompare_data], ignore_index=True)
            combined = combined.sort_values('timestamp').drop_duplicates('timestamp')
            all_data = combined.copy()
            logger.info(f"Combined data sources. Total records: {len(all_data)}")
    
    return all_data

def save_data_to_csv(data: pd.DataFrame, filename: str = 'data/bitcoin_alternative.csv'):
    """Save data to CSV file"""
    try:
        if not data.empty:
            data.to_csv(filename, index=False)
            logger.info(f"Data saved to {filename}")
            return True
        else:
            logger.error("No data to save")
            return False
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return False

def main():
    """Main data fetching function"""
    logger.info("Starting alternative data source fetch process...")
    
    # Try to combine data from multiple sources
    alternative_data = combine_data_sources()
    
    if not alternative_data.empty:
        logger.info(f"Total records fetched: {len(alternative_data)}")
        logger.info(f"Date range: {alternative_data['timestamp'].min()} to {alternative_data['timestamp'].max()}")
        
        # Save the data
        success = save_data_to_csv(alternative_data)
        
        if success:
            # Create updated config
            config = {
                "bitcoin_source": "binance",  # or "cryptocompare" depending on what worked
                "historical_data_file": "data/bitcoin_alternative.csv",
                "update_interval": 60,
                "lookback_period": "365d"
            }
            
            with open('config_alternative.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info("Updated config saved to config_alternative.json")
            logger.info("Data fetch completed successfully!")
        else:
            logger.error("Failed to save data")
    else:
        logger.error("Failed to fetch data from any alternative source")
        logger.info("Consider:")
        logger.info("1. Installing yfinance library for Yahoo Finance data")
        logger.info("2. Getting a CoinGecko API key for extended history")
        logger.info("3. Using paid data sources for more comprehensive data")

if __name__ == "__main__":
    main()