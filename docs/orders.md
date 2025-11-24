# Mudrex API - Order Management

## Create Order

Create a new trading order.

### Endpoint

```
POST /v1/orders
```

### Request Body

```json
{
  "symbol": "BTC/USDT",
  "side": "buy",
  "type": "limit",
  "quantity": 0.001,
  "price": 45000
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| symbol | string | Yes | Trading pair (e.g., BTC/USDT) |
| side | string | Yes | Order side: `buy` or `sell` |
| type | string | Yes | Order type: `market` or `limit` |
| quantity | number | Yes | Order quantity |
| price | number | No | Price (required for limit orders) |

### Response

```json
{
  "orderId": "12345",
  "status": "open",
  "symbol": "BTC/USDT",
  "side": "buy",
  "type": "limit",
  "quantity": 0.001,
  "price": 45000,
  "filled": 0,
  "createdAt": "2024-01-15T10:30:00Z"
}
```

## Get Order Status

Retrieve the status of a specific order.

### Endpoint

```
GET /v1/orders/{orderId}
```

### Response

```json
{
  "orderId": "12345",
  "status": "filled",
  "filled": 0.001,
  "remaining": 0
}
```

## Cancel Order

Cancel an open order.

### Endpoint

```
DELETE /v1/orders/{orderId}
```

### Response

```json
{
  "success": true,
  "orderId": "12345",
  "status": "cancelled"
}
```

## Common Errors

### 400 Bad Request

```json
{
  "error": "Invalid quantity",
  "message": "Quantity must be greater than minimum trade amount"
}
```

**Solution**: Check minimum trade amounts for your trading pair.

### 401 Unauthorized

```json
{
  "error": "Unauthorized",
  "message": "Invalid API credentials"
}
```

**Solution**: Verify your API key and secret are correct.
