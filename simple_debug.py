#!/usr/bin/env python3
"""
Simple Debug Script for Kalshi Bitcoin Trading Bot
Quick and easy way to test the trading system
"""

import json
import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import components
from api.kalshi_api import KalshiAPI
from data.data_feed import BitcoinDataFeed
from strategies.bitcoin_strategy import BitcoinStrategy
from execution.trade_executor import TradeExecutor
from risk.risk_manager import RiskManager
from backtesting.backtester import Backtester

def main():
    """Simple debug script"""
    print("🔍 Kalshi Bitcoin Trading Bot - Simple Debug")
    print("=============================================")
    
    try:
        # Load configuration
        with open('config.json', 'r') as f:
            config = json.load(f)
        print("✅ Configuration loaded")
        
        # Initialize components
        print("📊 Initializing components...")
        api = KalshiAPI(config['api'])
        data_feed = BitcoinDataFeed(config['data'])
        risk_manager = RiskManager(config['risk'])
        strategy = BitcoinStrategy(config['strategy'], data_feed)
        executor = TradeExecutor(api, risk_manager)
        backtester = Backtester(strategy, executor, data_feed)
        
        # Enable backtesting mode
        strategy.backtesting_mode = True
        print(f"✅ Components initialized")
        print(f"📈 Data: {len(data_feed.historical_data)} records")
        print(f"📏 Strategy: {config['strategy']['name']}")
        
        # Run backtest
        print("\n🧪 Running backtest...")
        result = backtester.run("2025-06-01", "2026-03-19")
        
        # Show results
        print(f"\n📊 BACKTEST RESULTS:")
        print(f"📈 Total Trades: {result.total_trades}")
        print(f"💰 Winning Trades: {result.winning_trades}")
        print(f"💸 Losing Trades: {result.losing_trades}")
        print(f"🎯 Win Rate: {result.win_rate:.1%}")
        print(f"📈 Total Return: {result.total_return:.1%}")
        print(f"📊 Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"📉 Max Drawdown: {result.max_drawdown:.1%}")
        
        if result.total_trades == 0:
            print("\n⚠️  No trades executed. Try these fixes:")
            print("1. Use more aggressive parameters (lower bb_period, atr_period)")
            print("2. Reduce min_volatility threshold")
            print("3. Try different date ranges")
            print("4. Check data quality and availability")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()