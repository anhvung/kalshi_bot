#!/usr/bin/env python3
"""
Simple Strategy Optimization Script
Finds parameters that generate trading signals
"""

import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import the bot components
from api.kalshi_api import KalshiAPI
from data.data_feed import BitcoinDataFeed
from strategies.bitcoin_strategy import BitcoinStrategy
from execution.trade_executor import TradeExecutor
from risk.risk_manager import RiskManager
from backtesting.backtester import Backtester

def load_config() -> dict:
    """Load configuration from file"""
    with open('config.json', 'r') as f:
        return json.load(f)

def test_parameters(config: dict, params: dict) -> bool:
    """Test a parameter combination and return True if it generates trades"""
    # Update config with new parameters
    config['strategy']['parameters'].update(params)
    
    # Initialize components
    api = KalshiAPI(config['api'])
    data_feed = BitcoinDataFeed(config['data'])
    risk_manager = RiskManager(config['risk'])
    strategy = BitcoinStrategy(config['strategy'], data_feed)
    executor = TradeExecutor(api, risk_manager)
    backtester = Backtester(strategy, executor, data_feed)
    
    # Run a quick backtest
    try:
        result = backtester.run("2025-07-01", "2026-03-19")  # Shorter period for speed
        logger.info(f"Params {params}: {result.total_trades} trades, Return: {result.total_return:.2%}")
        return result.total_trades > 0
    except Exception as e:
        logger.error(f"Error testing {params}: {e}")
        return False

def main():
    """Main optimization entry point"""
    config = load_config()
    
    logger.info("Starting simple parameter optimization")
    
    # Test progressively more aggressive parameters
    test_cases = [
        # Very aggressive (low periods, low volatility threshold)
        {'bb_period': 3, 'bb_std_dev': 1.0, 'atr_period': 3, 'min_volatility': 0.001},
        {'bb_period': 3, 'bb_std_dev': 1.5, 'atr_period': 3, 'min_volatility': 0.001},
        
        # Moderately aggressive
        {'bb_period': 5, 'bb_std_dev': 1.5, 'atr_period': 5, 'min_volatility': 0.005},
        {'bb_period': 5, 'bb_std_dev': 2.0, 'atr_period': 5, 'min_volatility': 0.005},
        
        # Current conservative settings
        {'bb_period': 10, 'bb_std_dev': 2.0, 'atr_period': 7, 'min_volatility': 0.01},
        
        # Try with even lower volatility thresholds
        {'bb_period': 7, 'bb_std_dev': 1.5, 'atr_period': 7, 'min_volatility': 0.001},
        {'bb_period': 7, 'bb_std_dev': 1.5, 'atr_period': 7, 'min_volatility': 0.003},
        
        # Try different Bollinger Band settings
        {'bb_period': 5, 'bb_std_dev': 1.0, 'atr_period': 5, 'min_volatility': 0.001},
        {'bb_period': 5, 'bb_std_dev': 1.0, 'atr_period': 5, 'min_volatility': 0.003},
    ]
    
    working_params = []
    
    for i, params in enumerate(test_cases):
        logger.info(f"Testing parameter set {i+1}/{len(test_cases)}: {params}")
        
        if test_parameters(config, params):
            working_params.append(params)
            logger.info(f"✅ SUCCESS: Found working parameters: {params}")
            
            # Save the first working parameters
            with open('working_parameters.json', 'w') as f:
                json.dump({'best_params': params}, f, indent=2)
            break
        else:
            logger.info(f"❌ NO TRADES: {params}")
    
    if working_params:
        logger.info(f"Found {len(working_params)} working parameter set(s)")
        logger.info(f"Best parameters: {working_params[0]}")
        
        # Update config with working parameters
        config['strategy']['parameters'].update(working_params[0])
        
        with open('config_optimized.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info("Updated config saved to config_optimized.json")
    else:
        logger.warning("No parameter combinations generated trades")
        logger.info("Try these manual adjustments:")
        logger.info("1. Reduce bb_period to 3-5")
        logger.info("2. Reduce bb_std_dev to 1.0-1.5")
        logger.info("3. Reduce min_volatility to 0.001-0.005")
        logger.info("4. Use shorter date ranges for testing")

if __name__ == "__main__":
    main()