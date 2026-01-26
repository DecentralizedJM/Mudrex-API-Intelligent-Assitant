# Mudrex URLs and Access

## Important URL Distinction

Mudrex has two different URLs for different purposes:

### Web Dashboard URL (Browser Access)
**URL**: `www.mudrex.com/pro-trading`

This is the web interface where users can:
- Access API trading features in their browser
- Generate API keys
- View API dashboard
- Manage API settings

**When to use**: When users ask for:
- "web URL"
- "dashboard URL"
- "API trading URL"
- "where to access API trading"
- "browser URL"

### REST API Base URL (API Endpoints)
**URL**: `https://trade.mudrex.com/fapi/v1`

This is the base URL for making REST API calls programmatically.

**Authentication**:
- Header: `X-Authentication: <your_api_secret>`
- Content-Type: `application/json` (for POST/PATCH/DELETE)
- No HMAC, no signatures, no timestamps

**When to use**: When users ask for:
- "API endpoint"
- "base URL"
- "REST API URL"
- "API base URL"
- "where to make API calls"

## Summary

- **Web Dashboard**: `www.mudrex.com/pro-trading` (for browser access)
- **API Base URL**: `https://trade.mudrex.com/fapi/v1` (for API calls)
