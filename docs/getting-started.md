# Mudrex API - Getting Started

## Overview

The Mudrex API allows you to programmatically interact with your Mudrex account to create and manage trading strategies, orders, and positions.

## Base URL

```
https://api.mudrex.com
```

## Authentication

All API requests require authentication using API keys.

### Getting API Keys

1. Log in to your Mudrex account
2. Navigate to Settings → API Keys
3. Click "Create New API Key"
4. Save your API Key and API Secret securely

### Authentication Headers

Include these headers in every request:

```
X-API-Key: your_api_key
X-API-Secret: your_api_secret
```

### Example Request

```bash
curl -X GET https://api.mudrex.com/v1/account \
  -H "X-API-Key: abc123..." \
  -H "X-API-Secret: xyz789..."
```

## Rate Limits

- **Public endpoints**: 100 requests per minute
- **Private endpoints**: 60 requests per minute

If you exceed the rate limit, you'll receive a `429 Too Many Requests` response.

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or missing API keys |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Endpoint doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

## Quick Start Example

```python
import requests

API_KEY = "your_api_key"
API_SECRET = "your_api_secret"
BASE_URL = "https://api.mudrex.com"

headers = {
    "X-API-Key": API_KEY,
    "X-API-Secret": API_SECRET
}

# Get account information
response = requests.get(f"{BASE_URL}/v1/account", headers=headers)
print(response.json())
```

## Next Steps

- Check out the [Endpoints](endpoints.md) documentation
- Learn about [Order Management](orders.md)
- Explore [Position Tracking](positions.md)
