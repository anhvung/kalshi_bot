#!/usr/bin/env python3
"""
Simple Debugging Notebook for Kalshi Bitcoin Trading Bot
Run this script to execute backtests and debug the trading system
"""

import json
import pandas as pd
import logging
from datetime import datetime
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging for debugging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for maximum information
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_notebook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import bot components
from api.kalshi_api import KalshiAPI
from data.data_feed import BitcoinDataFeed
from strategies.bitcoin_strategy import BitcoinStrategy
from execution.trade_executor import TradeExecutor
from risk.risk_manager import RiskManager
from backtesting.backtester import Backtester
from monitoring.monitor import Monitor

def load_config(config_file='config.json'):
    """Load configuration from file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded config from {config_file}")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def debug_data_loading():
    """Debug data loading process"""
    logger.info("\n=== DEBUGGING DATA LOADING ===")
    
    # Test different config files
    config_files = ['config.json', 'config_yahoo.json', 'config_extended.json']
    
    for config_file in config_files:
        if os.path.exists(config_file):
            logger.info(f"Testing {config_file}...")
            config = load_config(config_file)
            if config:
                try:
                    data_feed = BitcoinDataFeed(config['data'])
                    logger.info(f"Data feed initialized: {len(data_feed.historical_data)} records")
                    logger.info(f"Data range: {data_feed.historical_data['timestamp'].min()} to {data_feed.historical_data['timestamp'].max()}")
                    logger.info(f"Current price: ${data_feed.get_current_price():,.2f}")
                    break
                except Exception as e:
                    logger.error(f"Error with {config_file}: {e}")
        else:
            logger.warning(f"Config file not found: {config_file}")

def debug_strategy_calculation(config):
    """Debug strategy signal calculation"""
    logger.info("\n=== DEBUGGING STRATEGY CALCULATION ===")
    
    try:
        # Initialize components
        data_feed = BitcoinDataFeed(config['data'])
        strategy = BitcoinStrategy(config['strategy'], data_feed)
        
        # Enable backtesting mode to avoid data corruption
        strategy.backtesting_mode = True
        
        # Test signal calculation with different data subsets
        test_dates = [
            ("2025-01-01", "2025-01-31"),  # Short period
            ("2025-06-01", "2025-06-30"),  # Medium period
            ("2025-01-01", "2026-03-19"),  # Full period
        ]
        
        for start_date, end_date in test_dates:
            logger.info(f"\nTesting period: {start_date} to {end_date}")
            
            # Filter data for this period
            historical = data_feed.get_historical_data()
            mask = (historical['timestamp'] >= start_date) & (historical['timestamp'] <= end_date)
            period_data = historical.loc[mask]
            
            logger.info(f"Data points in period: {len(period_data)}")
            
            if len(period_data) >= max(config['strategy']['parameters']['bb_period'], 
                                     config['strategy']['parameters']['atr_period']):
                # Update data feed with period data
                data_feed.historical_data = period_data
                
                # Test signal calculation
                for i in range(min(10, len(period_data))):  # Test first 10 days
                    data_feed.current_price = period_data.iloc[i]['price']
                    signal = strategy.calculate_signal()
                    if signal:
                        logger.info(f"Day {i+1}: {signal.action} signal (confidence: {signal.confidence:.2f})")
                    else:
                        logger.debug(f"Day {i+1}: No signal")
            else:
                logger.warning(f"Insufficient data for indicators (need {max(config['strategy']['parameters']['bb_period'], config['strategy']['parameters']['atr_period'])} points)")
                
    except Exception as e:
        logger.error(f"Strategy calculation error: {e}")
        import traceback
        traceback.print_exc()

def run_backtest_with_debugging(config, start_date, end_date):
    """Run backtest with detailed debugging"""
    logger.info(f"\n=== RUNNING BACKTEST: {start_date} to {end_date} ===")
    
    try:
        # Initialize components
        api = KalshiAPI(config['api'])
        data_feed = BitcoinDataFeed(config['data'])
        risk_manager = RiskManager(config['risk'])
        strategy = BitcoinStrategy(config['strategy'], data_feed)
        executor = TradeExecutor(api, risk_manager)
        backtester = Backtester(strategy, executor, data_feed)
        
        # Enable backtesting mode
        strategy.backtesting_mode = True
        
        logger.info("Starting backtest...")
        result = backtester.run(start_date, end_date)
        
        logger.info(f"\nBacktest Results:")
        logger.info(f"Total Trades: {result.total_trades}")
        logger.info(f"Winning Trades: {result.winning_trades}")
        logger.info(f"Losing Trades: {result.losing_trades}")
        logger.info(f"Win Rate: {result.win_rate:.2%}")
        logger.info(f"Total Return: {result.total_return:.2%}")
        logger.info(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        logger.info(f"Max Drawdown: {result.max_drawdown:.2%}")
        
        return result
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_different_parameters(config):
    """Test strategy with different parameter sets"""
    logger.info("\n=== TESTING DIFFERENT PARAMETERS ===")
    
    # Define parameter sets to test
    param_sets = [
        {"bb_period": 5, "bb_std_dev": 1.5, "atr_period": 5, "min_volatility": 0.005},
        {"bb_period": 10, "bb_std_dev": 2.0, "atr_period": 7, "min_volatility": 0.01},
        {"bb_period": 3, "bb_std_dev": 1.0, "atr_period": 3, "min_volatility": 0.001},
    ]
    
    for i, params in enumerate(param_sets):
        logger.info(f"\nTesting parameter set {i+1}: {params}")
        
        # Update config with new parameters
        original_params = config['strategy']['parameters'].copy()
        config['strategy']['parameters'].update(params)
        
        # Run quick backtest
        result = run_backtest_with_debugging(config, "2025-06-01", "2026-03-19")
        
        # Restore original parameters
        config['strategy']['parameters'] = original_params
        
        if result and result.total_trades > 0:
            logger.info(f"✅ SUCCESS: {result.total_trades} trades, Return: {result.total_return:.2%}")
        else:
            logger.info(f"❌ NO TRADES: Adjust parameters or check data")

def main():
    """Main debugging notebook entry point"""
    logger.info("🚀 Starting Kalshi Bitcoin Trading Bot Debugging Notebook")
    logger.info("=====================================================")
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        return
    
    # Run debugging steps
    debug_data_loading()
    debug_strategy_calculation(config)
    
    # Run backtest with default parameters
    run_backtest_with_debugging(config, "2025-06-01", "2026-03-19")
    
    # Test different parameters
    test_different_parameters(config)
    
    logger.info("\n=== DEBUGGING COMPLETE ===")
    logger.info("Check debug_notebook.log for detailed information")
    logger.info("To run specific tests, modify this script and run: python debug_notebook.py")

if __name__ == "__main__":
    main()