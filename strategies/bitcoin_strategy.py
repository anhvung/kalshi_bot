import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TradingSignal:
    """Data class for trading signals"""
    action: str  # 'buy', 'sell', or None
    confidence: float  # 0-1 confidence score
    reason: str  # Human-readable reason
    market_id: Optional[str] = None
    price: Optional[float] = None
    
class BitcoinStrategy:
    """Volatility-based Bitcoin trading strategy for Kalshi markets"""
    
    def __init__(self, config: dict, data_feed: Any):
        self.config = config
        self.data_feed = data_feed
        self.parameters = config.get('parameters', {})
        
        # Strategy parameters with defaults
        self.bb_period = self.parameters.get('bb_period', 20)
        self.bb_std_dev = self.parameters.get('bb_std_dev', 2.0)
        self.atr_period = self.parameters.get('atr_period', 14)
        self.min_volatility = self.parameters.get('min_volatility', 0.015)
        self.max_spread = self.parameters.get('max_spread', 0.05)
        self.backtesting_mode = False
        
        logger.info(f"Initialized {self.config.get('name', 'bitcoin')} strategy")
    
    def _calculate_bollinger_bands(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        if len(prices) < self.bb_period:
            return {'upper': prices, 'middle': prices, 'lower': prices}
        
        rolling_mean = prices.rolling(window=self.bb_period).mean()
        rolling_std = prices.rolling(window=self.bb_period).std()
        
        return {
            'upper': rolling_mean + (rolling_std * self.bb_std_dev),
            'middle': rolling_mean,
            'lower': rolling_mean - (rolling_std * self.bb_std_dev)
        }
    
    def _calculate_atr(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        if len(prices) < period:
            return pd.Series([0.0] * len(prices), index=prices.index)
        
        high = prices
        low = prices
        close = prices
        
        tr = pd.DataFrame({
            'h-l': high - low,
            'h-c': abs(high - close.shift()),
            'l-c': abs(low - close.shift())
        }).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        return atr
    
    def _calculate_market_conditions(self) -> Dict[str, Any]:
        """Calculate current market conditions"""
        # Get historical data - use full dataset if available for backtesting
        historical = self.data_feed.historical_data
        if historical is None or len(historical) < max(self.bb_period, self.atr_period):
            # Fall back to lookback period if not enough data
            historical = self.data_feed.get_historical_data(self.data_feed.lookback_period)
            if len(historical) < max(self.bb_period, self.atr_period):
                logger.warning("Insufficient historical data for calculations")
                return {}
        
        prices = historical['price']
        
        # Calculate indicators
        bb = self._calculate_bollinger_bands(prices)
        atr = self._calculate_atr(prices, self.atr_period)
        volatility = self.data_feed.calculate_volatility(self.bb_period)
        
        # Get the last valid values (handle NaN values properly)
        try:
            last_bb_upper = bb['upper'].dropna().iloc[-1] if len(bb['upper'].dropna()) > 0 else None
            last_bb_middle = bb['middle'].dropna().iloc[-1] if len(bb['middle'].dropna()) > 0 else None
            last_bb_lower = bb['lower'].dropna().iloc[-1] if len(bb['lower'].dropna()) > 0 else None
            last_atr = atr.dropna().iloc[-1] if len(atr.dropna()) > 0 else None
            
            # Check if we have valid data
            if None in [last_bb_upper, last_bb_middle, last_bb_lower, last_atr]:
                logger.debug("Insufficient valid data points for indicator calculations")
                return {}
            
            # Safely get current price
            if len(prices) == 0:
                logger.debug("Empty price series")
                return {}
            current_price = prices.iloc[-1]
            
            return {
                'price': current_price,
                'bb_upper': last_bb_upper,
                'bb_middle': last_bb_middle,
                'bb_lower': last_bb_lower,
                'atr': last_atr,
                'volatility': volatility,
                'price_above_upper': current_price > last_bb_upper,
                'price_below_lower': current_price < last_bb_lower
            }
        except (IndexError, KeyError) as e:
            logger.debug(f"Error accessing indicator values: {e}")
            return {}
    
    def calculate_signal(self) -> Optional[TradingSignal]:
        """Calculate trading signal based on current market conditions"""
        try:
            # Update data (skip during backtesting to avoid saving partial datasets)
            if not self.backtesting_mode:
                self.data_feed.update_data()
            
            # Calculate market conditions
            conditions = self._calculate_market_conditions()
            
            if not conditions:
                return None
            
            # Check if we have all required data
            required_fields = ['price', 'volatility', 'price_above_upper', 'price_below_lower']
            if not all(field in conditions for field in required_fields):
                logger.warning("Missing required fields in market conditions")
                return None
            
            current_price = conditions['price']
            volatility = conditions['volatility']
            
            # Check minimum volatility requirement
            if volatility < self.min_volatility:
                logger.debug(f"Volatility too low: {volatility:.4f} < {self.min_volatility:.4f}")
                return None
            
            # Volatility breakout strategy
            if conditions['price_above_upper']:
                # Price broke above upper Bollinger Band - potential upward momentum
                confidence = min(0.9, volatility * 10)  # Scale confidence with volatility
                return TradingSignal(
                    action='buy',
                    confidence=confidence,
                    reason=f"Price broke above upper BB (${current_price:,.2f}), volatility: {volatility:.4f}",
                    price=current_price
                )
            
            elif conditions['price_below_lower']:
                # Price broke below lower Bollinger Band - potential downward momentum
                confidence = min(0.9, volatility * 10)
                return TradingSignal(
                    action='sell',
                    confidence=confidence,
                    reason=f"Price broke below lower BB (${current_price:,.2f}), volatility: {volatility:.4f}",
                    price=current_price
                )
            
            # Mean reversion strategy (when price is near middle band)
            elif abs(current_price - conditions['bb_middle']) < (conditions['bb_upper'] - conditions['bb_middle']) * 0.1:
                # Check if we're coming from above or below
                prev_price = self.data_feed.get_historical_data('2d')['price'].iloc[-2]
                
                if prev_price > conditions['bb_middle']:
                    # Price was above middle band, now near middle - potential sell
                    return TradingSignal(
                        action='sell',
                        confidence=0.6,
                        reason=f"Mean reversion from above (${current_price:,.2f})",
                        price=current_price
                    )
                else:
                    # Price was below middle band, now near middle - potential buy
                    return TradingSignal(
                        action='buy',
                        confidence=0.6,
                        reason=f"Mean reversion from below (${current_price:,.2f})",
                        price=current_price
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating signal: {e}")
            return None
    
    def optimize_parameters(self, historical_data: pd.DataFrame) -> Dict[str, float]:
        """Optimize strategy parameters using historical data"""
        # This would be implemented with a proper optimization algorithm
        # For now, return current parameters
        logger.info("Parameter optimization not yet implemented")
        return self.parameters.copy()