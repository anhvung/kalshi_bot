#!/usr/bin/env python3
"""
Strategy Parameter Optimization Script
Optimizes the volatility breakout strategy parameters to find profitable settings
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple
import itertools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('optimization.log'),
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
from monitoring.monitor import Monitor

class StrategyOptimizer:
    def __init__(self, config: dict):
        """Initialize the optimizer with configuration"""
        self.config = config
        
        # Initialize components
        self.api = KalshiAPI(config['api'])
        self.data_feed = BitcoinDataFeed(config['data'])
        self.risk_manager = RiskManager(config['risk'])
        self.strategy = BitcoinStrategy(config['strategy'], self.data_feed)
        self.executor = TradeExecutor(self.api, self.risk_manager)
        self.backtester = Backtester(self.strategy, self.executor, self.data_feed)
        
        logger.info("Initialized strategy optimizer")
    
    def optimize_parameters(self, start_date: str, end_date: str,
                          param_ranges: Dict[str, List[float]]) -> Dict[str, Any]:
        """Optimize strategy parameters using grid search"""
        logger.info("Starting parameter optimization")
        
        best_result = None
        best_params = {}
        best_sharpe = -float('inf')
        best_return = -float('inf')
        
        # Generate all parameter combinations
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        
        total_combinations = 1
        for values in param_values:
            total_combinations *= len(values)
        
        logger.info(f"Testing {total_combinations} parameter combinations")
        
        # Test each combination
        combination_num = 0
        for combination in itertools.product(*param_values):
            combination_num += 1
            
            # Create parameter dict for this combination
            current_params = {}
            for i, param_name in enumerate(param_names):
                current_params[param_name] = combination[i]
            
            # Update strategy parameters
            original_params = self.strategy.parameters.copy()
            self.strategy.parameters.update(current_params)
            
            logger.info(f"Testing combination {combination_num}/{total_combinations}: {current_params}")
            
            # Run backtest
            try:
                result = self.backtester.run(start_date, end_date)
                
                # Evaluate results
                if result.total_trades > 0:  # Only consider combinations with trades
                    logger.info(f"  Result: {result.total_trades} trades, "
                              f"Return: {result.total_return:.2%}, "
                              f"Sharpe: {result.sharpe_ratio:.2f}")
                    
                    # Use a composite score: Sharpe ratio + return (weighted)
                    composite_score = (result.sharpe_ratio * 0.6) + (result.total_return * 0.4)
                    
                    if composite_score > (best_sharpe * 0.6 + best_return * 0.4):
                        best_sharpe = result.sharpe_ratio
                        best_return = result.total_return
                        best_result = result
                        best_params = current_params.copy()
                        
                        logger.info(f"  NEW BEST: Composite score {composite_score:.3f}")
                else:
                    logger.info(f"  No trades executed")
                    
            except Exception as e:
                logger.error(f"  Error testing combination: {e}")
            
            # Restore original parameters
            self.strategy.parameters = original_params
        
        logger.info(f"Optimization complete. Best parameters: {best_params}")
        
        if best_result:
            logger.info(f"Best result: {best_result.total_trades} trades, "
                      f"Return: {best_result.total_return:.2%}, "
                      f"Sharpe: {best_result.sharpe_ratio:.2f}")
        else:
            logger.warning("No profitable parameter combinations found")
        
        return {
            'best_params': best_params,
            'best_result': best_result.to_dict() if best_result else None,
            'total_combinations': total_combinations,
            'combinations_tested': combination_num
        }

def load_config() -> dict:
    """Load configuration from file"""
    with open('config.json', 'r') as f:
        return json.load(f)

def main():
    """Main optimization entry point"""
    config = load_config()
    
    # Define parameter ranges to test
    param_ranges = {
        'bb_period': [5, 10, 15, 20],           # Bollinger Bands period
        'bb_std_dev': [1.5, 2.0, 2.5],          # Bollinger Bands standard deviations
        'atr_period': [5, 7, 10, 14],           # ATR period
        'min_volatility': [0.005, 0.01, 0.015] # Minimum volatility threshold
    }
    
    # Create optimizer
    optimizer = StrategyOptimizer(config)
    
    # Run optimization (use a shorter date range for faster testing)
    results = optimizer.optimize_parameters("2025-06-01", "2026-03-19", param_ranges)
    
    # Save results
    with open('optimization_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("Optimization results saved to optimization_results.json")
    
    # Print summary
    print("\n" + "="*50)
    print("OPTIMIZATION SUMMARY")
    print("="*50)
    
    if results['best_result']:
        best_result = results['best_result']
        print(f"Best Parameters: {results['best_params']}")
        print(f"Total Trades: {best_result['total_trades']}")
        print(f"Winning Trades: {best_result['winning_trades']}")
        print(f"Win Rate: {best_result['win_rate']:.2%}")
        print(f"Total Return: {best_result['total_return']:.2%}")
        print(f"Sharpe Ratio: {best_result['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {best_result['max_drawdown']:.2%}")
        print(f"Profit Factor: {best_result['profit_factor']:.2f}")
    else:
        print("No profitable parameter combinations found")
    
    print("="*50)

if __name__ == "__main__":
    main()