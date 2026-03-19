#!/usr/bin/env python3
"""
Kalshi Bitcoin Trading Bot
Main execution script
"""

import logging
from datetime import datetime
from typing import Optional

from api.kalshi_api import KalshiAPI
from data.data_feed import BitcoinDataFeed
from strategies.bitcoin_strategy import BitcoinStrategy
from execution.trade_executor import TradeExecutor
from risk.risk_manager import RiskManager
from backtesting.backtester import Backtester
from monitoring.monitor import Monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('kalshi_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class KalshiBitcoinBot:
    def __init__(self, config: dict):
        """Initialize the trading bot with configuration"""
        self.config = config
        
        # Initialize components
        self.api = KalshiAPI(config['api'])
        self.data_feed = BitcoinDataFeed(config['data'])
        self.risk_manager = RiskManager(config['risk'])
        self.strategy = BitcoinStrategy(config['strategy'], self.data_feed)
        self.executor = TradeExecutor(self.api, self.risk_manager)
        self.monitor = Monitor()
        
        # Backtesting component
        self.backtester = Backtester(
            self.strategy,
            self.executor,
            self.data_feed
        )
    
    def run_backtest(self, start_date: str, end_date: str):
        """Run backtest on historical data"""
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        results = self.backtester.run(start_date, end_date)
        # Convert BacktestResult to dict for monitoring
        if hasattr(results, 'to_dict'):
            self.monitor.log_backtest_results(results.to_dict())
        else:
            self.monitor.log_backtest_results(results)
        return results
    
    def run_live(self):
        """Run live trading session"""
        logger.info("Starting live trading session")
        
        try:
            while True:
                # Update data
                self.data_feed.update_data()
                
                # Get trading signal
                signal = self.strategy.calculate_signal()
                
                if signal:
                    # Execute trade
                    order_result = self.executor.execute_trade(signal)
                    self.monitor.log_trade(order_result)
                
                # Monitor positions and risk
                self.risk_manager.check_risk_limits()
                
                # Sleep for configured interval
                import time
                time.sleep(self.config['trading_interval'])
                
        except KeyboardInterrupt:
            logger.info("Stopping live trading session")
        except Exception as e:
            logger.error(f"Error in live trading: {e}")
            raise

def load_config() -> dict:
    """Load configuration from file"""
    import json
    with open('config.json', 'r') as f:
        return json.load(f)

def main():
    """Main entry point"""
    config = load_config()
    bot = KalshiBitcoinBot(config)
    
    # Uncomment to run backtest
    # bot.run_backtest("2023-01-01", "2023-12-31")
    
    # Run backtest with Yahoo Finance data (2 years of data)
    bot.run_backtest("2024-06-01", "2026-03-19")
    
    # Run live trading
    # bot.run_live()

if __name__ == "__main__":
    main()