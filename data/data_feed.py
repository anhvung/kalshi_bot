import requests
import pandas as pd
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

class BitcoinDataFeed:
    """Handles Bitcoin price data from various sources"""
    
    def __init__(self, config: dict):
        self.config = config
        self.source = config.get('bitcoin_source', 'coingecko')
        self.api_key = config.get('coingecko_api_key')
        self.historical_file = config.get('historical_data_file', 'data/bitcoin_historical.csv')
        self.update_interval = config.get('update_interval', 60)
        self.lookback_period = config.get('lookback_period', '7d')
        
        # Initialize data storage
        self.current_price = None
        self.historical_data = None
        self.last_update = 0
        
        # Load historical data
        self._load_historical_data()
    
    def _load_historical_data(self):
        """Load historical data from file or initialize new dataset"""
        try:
            if os.path.exists(self.historical_file):
                self.historical_data = pd.read_csv(self.historical_file, parse_dates=['timestamp'])
                logger.info(f"Loaded historical data with {len(self.historical_data)} records")
                logger.info(f"Data range: {self.historical_data['timestamp'].min()} to {self.historical_data['timestamp'].max()}")
            else:
                # Create empty dataframe with proper structure
                self.historical_data = pd.DataFrame(columns=['timestamp', 'price', 'volume'])
                logger.info("Created new historical data file")
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            self.historical_data = pd.DataFrame(columns=['timestamp', 'price', 'volume'])
    
    def _save_historical_data(self):
        """Save historical data to file"""
        try:
            os.makedirs(os.path.dirname(self.historical_file), exist_ok=True)
            self.historical_data.to_csv(self.historical_file, index=False)
        except Exception as e:
            logger.error(f"Error saving historical data: {e}")
    
    def _fetch_coingecko_data(self) -> Dict[str, Any]:
        """Fetch Bitcoin data from CoinGecko API"""
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'bitcoin',
            'vs_currencies': 'usd',
            'include_market_cap': 'true',
            'include_24hr_vol': 'true',
            'include_24hr_change': 'true'
        }
        
        if self.api_key:
            params['x_cg_demo_api_key'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching CoinGecko data: {e}")
            return None
    
    def _fetch_historical_data(self, days: int = 7) -> pd.DataFrame:
        """Fetch historical Bitcoin data"""
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': min(days, 365)  # Max 365 days for free tier
        }
        
        # Don't use API key for free tier to avoid 401 errors
        # if self.api_key:
        #     params['x_cg_demo_api_key'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Convert to dataframe
            prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
            prices['timestamp'] = pd.to_datetime(prices['timestamp'], unit='ms')
            prices['price'] = prices['price'].astype(float)
            
            return prices
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def update_data(self) -> bool:
        """Update current Bitcoin price data"""
        current_time = time.time()
        
        # Only update if interval has passed
        if current_time - self.last_update < self.update_interval:
            return False
        
        try:
            if self.source == 'coingecko':
                data = self._fetch_coingecko_data()
                if data and 'bitcoin' in data:
                    self.current_price = data['bitcoin']['usd']
                    self.last_update = current_time
                    
                    # Add to historical data
                    new_record = pd.DataFrame({
                        'timestamp': [datetime.now()],
                        'price': [self.current_price],
                        'volume': [data['bitcoin'].get('usd_24h_vol', 0)]
                    })
                    
                    if self.historical_data is not None:
                        self.historical_data = pd.concat([self.historical_data, new_record], ignore_index=True)
                        # Only save during live trading, not backtesting
                        import sys
                        if 'main.py' in sys.argv[0] and not any('backtest' in arg for arg in sys.argv):
                            self._save_historical_data()
                    
                    logger.info(f"Updated Bitcoin price: ${self.current_price:,.2f}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating data: {e}")
            return False
    
    def get_current_price(self) -> Optional[float]:
        """Get current Bitcoin price"""
        if self.current_price is None:
            self.update_data()
        return self.current_price
    
    def get_historical_data(self, lookback: Optional[str] = None) -> pd.DataFrame:
        """Get historical data with optional lookback period"""
        if lookback:
            lookback_days = int(lookback.replace('d', ''))
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            return self.historical_data[self.historical_data['timestamp'] >= cutoff_date]
        return self.historical_data
    
    def refresh_historical_data(self, days: int = 7):
        """Refresh historical data from API"""
        historical = self._fetch_historical_data(days)
        if not historical.empty:
            self.historical_data = historical
            self._save_historical_data()
            logger.info(f"Refreshed historical data with {len(historical)} records")
            return True
        return False
    
    def calculate_volatility(self, period: int = 20) -> float:
        """Calculate historical volatility"""
        if self.historical_data is None or len(self.historical_data) < period:
            return 0.0
        
        try:
            returns = self.historical_data['price'].pct_change()
            rolling_std = returns.rolling(window=period).std()
            
            # Safely get the last valid volatility value
            if len(rolling_std.dropna()) > 0:
                volatility = rolling_std.dropna().iloc[-1]
                return volatility if not pd.isna(volatility) else 0.0
            else:
                return 0.0
        except (IndexError, KeyError):
            return 0.0