# Fixing API Key Issues on Railway

## Problem
After updating `GEMINI_API_KEY` in Railway environment variables, the bot still shows "API key expired" errors.

## Solution

### 1. Restart the Railway Deployment

**The bot loads environment variables only at startup.** After changing environment variables in Railway, you MUST restart the deployment:

1. Go to your Railway project dashboard
2. Click on your service/deployment
3. Click the **"Deployments"** tab
4. Find the latest deployment
5. Click the **three dots (⋯)** menu
6. Select **"Redeploy"** or **"Restart"**

Alternatively:
- Go to **Settings** → **Deploy** → Click **"Redeploy"**
- Or trigger a new deployment by pushing a commit (even a small change)

### 2. Verify Environment Variable

1. In Railway dashboard, go to your service
2. Click **"Variables"** tab
3. Verify:
   - Variable name is exactly: `GEMINI_API_KEY` (case-sensitive)
   - Value is set (not empty)
   - No extra spaces or quotes around the value
   - The key is valid and not expired

### 3. Check Logs After Restart

After restarting, check the logs to see if the new key is being used:

```bash
# In Railway dashboard, go to "Deployments" → Click on latest deployment → "Logs"
# Look for:
# - "Initialized Gemini client (new SDK): gemini-3-flash-preview"
# - No "API key expired" errors
```

### 4. Test the New Key

You can test if your new API key is valid:

```bash
# In Railway shell or locally
python3 -c "
import os
from google import genai
os.environ['GEMINI_API_KEY'] = 'YOUR_NEW_KEY_HERE'
client = genai.Client()
try:
    result = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents='Hello'
    )
    print('✅ API key is valid!')
except Exception as e:
    print(f'❌ API key error: {e}')
"
```

### 5. Common Issues

**Issue**: "API key expired" even after restart
- **Solution**: The new key might also be expired. Generate a fresh key from [Google AI Studio](https://makersuite.google.com/app/apikey)

**Issue**: Variable not found
- **Solution**: Check variable name spelling: `GEMINI_API_KEY` (exact case)

**Issue**: Bot still using old key
- **Solution**: Make sure you restarted the deployment, not just saved the variable

**Issue**: Multiple services/environments
- **Solution**: Make sure you updated the variable in the correct service/environment

## Quick Checklist

- [ ] Updated `GEMINI_API_KEY` in Railway Variables
- [ ] Verified variable name is exactly `GEMINI_API_KEY`
- [ ] Verified value is set (not empty)
- [ ] Restarted/Redeployed the Railway service
- [ ] Checked logs after restart
- [ ] Verified new API key is valid (not expired)

## How the Bot Loads the Key

The bot loads the API key in this order:

1. **At startup**: `Config.from_env()` reads `GEMINI_API_KEY` from environment
2. **When initializing**: `GeminiClient.__init__()` sets `os.environ['GEMINI_API_KEY']` from config
3. **When using**: `genai.Client()` reads from `os.environ['GEMINI_API_KEY']`

**Important**: This happens only once at startup. Railway environment variables are injected when the container starts, so you must restart to pick up changes.
