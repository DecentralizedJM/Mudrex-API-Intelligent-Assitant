# Mudrex API - Custom FAQ
Source: User Chat Load
Date: 2026-01-24

## General
**Q: What is an API key?**
A: An API key connects your Mudrex account to your trading bot or system. It allows your bot to securely read data and place orders using the Mudrex Futures API.

**Q: Why am I not able to see the API dashboard on mobile?**
A: API trading is currently available only on desktop. Log in to Mudrex on a desktop browser and navigate to the API tab from the main navigation bar to access your API dashboard.

## API Key Management
**Q: How do I create an API key?**
A: Go to API Dashboard → Generate API Key. Name your key, confirm KYC + 2FA, and copy your secret immediately—it is shown only once.

**Q: Why can’t I see my API secret again?**
A: For security reasons, the secret is shown only once during creation. If you lose it, you must rotate the key to generate a new secret.

**Q: How many API keys can I create?**
A: Currently, you can create one API key per user.

**Q: How do I rotate my API key?**
A: Click Rotate on your key card. This invalidates your current secret and generates a new one. Update your bot configuration with the new secret.

**Q: How do I revoke my API key?**
A: Click Revoke and confirm. Once revoked, the key is permanently disabled and cannot be recovered.

**Q: Why can’t I create a key without KYC or 2FA?**
A: API access requires completed KYC and enabled 2FA for compliance and account security.

**Q: How do I enable 2FA?**
A: Enable it via the Mudrex mobile app: Account → Security → Two-Factor Authentication.

**Q: What happens if I revoke or rotate my key while bots are running?**
A: Your bot will lose access immediately. You must update it with the new key/secret to restore access.

**Q: Is my API key shared across Spot and Futures?**
A: No. The API key currently supports Futures trading only.

**Q: Is there any expiry for my API Key?**
A: Yes. For security reasons, your API key is valid for 90 days and will expire after that period. You’ll need to generate or rotate your key to continue using API trading.

**Q: My key stopped working suddenly. Why?**
A: It may have been revoked/rotated or expired due to inactivity. Rotate or generate a new key if needed.

**Q: I dismissed the secret modal without copying it. What now?**
A: You must rotate the key. The secret cannot be recovered.

**Q: Can I use my key on multiple systems?**
A: Yes. You can use the same API key across multiple systems, but rate limits are applied per API key. This means requests from all systems using that key count toward the same limit. Store your key securely and avoid sharing it publicly.

## Technical Details
**Q: Where do I find API documentation?**
A: Documentation is available at Overview and includes endpoints for Wallet, Leverage, Orders, Positions, and error handling.

**Q: I got “Too many requests. Try again in X seconds.”**
A: You hit the rate limit: 2 requests/second per API key. Wait briefly and retry.

**Q: My request failed with “position not in sync with exchange.”**
A: Your local state differs from the exchange. Fetch the latest position/order data and retry.

**Q: Do you support WebSockets?**
A: No. Mudrex supports only REST. There are no WebSocket or Webhook APIs. Use REST polling for market data.

**Q: What headers are required for authentication?**
A: Only `X-Authentication` with your API secret. Mudrex does not use HMAC, SHA256, signature, X-MUDREX-API-KEY, X-MUDREX-SIGNATURE, X-MUDREX-TIMESTAMP, or X-Time. For POST/PATCH/DELETE add `Content-Type: application/json`.

**Q: Are numeric values integers or strings?**
A: All numeric values are returned as strings to preserve precision (for example, "0.001").

**Q: Where can I get developer support?**
A: Feel free to reach out to our developer support team at api@mudrex.com. You can also join the Mudrex Developers Channel on Telegram for updates, discussions, and community support.
