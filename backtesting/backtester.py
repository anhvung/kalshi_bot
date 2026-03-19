import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class BacktestResult:
    """Data class for backtest results"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    average_profit: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_return': self.total_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'average_profit': self.average_profit,
            'average_loss': self.average_loss,
            'profit_factor': self.profit_factor
        }

class Backtester:
    """Backtesting engine for trading strategies"""
    
    def __init__(self, strategy: Any, executor: Any, data_feed: Any):
        self.strategy = strategy
        self.executor = executor
        self.data_feed = data_feed
        
    def _simulate_trade(self, signal: Any, current_price: float, 
                       risk_manager: Any) -> Dict[str, Any]:
        """Simulate a trade execution"""
        # Calculate position size (using risk manager logic)
        position_size = risk_manager.calculate_position_size(signal.confidence, current_price)
        
        if position_size <= 0:
            return {
                'executed': False,
                'reason': 'Position size too small'
            }
        
        # Simulate order execution with some slippage
        slippage = current_price * 0.001  # 0.1% slippage
        execution_price = current_price + slippage if signal.action == 'buy' else current_price - slippage
        
        # Calculate outcome (simplified - in reality would use next candle)
        # For this simulation, we'll assume a small profit/loss based on signal confidence
        price_change = np.random.normal(0, 0.005)  # Random price movement
        exit_price = execution_price * (1 + price_change)
        
        pnl = (exit_price - execution_price) * position_size if signal.action == 'buy' else \
              (execution_price - exit_price) * position_size
        
        return {
            'executed': True,
            'action': signal.action,
            'position_size': position_size,
            'entry_price': execution_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'confidence': signal.confidence,
            'timestamp': datetime.now().timestamp()
        }
    
    def run(self, start_date: str, end_date: str, initial_capital: float = 10000.0) -> BacktestResult:
        """Run backtest on historical data"""
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        try:
            # Get historical data directly from data feed's storage
            historical_data = self.data_feed.historical_data
            if historical_data is None or historical_data.empty:
                logger.error("No historical data available for backtesting")
                return BacktestResult()
            
            # Filter by date range
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            mask = (historical_data['timestamp'] >= start_dt) & (historical_data['timestamp'] <= end_dt)
            backtest_data = historical_data.loc[mask]
            
            if backtest_data.empty:
                logger.error(f"No data available for date range {start_date} to {end_date}")
                return BacktestResult()
            
            # Initialize backtest variables
            capital = initial_capital
            peak_capital = initial_capital
            trades = []
            
            # Enable backtesting mode for strategy
            self.strategy.backtesting_mode = True
            
            # Create a mock risk manager for backtesting
            from risk.risk_manager import RiskManager
            mock_config = {
                'max_position_size': 0.02,
                'max_daily_loss': 1.0,  # Disable for backtesting
                'stop_loss_pct': 0.03,
                'max_drawdown': 1.0,   # Disable for backtesting
                'position_limit': 1000,
                'initial_capital': initial_capital
            }
            risk_manager = RiskManager(mock_config)
            
            # Simulate trading day by day
            for i in range(len(backtest_data)):
                current_row = backtest_data.iloc[i]
                current_price = current_row['price']
                
                # Update data feed with current data point
                self.data_feed.current_price = current_price
                
                # Update historical data up to current point for strategy calculations
                historical_up_to_now = backtest_data.iloc[:i+1]
                self.data_feed.historical_data = historical_up_to_now
                
                # Get trading signal (don't call update_data to avoid saving partial data)
                signal = self.strategy.calculate_signal()
                
                if signal and signal.action:
                    # Simulate trade
                    trade_result = self._simulate_trade(signal, current_price, risk_manager)
                    
                    if trade_result['executed']:
                        # Update capital
                        capital += trade_result['pnl']
                        
                        # Update peak capital for drawdown calculation
                        if capital > peak_capital:
                            peak_capital = capital
                        
                        # Record trade
                        trade_result['capital_after'] = capital
                        trades.append(trade_result)
                        
                        logger.debug(f"Simulated {signal.action} trade: PnL ${trade_result['pnl']:.2f}, "
                                   f"Capital: ${capital:.2f}")
            
            # Calculate backtest metrics
            if trades:
                result = self._calculate_metrics(trades, initial_capital, peak_capital)
                logger.info(f"Backtest completed: {result.total_trades} trades, "
                          f"Total return: {result.total_return:.2%}")
                return result
            else:
                logger.warning("No trades executed during backtest period")
                return BacktestResult()
                
        except Exception as e:
            logger.error(f"Error during backtest: {e}")
            return BacktestResult()
    
    def _calculate_metrics(self, trades: List[Dict[str, Any]], 
                          initial_capital: float, peak_capital: float) -> BacktestResult:
        """Calculate performance metrics from trade results"""
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['pnl'] > 0)
        losing_trades = total_trades - winning_trades
        
        if total_trades > 0:
            win_rate = winning_trades / total_trades
            
            # Calculate returns
            total_return = (trades[-1]['capital_after'] - initial_capital) / initial_capital
            
            # Calculate average profit and loss
            profits = [t['pnl'] for t in trades if t['pnl'] > 0]
            losses = [t['pnl'] for t in trades if t['pnl'] < 0]
            
            avg_profit = sum(profits) / len(profits) if profits else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            profit_factor = sum(profits) / abs(sum(losses)) if losses else float('inf')
            
            # Calculate Sharpe ratio (simplified)
            trade_returns = [t['pnl'] / initial_capital for t in trades]
            mean_return = sum(trade_returns) / total_trades
            std_return = np.std(trade_returns) if len(trade_returns) > 1 else 0
            sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0
            
            # Calculate max drawdown
            max_drawdown = (peak_capital - trades[-1]['capital_after']) / peak_capital
            
            return BacktestResult(
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                average_profit=avg_profit,
                average_loss=avg_loss,
                profit_factor=profit_factor
            )
        
        return BacktestResult()
    
    def optimize_strategy(self, start_date: str, end_date: str, 
                         param_grid: Dict[str, List[float]]) -> Dict[str, Any]:
        """Optimize strategy parameters using grid search"""
        logger.info("Starting strategy optimization")
        
        best_result = None
        best_params = {}
        best_metric = -float('inf')
        
        # This is a simplified grid search - in production you'd use more sophisticated methods
        for bb_period in param_grid.get('bb_period', [20]):
            for bb_std_dev in param_grid.get('bb_std_dev', [2.0]):
                for atr_period in param_grid.get('atr_period', [14]):
                    for min_volatility in param_grid.get('min_volatility', [0.015]):
                        # Update strategy parameters
                        original_params = self.strategy.parameters.copy()
                        self.strategy.parameters.update({
                            'bb_period': bb_period,
                            'bb_std_dev': bb_std_dev,
                            'atr_period': atr_period,
                            'min_volatility': min_volatility
                        })
                        
                        # Run backtest
                        result = self.run(start_date, end_date)
                        
                        # Use Sharpe ratio as optimization metric
                        if result.sharpe_ratio > best_metric:
                            best_metric = result.sharpe_ratio
                            best_result = result
                            best_params = {
                                'bb_period': bb_period,
                                'bb_std_dev': bb_std_dev,
                                'atr_period': atr_period,
                                'min_volatility': min_volatility
                            }
                        
                        # Restore original parameters
                        self.strategy.parameters = original_params
        
        logger.info(f"Optimization complete. Best Sharpe ratio: {best_metric:.2f} "
                  f"with params: {best_params}")
        
        return {
            'best_params': best_params,
            'best_result': best_result.to_dict() if best_result else None,
            'best_metric': best_metric
        }