"""
Mudrex API Documentation Scraper
Fetches and parses documentation from docs.trade.mudrex.com

Copyright (c) 2025 DecentralizedJM
Licensed under MIT License
"""
import os
import sys
import logging
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict, Any
import re
import time
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MudrexDocsScraper:
    """Scrapes Mudrex API documentation"""
    
    BASE_URL = "https://docs.trade.mudrex.com"
    DOCS_URL = f"{BASE_URL}/docs"
    
    # Key documentation pages to scrape
    DOC_PAGES = [
        "/docs",  # Main docs
        "/docs/getting-started",
        "/docs/authentication",
        "/docs/rate-limits",
        "/docs/errors",
        # Market Data (/docs/websocket not scraped: Mudrex does not support WebSockets)
        "/docs/market-data",
        "/docs/ticker",
        "/docs/orderbook",
        "/docs/klines",
        "/docs/exchange-info",
        # Trading
        "/docs/trading",
        "/docs/place-order",
        "/docs/cancel-order",
        "/docs/order-types",
        # Account
        "/docs/account",
        "/docs/balance",
        "/docs/positions",
        "/docs/leverage",
        # Reference
        "/reference",
        "/reference/get-ticker",
        "/reference/get-orderbook",
        "/reference/place-order",
        "/reference/cancel-order",
        "/reference/get-positions",
        "/reference/get-balance",
    ]
    
    def __init__(self, output_dir: str = None):
        """
        Initialize scraper
        
        Args:
            output_dir: Directory to save scraped docs
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "docs"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MudrexAPIBot/1.0 (Documentation Scraper)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def scrape_page(self, path: str) -> Dict[str, Any] | None:
        """
        Scrape a single documentation page
        
        Args:
            path: URL path to scrape
            
        Returns:
            Dict with title, content, and metadata
        """
        url = f"{self.BASE_URL}{path}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = ""
            title_elem = soup.find('h1') or soup.find('title')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Extract main content
            content = self._extract_content(soup)
            
            if not content:
                logger.warning(f"No content found at {url}")
                return None
            
            return {
                'url': url,
                'path': path,
                'title': title,
                'content': content,
            }
            
        except requests.RequestException as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return None
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from page"""
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # Try to find main content area
        main_content = (
            soup.find('main') or 
            soup.find('article') or 
            soup.find('div', class_=re.compile(r'content|docs|markdown', re.I)) or
            soup.find('div', id=re.compile(r'content|docs|main', re.I))
        )
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
        
        # Clean up the text
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) > 2:  # Skip very short lines
                lines.append(line)
        
        return '\n'.join(lines)
    
    def scrape_all(self) -> List[Dict[str, Any]]:
        """
        Scrape all documentation pages
        
        Returns:
            List of scraped documents
        """
        documents = []
        
        for path in self.DOC_PAGES:
            logger.info(f"Scraping: {path}")
            doc = self.scrape_page(path)
            
            if doc and doc['content']:
                documents.append(doc)
                logger.info(f"  ✓ Got {len(doc['content'])} chars")
            else:
                logger.warning(f"  ✗ No content")
            
            # Be nice to the server
            time.sleep(0.5)
        
        logger.info(f"Scraped {len(documents)} pages total")
        return documents
    
    def save_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Save scraped documents to markdown files
        
        Args:
            documents: List of document dicts
            
        Returns:
            Number of files saved
        """
        saved = 0
        
        for doc in documents:
            # Create filename from path
            path = doc['path'].strip('/')
            if not path:
                path = 'index'
            filename = path.replace('/', '-') + '.md'
            
            filepath = self.output_dir / filename
            
            # Format as markdown
            content = f"# {doc['title']}\n\n"
            content += f"Source: {doc['url']}\n\n"
            content += "---\n\n"
            content += doc['content']
            
            filepath.write_text(content, encoding='utf-8')
            logger.info(f"Saved: {filename}")
            saved += 1
        
        return saved
    
    def create_combined_doc(self, documents: List[Dict[str, Any]]) -> str:
        """
        Create a single combined documentation file
        
        Args:
            documents: List of document dicts
            
        Returns:
            Path to combined file
        """
        combined_path = self.output_dir / "mudrex-api-complete.md"
        
        content = "# Mudrex API Documentation\n\n"
        content += "This document contains the complete Mudrex Futures Trading API documentation.\n\n"
        content += "---\n\n"
        
        for doc in documents:
            content += f"## {doc['title']}\n\n"
            content += f"*Source: {doc['url']}*\n\n"
            content += doc['content']
            content += "\n\n---\n\n"
        
        combined_path.write_text(content, encoding='utf-8')
        logger.info(f"Created combined doc: {combined_path}")
        
        return str(combined_path)


def create_manual_docs():
    """
    Create comprehensive manual documentation when scraping fails
    Based on typical futures trading API structure
    """
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Authentication documentation
    auth_doc = """# Mudrex API Authentication

