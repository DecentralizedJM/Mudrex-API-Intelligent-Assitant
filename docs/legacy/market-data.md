# ⚠️ LEGACY DOCUMENTATION - DO NOT USE ⚠️

**THIS DOCUMENTATION IS FOR THE OLD MUDREX API AND IS NO LONGER VALID.**

**Current Mudrex Futures API Base URL:** `https://trade.mudrex.com/fapi/v1`

**This file documents the OLD API at:** `https://api.mudrex.com/api/v1` which is **NOT the current Futures API**.

**The endpoints in this file (including /klines) do NOT exist in the current Mudrex Futures API.**

Do NOT use this documentation for the current API. Refer to the official docs at https://docs.trade.mudrex.com

---

# Mudrex Market Data API (LEGACY - DEPRECATED)

## Base URL (OLD - DO NOT USE)
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
