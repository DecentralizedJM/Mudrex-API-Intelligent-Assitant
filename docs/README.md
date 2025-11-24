# Mudrex API Documentation

This directory should contain your Mudrex API documentation files.

## Supported Formats

- Markdown (`.md`)
- Plain text (`.txt`)
- reStructuredText (`.rst`)

## Organization

You can organize files in subdirectories. Examples:

```
docs/
├── getting-started.md
├── authentication.md
├── endpoints/
│   ├── orders.md
│   ├── positions.md
│   └── account.md
├── errors.md
└── examples.md
```

## Adding Documentation

1. Place your documentation files in this directory
2. Run the ingestion script: `python scripts/ingest_docs.py`
3. The bot will index all documents automatically

## Tips

- Use clear headings and structure
- Include code examples
- Document all endpoints, parameters, and responses
- Add common error codes and solutions
- Update regularly as API changes

## Sample Documentation

Create a file like `authentication.md`:

```markdown
# Authentication

## Overview
All Mudrex API requests require authentication using API keys.

## Getting API Keys
1. Log in to your Mudrex account
2. Navigate to Settings > API
3. Generate new API key pair

## Making Authenticated Requests

Include headers:
- `X-API-Key`: Your API key
- `X-API-Secret`: Your API secret

Example:
\`\`\`bash
curl -X GET https://api.mudrex.com/v1/account \
  -H "X-API-Key: your_key" \
  -H "X-API-Secret: your_secret"
\`\`\`
```

After adding documentation, run: `python scripts/ingest_docs.py`