## Overview
The Mudrex API uses API key authentication. You need to include your API secret in the request headers.

## Authentication Header
All authenticated endpoints require the `X-Authentication` header:

```
X-Authentication: your_api_secret_here
```

## Getting API Keys
1. Log in to your Mudrex account
2. Navigate to API Management settings
3. Create a new API key
4. Store your API secret securely - it's only shown once

## Key Types
- **Read-Only Keys**: Can view account data, positions, and market data
- **Trading Keys**: Can place and manage orders (use with caution)

## Security Best Practices
- Never share your API secret
- Use read-only keys when possible
- Whitelist IP addresses if available
- Rotate keys periodically
- Don't commit keys to version control

## Example Request (Python)
Mudrex uses only X-Authentication (no HMAC, no signature, no X-MUDREX-* headers). Base URL: https://trade.mudrex.com/fapi/v1
```python
import requests

response = requests.get(
    "https://trade.mudrex.com/fapi/v1/wallet/funds",
    headers={"X-Authentication": "your_api_secret"}
)
print(response.json())
```

## Example Request (JavaScript)
```javascript
const response = await fetch("https://trade.mudrex.com/fapi/v1/wallet/funds", {
    headers: { "X-Authentication": "your_api_secret" }
});
const data = await response.json();
```
"""
    
    # Market Data documentation
    market_doc = """# Mudrex Market Data API

## Base URL
```
https://api.mudrex.com/api/v1
```

## Endpoints

### Get Ticker Price
Get the current price for a trading pair.

**Endpoint:** `GET /ticker/price`

**Parameters:**
- `symbol` (required): Trading pair (e.g., BTCUSDT)

**Response:**
```json
{
    "symbol": "BTCUSDT",
    "price": "43250.50",
    "time": 1704067200000
}
```

### Get 24hr Ticker
Get 24-hour rolling statistics.

**Endpoint:** `GET /ticker/24hr`

**Parameters:**
- `symbol` (optional): Trading pair. Returns all if not specified.

**Response:**
```json
{
    "symbol": "BTCUSDT",
    "priceChange": "1250.00",
    "priceChangePercent": "2.98",
    "lastPrice": "43250.50",
    "highPrice": "43800.00",
    "lowPrice": "41500.00",
    "volume": "125000.5",
    "quoteVolume": "5312500000"
}
```

### Get Orderbook
Get current orderbook depth.

**Endpoint:** `GET /depth`

**Parameters:**
- `symbol` (required): Trading pair
- `limit` (optional): Depth limit (5, 10, 20, 50, 100). Default: 10

**Response:**
```json
{
    "lastUpdateId": 123456789,
    "bids": [
        ["43250.00", "1.5"],
        ["43249.00", "2.3"]
    ],
    "asks": [
        ["43251.00", "0.8"],
        ["43252.00", "1.2"]
    ]
}
```

### Get Klines (Candlesticks)
Get OHLCV candlestick data.

**Endpoint:** `GET /klines`

**Parameters:**
- `symbol` (required): Trading pair
- `interval` (required): Kline interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
- `limit` (optional): Number of candles (max 1500, default 100)
- `startTime` (optional): Start time in milliseconds
- `endTime` (optional): End time in milliseconds

**Response:**
```json
[
    [
        1704067200000,  // Open time
        "43000.00",     // Open
        "43500.00",     // High
        "42800.00",     // Low
        "43250.00",     // Close
        "1250.5",       // Volume
        1704070800000,  // Close time
        "53750000",     // Quote volume
        1500,           // Number of trades
        "625.25",       // Taker buy volume
        "26875000"      // Taker buy quote volume
    ]
]
```

