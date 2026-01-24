# WebSocket and Webhook — Not Supported

**Mudrex does not offer WebSocket or Webhook APIs.**

Only **REST** endpoints are available. Use `https://trade.mudrex.com/fapi/v1` with the `X-Authentication` header for all API access.

For real-time data, poll the REST endpoints (e.g. ticker, orderbook, klines) at an appropriate interval.
