import logging
from typing import Dict, Any, List
from datetime import datetime
import csv
import os

logger = logging.getLogger(__name__)

class Monitor:
    """Monitoring and logging for trading bot"""
    
    def __init__(self):
        self.trade_log_file = 'logs/trades.csv'
        self.performance_log_file = 'logs/performance.csv'
        self._initialize_log_files()
    
    def _initialize_log_files(self):
        """Initialize log files with headers"""
        os.makedirs('logs', exist_ok=True)
        
        # Trade log headers
        trade_headers = [
            'timestamp', 'order_id', 'market_id', 'action', 'quantity',
            'price', 'success', 'error', 'capital_after'
        ]
        
        # Performance log headers
        performance_headers = [
            'timestamp', 'capital', 'daily_loss', 'daily_loss_pct',
            'drawdown', 'drawdown_pct', 'active_positions'
        ]
        
        # Create files if they don't exist
        for file_path, headers in [(self.trade_log_file, trade_headers),
                                  (self.performance_log_file, performance_headers)]:
            if not os.path.exists(file_path):
                with open(file_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
    
    def log_trade(self, trade_result: Dict[str, Any]):
        """Log a trade execution"""
        try:
            trade_data = {
                'timestamp': datetime.fromtimestamp(trade_result.get('timestamp', 0)).isoformat(),
                'order_id': trade_result.get('order_id', ''),
                'market_id': trade_result.get('market_id', ''),
                'action': trade_result.get('action', ''),
                'quantity': trade_result.get('quantity', 0),
                'price': trade_result.get('price', 0.0),
                'success': trade_result.get('success', False),
                'error': trade_result.get('error', ''),
                'capital_after': trade_result.get('capital_after', 0.0)
            }
            
            with open(self.trade_log_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=trade_data.keys())
                writer.writerow(trade_data)
            
            log_level = logging.INFO if trade_result.get('success', False) else logging.ERROR
            logger.log(log_level, f"Trade logged: {trade_result.get('action', 'unknown')} "
                      f"{trade_result.get('quantity', 0)} contracts at "
                      f"${trade_result.get('price', 0.0):.2f}")
            
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
    
    def log_performance(self, risk_metrics: Dict[str, float], 
                       active_positions: int = 0):
        """Log performance metrics"""
        try:
            performance_data = {
                'timestamp': datetime.now().isoformat(),
                'capital': risk_metrics.get('current_capital', 0.0),
                'daily_loss': risk_metrics.get('daily_loss', 0.0),
                'daily_loss_pct': risk_metrics.get('daily_loss_pct', 0.0),
                'drawdown': risk_metrics.get('drawdown', 0.0),
                'drawdown_pct': risk_metrics.get('drawdown_pct', 0.0),
                'active_positions': active_positions
            }
            
            with open(self.performance_log_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=performance_data.keys())
                writer.writerow(performance_data)
            
            logger.debug(f"Performance logged: Capital ${performance_data['capital']:.2f}, "
                       f"Drawdown {performance_data['drawdown_pct']:.2%}")
            
        except Exception as e:
            logger.error(f"Error logging performance: {e}")
    
    def log_backtest_results(self, results: Dict[str, Any]):
        """Log backtest results"""
        try:
            log_message = (
                f"Backtest Results:\n"
                f"Total Trades: {results.get('total_trades', 0)}\n"
                f"Winning Trades: {results.get('winning_trades', 0)}\n"
                f"Losing Trades: {results.get('losing_trades', 0)}\n"
                f"Win Rate: {results.get('win_rate', 0.0):.2%}\n"
                f"Total Return: {results.get('total_return', 0.0):.2%}\n"
                f"Sharpe Ratio: {results.get('sharpe_ratio', 0.0):.2f}\n"
                f"Max Drawdown: {results.get('max_drawdown', 0.0):.2%}\n"
                f"Profit Factor: {results.get('profit_factor', 0.0):.2f}\n"
                f"Avg Profit: ${results.get('average_profit', 0.0):.2f}\n"
                f"Avg Loss: ${results.get('average_loss', 0.0):.2f}"
            )
            
            logger.info(log_message)
            
            # Also save to separate file
            with open('logs/backtest_results.txt', 'a') as f:
                f.write(f"\n{datetime.now().isoformat()}\n")
                f.write(log_message)
                f.write("\n" + "="*50 + "\n")
                
        except Exception as e:
            logger.error(f"Error logging backtest results: {e}")
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades from log"""
        try:
            if not os.path.exists(self.trade_log_file):
                return []
            
            with open(self.trade_log_file, 'r') as f:
                reader = csv.DictReader(f)
                trades = list(reader)
                return trades[-limit:] if len(trades) > limit else trades
                
        except Exception as e:
            logger.error(f"Error reading trade log: {e}")
            return []
    
    def get_performance_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent performance metrics"""
        try:
            if not os.path.exists(self.performance_log_file):
                return []
            
            with open(self.performance_log_file, 'r') as f:
                reader = csv.DictReader(f)
                performance = list(reader)
                return performance[-limit:] if len(performance) > limit else performance
                
        except Exception as e:
            logger.error(f"Error reading performance log: {e}")
            return []
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive trading report"""
        try:
            # Get recent data
            recent_trades = self.get_recent_trades(20)
            performance_history = self.get_performance_history(20)
            
            # Calculate summary statistics
            successful_trades = sum(1 for t in recent_trades if t['success'] == 'True')
            total_trades = len(recent_trades)
            
            # Get current performance
            current_performance = performance_history[-1] if performance_history else {}
            
            return {
                'summary': {
                    'total_trades': total_trades,
                    'success_rate': successful_trades / total_trades if total_trades > 0 else 0,
                    'current_capital': current_performance.get('capital', 'N/A'),
                    'current_drawdown': current_performance.get('drawdown_pct', 'N/A')
                },
                'recent_trades': recent_trades,
                'performance_history': performance_history
            }
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {'error': str(e)}
    
    def log_error(self, error: str, context: str = ""):
        """Log an error with context"""
        error_message = f"ERROR: {error}"
        if context:
            error_message += f" | Context: {context}"
        
        logger.error(error_message)
        
        # Also log to error file
        try:
            with open('logs/errors.log', 'a') as f:
                f.write(f"{datetime.now().isoformat()} - {error_message}\n")
        except Exception:
            pass  # Don't fail if error logging fails