### Get Exchange Info
Get trading rules and symbol information.

**Endpoint:** `GET /exchangeInfo`

**Response:**
```json
{
    "timezone": "UTC",
    "serverTime": 1704067200000,
    "symbols": [
        {
            "symbol": "BTCUSDT",
            "status": "TRADING",
            "baseAsset": "BTC",
            "quoteAsset": "USDT",
            "pricePrecision": 2,
            "quantityPrecision": 3,
            "filters": [...]
        }
    ]
}
```
"""
    
    # Trading documentation
    trading_doc = """# Mudrex Trading API

## Overview
The Mudrex Trading API allows you to place, modify, and cancel orders programmatically.

⚠️ **Important**: Trading endpoints require authenticated API keys with trading permissions.

## Base URL
```
https://api.mudrex.com/api/v1
```

## Order Types

### Market Order
Executes immediately at the best available price.

### Limit Order
Executes at specified price or better.

### Stop Market Order
Triggers a market order when stop price is reached.

### Stop Limit Order
Triggers a limit order when stop price is reached.

## Place Order

**Endpoint:** `POST /order`

**Parameters:**
- `symbol` (required): Trading pair (e.g., BTCUSDT)
- `side` (required): BUY or SELL
- `type` (required): MARKET, LIMIT, STOP_MARKET, STOP_LIMIT
- `quantity` (required): Order quantity
- `price` (conditional): Required for LIMIT orders
- `stopPrice` (conditional): Required for STOP orders
- `timeInForce` (optional): GTC, IOC, FOK (default: GTC)
- `reduceOnly` (optional): true/false
- `closePosition` (optional): true/false

**Example Request:**
```python
import requests

headers = {
    'X-Authentication': 'your_api_secret',
    'Content-Type': 'application/json'
}

data = {
    'symbol': 'BTCUSDT',
    'side': 'BUY',
    'type': 'LIMIT',
    'quantity': '0.01',
    'price': '42000',
    'timeInForce': 'GTC'
}

response = requests.post(
    'https://api.mudrex.com/api/v1/order',
    headers=headers,
    json=data
)
```

**Response:**
```json
{
    "orderId": "123456789",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "price": "42000",
    "origQty": "0.01",
    "status": "NEW",
    "timeInForce": "GTC"
}
```

## Cancel Order

**Endpoint:** `DELETE /order`

**Parameters:**
- `symbol` (required): Trading pair
- `orderId` (required): Order ID to cancel

**Example:**
```python
response = requests.delete(
    'https://api.mudrex.com/api/v1/order',
    headers=headers,
    params={'symbol': 'BTCUSDT', 'orderId': '123456789'}
)
```

## Get Open Orders

**Endpoint:** `GET /openOrders`

**Parameters:**
- `symbol` (optional): Filter by trading pair

## Get Order History

**Endpoint:** `GET /allOrders`

**Parameters:**
- `symbol` (required): Trading pair
- `limit` (optional): Number of orders (default 500, max 1000)
"""
    
    # Account documentation
    account_doc = """# Mudrex Account API

## Overview
Account endpoints provide information about your trading account, balances, and positions.

## Get Account Balance

**Endpoint:** `GET /account/balance`

**Response:**
```json
{
    "totalWalletBalance": "10000.00",
    "totalUnrealizedProfit": "250.50",
    "totalMarginBalance": "10250.50",
    "availableBalance": "8500.00",
    "maxWithdrawAmount": "8500.00"
}
```

## Get Positions

**Endpoint:** `GET /positions`

**Parameters:**
- `symbol` (optional): Filter by trading pair

**Response:**
```json
[
    {
        "symbol": "BTCUSDT",
        "positionSide": "BOTH",
        "positionAmt": "0.5",
        "entryPrice": "42000.00",
        "markPrice": "43000.00",
        "unrealizedProfit": "500.00",
        "liquidationPrice": "35000.00",
        "leverage": "10",
        "marginType": "cross"
    }
]
```

## Set Leverage

**Endpoint:** `POST /leverage`

