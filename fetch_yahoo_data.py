#!/usr/bin/env python3
"""
Yahoo Finance Data Fetcher
Uses yfinance to fetch extended historical Bitcoin data
"""

import json
import pandas as pd
import yfinance as yf
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('yahoo_data_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def fetch_yahoo_data(ticker: str = 'BTC-USD', period: str = '2y', interval: str = '1d') -> pd.DataFrame:
    """Fetch historical data from Yahoo Finance using yfinance"""
    try:
        logger.info(f"Fetching {period} of {interval} data for {ticker} from Yahoo Finance...")
        
        # Download data
        data = yf.download(ticker, period=period, interval=interval)
        
        if data.empty:
            logger.error("No data returned from Yahoo Finance")
            return pd.DataFrame()
        
        # Clean and format the data
        data = data.reset_index()
        data['timestamp'] = pd.to_datetime(data['Date'])
        data['price'] = data['Close']
        
        # Select relevant columns
        result = data[['timestamp', 'price']].copy()
        
        logger.info(f"Successfully fetched {len(result)} data points from Yahoo Finance")
        logger.info(f"Data range: {result['timestamp'].min()} to {result['timestamp'].max()}")
        logger.info(f"First price: ${result['price'].iloc[0]:,.2f}")
        logger.info(f"Last price: ${result['price'].iloc[-1]:,.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching Yahoo Finance data: {e}")
        return pd.DataFrame()

def save_data_to_csv(data: pd.DataFrame, filename: str = 'data/bitcoin_yahoo.csv'):
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
    logger.info("Starting Yahoo Finance data fetch process...")
    
    # Fetch 2 years of daily data
    yahoo_data = fetch_yahoo_data('BTC-USD', period='2y', interval='1d')
    
    if not yahoo_data.empty:
        # Save the data
        success = save_data_to_csv(yahoo_data)
        
        if success:
            # Create updated config
            config = {
                "bitcoin_source": "yahoo",
                "historical_data_file": "data/bitcoin_yahoo.csv",
                "update_interval": 60,
                "lookback_period": "365d"
            }
            
            with open('config_yahoo.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info("Updated config saved to config_yahoo.json")
            logger.info("Data fetch completed successfully!")
            
            # Show some statistics
            returns = yahoo_data['price'].pct_change().dropna()
            logger.info(f"Average daily return: {returns.mean():.4%}")
            logger.info(f"Volatility: {returns.std():.4%}")
            logger.info(f"Max price: ${yahoo_data['price'].max():,.2f}")
            logger.info(f"Min price: ${yahoo_data['price'].min():,.2f}")
            
        else:
            logger.error("Failed to save data")
    else:
        logger.error("Failed to fetch data from Yahoo Finance")

if __name__ == "__main__":
    main()