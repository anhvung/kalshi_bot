import requests
import time
import hashlib
import hmac
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class KalshiAPI:
    """Wrapper for Kalshi API"""
    
    def __init__(self, config: dict):
        self.base_url = config['base_url']
        self.api_key = config['api_key']
        self.api_secret = config['api_secret']
        self.timeout = config.get('timeout', 30)
        self.rate_limit = config.get('rate_limit', 10)
        self.last_request_time = 0
        
        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < 1.0 / self.rate_limit:
            time.sleep(1.0 / self.rate_limit - elapsed)
        self.last_request_time = time.time()
    
    def _sign_request(self, method: str, path: str, body: str = '') -> str:
        """Generate HMAC signature for request"""
        timestamp = str(int(time.time() * 1000))
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{self.api_key}:{timestamp}:{signature}"
    
    def _request(self, method: str, endpoint: str, params: Optional[dict] = None, 
                data: Optional[dict] = None) -> Dict[str, Any]:
        """Make authenticated API request"""
        self._enforce_rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        body = json.dumps(data) if data else ''
        
        # Sign the request
        auth_header = self._sign_request(method.upper(), endpoint, body)
        self.session.headers['Authorization'] = auth_header
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=body,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def get_markets(self, market_type: str = 'crypto') -> List[Dict[str, Any]]:
        """Get available markets"""
        endpoint = '/markets'
        params = {'market_type': market_type}
        return self._request('GET', endpoint, params=params)
    
    def get_market_details(self, market_id: str) -> Dict[str, Any]:
        """Get details for specific market"""
        endpoint = f'/markets/{market_id}'
        return self._request('GET', endpoint)
    
    def get_orderbook(self, market_id: str) -> Dict[str, Any]:
        """Get orderbook for a market"""
        endpoint = f'/markets/{market_id}/orderbook'
        return self._request('GET', endpoint)
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        endpoint = '/positions'
        return self._request('GET', endpoint)
    
    def place_order(self, market_id: str, side: str, quantity: int, 
                   order_type: str = 'limit', price: Optional[float] = None) -> Dict[str, Any]:
        """Place an order"""
        endpoint = '/orders'
        data = {
            'market_id': market_id,
            'side': side,
            'quantity': quantity,
            'type': order_type
        }
        
        if order_type == 'limit' and price:
            data['price'] = price
            
        return self._request('POST', endpoint, data=data)
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        endpoint = f'/orders/{order_id}'
        return self._request('DELETE', endpoint)
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        endpoint = '/account/balance'
        return self._request('GET', endpoint)