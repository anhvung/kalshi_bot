import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class TradeResult:
    """Data class for trade execution results"""
    success: bool
    order_id: Optional[str] = None
    market_id: Optional[str] = None
    action: Optional[str] = None  # 'buy' or 'sell'
    quantity: int = 0
    price: float = 0.0
    timestamp: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'order_id': self.order_id,
            'market_id': self.market_id,
            'action': self.action,
            'quantity': self.quantity,
            'price': self.price,
            'timestamp': self.timestamp,
            'error': self.error
        }

class TradeExecutor:
    """Handles trade execution with Kalshi API"""
    
    def __init__(self, api: Any, risk_manager: Any):
        self.api = api
        self.risk_manager = risk_manager
        self.active_orders = {}
        
    def execute_trade(self, signal: Any) -> TradeResult:
        """Execute a trade based on trading signal"""
        if not signal or not signal.action:
            logger.warning("No valid signal provided")
            return TradeResult(success=False, error="No valid signal")
        
        try:
            # Get current market data
            markets = self.api.get_markets('crypto')
            if not markets:
                return TradeResult(success=False, error="No markets available")
            
            # For simplicity, use first crypto market (in production, you'd filter)
            market = markets[0]
            market_id = market['id']
            
            # Get orderbook to determine current price
            orderbook = self.api.get_orderbook(market_id)
            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                return TradeResult(success=False, error="Invalid orderbook")
            
            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                signal.confidence, 
                signal.price or orderbook['asks'][0]['price']
            )
            
            if position_size <= 0:
                logger.info("Position size calculated as 0, not executing trade")
                return TradeResult(success=False, error="Position size too small")
            
            # Determine price based on order type
            if signal.action == 'buy':
                price = orderbook['asks'][0]['price']  # Buy at best ask
            else:  # sell
                price = orderbook['bids'][0]['price']  # Sell at best bid
            
            # Place order
            order_result = self.api.place_order(
                market_id=market_id,
                side=signal.action,
                quantity=position_size,
                order_type='limit',
                price=price
            )
            
            if order_result and 'id' in order_result:
                trade_result = TradeResult(
                    success=True,
                    order_id=order_result['id'],
                    market_id=market_id,
                    action=signal.action,
                    quantity=position_size,
                    price=price,
                    timestamp=time.time()
                )
                
                self.active_orders[order_result['id']] = trade_result
                logger.info(f"Successfully placed {signal.action} order: {position_size} contracts at ${price:.2f}")
                return trade_result
            else:
                error_msg = order_result.get('error', 'Unknown order placement error')
                logger.error(f"Failed to place order: {error_msg}")
                return TradeResult(success=False, error=error_msg)
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return TradeResult(success=False, error=str(e))
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order"""
        try:
            result = self.api.cancel_order(order_id)
            if result and result.get('success', False):
                if order_id in self.active_orders:
                    del self.active_orders[order_id]
                logger.info(f"Successfully canceled order {order_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {e}")
            return False
    
    def check_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Check status of an order"""
        try:
            # Kalshi API doesn't have a direct order status endpoint in v1
            # This would need to be implemented based on their actual API
            logger.warning("Order status check not implemented in Kalshi v1 API")
            return None
        except Exception as e:
            logger.error(f"Error checking order status: {e}")
            return None
    
    def get_active_orders(self) -> Dict[str, TradeResult]:
        """Get all active orders"""
        return self.active_orders.copy()
    
    def close_all_positions(self) -> bool:
        """Close all open positions"""
        try:
            positions = self.api.get_positions()
            if not positions:
                logger.info("No positions to close")
                return True
            
            success = True
            for position in positions:
                market_id = position['market_id']
                quantity = position['quantity']
                
                # Determine opposite side
                side = 'sell' if quantity > 0 else 'buy'
                abs_quantity = abs(quantity)
                
                # Get current price
                orderbook = self.api.get_orderbook(market_id)
                if not orderbook:
                    success = False
                    continue
                
                price = orderbook['bids'][0]['price'] if side == 'sell' else orderbook['asks'][0]['price']
                
                # Place closing order
                order_result = self.api.place_order(
                    market_id=market_id,
                    side=side,
                    quantity=abs_quantity,
                    order_type='market'
                )
                
                if not order_result or 'id' not in order_result:
                    success = False
                    logger.error(f"Failed to close position for {market_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            return False