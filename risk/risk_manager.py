import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class RiskLimits:
    """Data class for risk limits"""
    max_position_size: float = 0.02  # % of capital
    max_daily_loss: float = 0.05     # % of capital
    stop_loss_pct: float = 0.03      # % per trade
    max_drawdown: float = 0.10      # % of capital
    position_limit: int = 1000      # Max contracts

class RiskManager:
    """Manages trading risk and position sizing"""
    
    def __init__(self, config: dict):
        self.config = config
        
        # Extract risk limits (excluding non-limit parameters)
        risk_limits_config = {k: v for k, v in config.items() 
                             if k in ['max_position_size', 'max_daily_loss', 
                                     'stop_loss_pct', 'max_drawdown', 'position_limit']}
        self.limits = RiskLimits(**risk_limits_config)
        
        # Tracking variables
        self.daily_loss = 0.0
        self.current_positions = {}
        self.max_capital = config.get('initial_capital', 10000.0)
        self.current_capital = self.max_capital
        self.daily_start_capital = self.current_capital
        self.last_reset_time = self._get_midnight()
        
        logger.info(f"Initialized risk manager with limits: {self.limits}")
    
    def _get_midnight(self) -> float:
        """Get timestamp for midnight today"""
        now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.timestamp()
    
    def _reset_daily_limits(self):
        """Reset daily limits at midnight"""
        current_time = time.time()
        if current_time >= self.last_reset_time + 86400:  # 24 hours
            self.daily_loss = 0.0
            self.daily_start_capital = self.current_capital
            self.last_reset_time = self._get_midnight()
            logger.info("Reset daily risk limits")
    
    def update_capital(self, amount: float):
        """Update current capital"""
        self.current_capital += amount
        if amount < 0:
            self.daily_loss += abs(amount)
        
        # Check if we've hit max drawdown
        drawdown = (self.max_capital - self.current_capital) / self.max_capital
        if drawdown >= self.limits.max_drawdown:
            logger.critical(f"Max drawdown reached: {drawdown:.2%}")
            raise Exception("Max drawdown limit reached")
    
    def calculate_position_size(self, signal_confidence: float, 
                               current_price: float) -> int:
        """Calculate position size based on risk parameters"""
        self._reset_daily_limits()
        
        # Check daily loss limit
        daily_loss_pct = self.daily_loss / self.daily_start_capital
        if daily_loss_pct >= self.limits.max_daily_loss:
            logger.warning(f"Daily loss limit reached: {daily_loss_pct:.2%}")
            return 0
        
        # Calculate max position size based on capital
        max_position_value = self.current_capital * self.limits.max_position_size
        
        # Adjust for signal confidence
        confidence_factor = min(1.0, max(0.1, signal_confidence))
        position_value = max_position_value * confidence_factor
        
        # Convert to contract size (assuming 1 contract = $1)
        position_size = int(position_value // current_price)
        
        # Apply position limit
        position_size = min(position_size, self.limits.position_limit)
        
        logger.debug(f"Position size calculated: {position_size} contracts "
                   f"(confidence: {signal_confidence:.2f}, price: ${current_price:.2f})")
        
        return position_size
    
    def check_risk_limits(self) -> bool:
        """Check if any risk limits are being violated"""
        self._reset_daily_limits()
        
        # Check daily loss
        daily_loss_pct = self.daily_loss / self.daily_start_capital
        if daily_loss_pct >= self.limits.max_daily_loss:
            logger.error(f"Daily loss limit violated: {daily_loss_pct:.2%} >= {self.limits.max_daily_loss:.2%}")
            return False
        
        # Check drawdown
        drawdown = (self.max_capital - self.current_capital) / self.max_capital
        if drawdown >= self.limits.max_drawdown:
            logger.error(f"Max drawdown violated: {drawdown:.2%} >= {self.limits.max_drawdown:.2%}")
            return False
        
        logger.debug(f"Risk check passed - Daily loss: {daily_loss_pct:.2%}, "
                   f"Drawdown: {drawdown:.2%}")
        return True
    
    def get_risk_metrics(self) -> Dict[str, float]:
        """Get current risk metrics"""
        self._reset_daily_limits()
        
        return {
            'current_capital': self.current_capital,
            'daily_loss': self.daily_loss,
            'daily_loss_pct': self.daily_loss / self.daily_start_capital if self.daily_start_capital > 0 else 0,
            'drawdown': (self.max_capital - self.current_capital) / self.max_capital if self.max_capital > 0 else 0,
            'drawdown_pct': (self.max_capital - self.current_capital) / self.max_capital if self.max_capital > 0 else 0
        }
    
    def should_stop_trading(self) -> bool:
        """Check if trading should be stopped due to risk limits"""
        self._reset_daily_limits()
        
        daily_loss_pct = self.daily_loss / self.daily_start_capital
        drawdown = (self.max_capital - self.current_capital) / self.max_capital
        
        if daily_loss_pct >= self.limits.max_daily_loss:
            logger.warning("Stopping trading: Daily loss limit reached")
            return True
        
        if drawdown >= self.limits.max_drawdown:
            logger.warning("Stopping trading: Max drawdown reached")
            return True
        
        return False