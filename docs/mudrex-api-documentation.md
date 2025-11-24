# Mudrex API Documentation

**Source:** https://docs.trade.mudrex.com  
**Fetched:** 2025-11-25 02:57:41

---

Overview
Mudrex Futures API — Overview
Mudrex Futures API gives programmatic control over your Mudrex trading account. You can transfer funds between your spot and futures wallets, list tradeable instruments, set leverage/margin type for each asset, place and manage orders, track open positions, and retrieve fee histories.
All endpoints are versioned under
https://trade.mudrex.com/fapi/v1
. Requests require an X-Authentication header carrying your API secret and a millisecond timestamp in X-Time. Responses use JSON; numeric values are strings to preserve precision.
Base URL
Host:
https://trade.mudrex.com
Base path:
/fapi/v1
Example:
https://trade.mudrex.com/fapi/v1/<resource>
Requirements
Auth header:
send
X-Authentication: <token>
with every request.
Rate limit:
1 request/second per API key.
Timestamps:
milliseconds since Unix epoch.
Decimals:
send as
strings
(e.g.,
"0.001"
,
"107526"
).
Endpoint Groups
Group
Purpose
Wallet
Fetch spot wallet balances; move funds between spot and futures.
Futures
Fetch futures wallet balance and available transfer amount.
Assets
List all futures instruments with sorting/pagination; retrieve full metadata for a specific asset.
Leverage
Get or set leverage and margin type (isolated) for a specific asset.
Orders
Create new orders (market or limit), list open orders, fetch order history, retrieve single orders, cancel/amend orders.
Positions
View open positions, set/edit stop‑loss and take‑profit, reverse or partially close positions, fetch position history.
Fees
Retrieve your trading fee history.
Use the Quickstart to follow a complete trading workflow.
Updated
about 1 month ago