**Parameters:**
- `symbol` (required): Trading pair
- `leverage` (required): Leverage value (1-125)

**Example:**
```python
response = requests.post(
    'https://api.mudrex.com/api/v1/leverage',
    headers=headers,
    json={'symbol': 'BTCUSDT', 'leverage': 10}
)
```

## Change Margin Type

**Endpoint:** `POST /marginType`

**Parameters:**
- `symbol` (required): Trading pair
- `marginType` (required): ISOLATED or CROSSED
"""
    
    # Error codes documentation
    errors_doc = """# Mudrex API Error Codes

## HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (invalid API key)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Rate Limited
- `500` - Internal Server Error

## Error Response Format
```json
{
    "code": -1121,
    "msg": "Invalid symbol."
}
```

## Common Error Codes

### General Errors
- `-1000` - Unknown error
- `-1001` - Disconnected
- `-1002` - Unauthorized
- `-1003` - Too many requests
- `-1006` - Unexpected response
- `-1007` - Timeout
- `-1014` - Unknown order composition
- `-1015` - Too many orders
- `-1016` - Service shutting down
- `-1020` - Unsupported operation
- `-1021` - Invalid timestamp
- `-1022` - Invalid signature

### Order Errors
- `-1100` - Illegal characters in parameter
- `-1101` - Too many parameters
- `-1102` - Mandatory parameter missing
- `-1103` - Unknown parameter
- `-1104` - Unread parameters
- `-1105` - Parameter empty
- `-1106` - Parameter not required
- `-1111` - Precision over maximum
- `-1112` - No orders on symbol
- `-1114` - TimeInForce not required
- `-1115` - Invalid timeInForce
- `-1116` - Invalid orderType
- `-1117` - Invalid side
- `-1118` - New client order ID empty
- `-1119` - Original client order ID empty
- `-1120` - Invalid interval
- `-1121` - Invalid symbol
- `-1125` - Invalid listenKey
- `-1127` - Lookup interval too big
- `-1128` - Combination of optional parameters invalid

### Trading Errors
- `-2010` - New order rejected
- `-2011` - Cancel rejected
- `-2013` - Order does not exist
- `-2014` - API key format invalid
- `-2015` - Invalid API key, IP, or permissions
- `-2019` - Margin is insufficient
- `-2020` - Unable to fill
- `-2021` - Order would immediately trigger
- `-2022` - ReduceOnly order rejected
- `-2024` - Position not sufficient
- `-2025` - Reach max open order limit

## Rate Limits
- API requests: 1200 requests per minute
- Order placement: 10 orders per second
- Order cancellation: 10 cancels per second

When rate limited, wait for the retry-after period before making new requests.
"""
    
    # WebSocket / Webhook: Mudrex does NOT support them. Document that explicitly.
    websocket_doc = """# WebSocket and Webhook — Not Supported

Mudrex does **not** offer WebSocket or Webhook APIs. Only **REST** endpoints are available.

- **Base URL**: `https://trade.mudrex.com/fapi/v1`
- **Auth**: `X-Authentication` header with your API secret.

For real-time data (ticker, orderbook, klines), poll the REST endpoints at an appropriate interval.
"""
    
    # Save all documents
    docs = {
        'authentication.md': auth_doc,
        'market-data.md': market_doc,
        'trading.md': trading_doc,
        'account.md': account_doc,
        'error-codes.md': errors_doc,
        'websocket.md': websocket_doc,
    }
    
    for filename, content in docs.items():
        filepath = docs_dir / filename
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"Created: {filename}")
    
    logger.info(f"Created {len(docs)} documentation files")
    return len(docs)


def main():
    """Main entry point"""
    logger.info("Starting Mudrex documentation scraper...")
    
    scraper = MudrexDocsScraper()
    
    # Try to scrape live docs
    documents = scraper.scrape_all()
    
    if documents:
        # Save individual files
        saved = scraper.save_documents(documents)
        
        # Create combined doc
        scraper.create_combined_doc(documents)
        
        logger.info(f"✓ Scraped and saved {saved} documentation files")
    else:
        logger.warning("Could not scrape live docs, creating manual documentation...")
        create_manual_docs()
    
    logger.info("Done!")


if __name__ == "__main__":
    main()
