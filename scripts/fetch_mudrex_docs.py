"""
Script to fetch Mudrex API documentation from public URL
and prepare it for ingestion into the vector database
"""
import requests
from pathlib import Path
import sys
import json
import time

def fetch_mudrex_docs():
    """Fetch documentation from Mudrex API docs website"""
    base_url = "https://docs.trade.mudrex.com"
    
    print(f"Fetching documentation from: {base_url}")
    print("Note: If this is a ReadMe.io or similar docs platform,")
    print("      we'll fetch the main content and structure it.")
    
    try:
        # Fetch the main page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"✓ Successfully fetched documentation ({len(response.content)} bytes)")
        
        # Save raw HTML for inspection
        html_file = Path("docs") / "mudrex-raw.html"
        html_file.write_text(response.text, encoding='utf-8')
        print(f"✓ Saved raw HTML to: {html_file}")
        
        # Try to extract content
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find main content area (common in documentation sites)
        main_content = soup.find('main') or soup.find('article') or soup.find(class_='content') or soup.find(id='content')
        
        if main_content:
            # Remove navigation, scripts, styles
            for tag in main_content.find_all(['script', 'style', 'nav', 'footer', 'aside']):
                tag.decompose()
            
            content = main_content.get_text(separator='\n', strip=True)
        else:
            # Fallback: get all text
            for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'aside', 'header']):
                tag.decompose()
            content = soup.get_text(separator='\n', strip=True)
        
        return content
        
    except Exception as e:
        print(f"✗ Error fetching documentation: {e}")
        print("\n💡 Alternative: You can manually copy the documentation")
        print("   1. Visit: https://docs.trade.mudrex.com")
        print("   2. Copy all the text content")
        print("   3. Save to: docs/mudrex-api-manual.md")
        return None


def save_documentation(content: str):
    """Save documentation to docs directory"""
    if not content:
        print("⚠ No content to save")
        return None
    
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    output_file = docs_dir / "mudrex-api-documentation.md"
    
    # Add markdown header
    from datetime import datetime
    markdown_content = f"""# Mudrex API Documentation

**Source:** https://docs.trade.mudrex.com  
**Fetched:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{content}
"""
    
    output_file.write_text(markdown_content, encoding='utf-8')
    
    print(f"✓ Saved documentation to: {output_file}")
    print(f"  File size: {output_file.stat().st_size:,} bytes")
    print(f"  Lines: {len(content.splitlines()):,}")
    
    return output_file


def create_manual_template():
    """Create a template file for manual documentation entry"""
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    template_file = docs_dir / "mudrex-api-MANUAL.md"
    
    template = """# Mudrex API Documentation (Manual Entry)

**Source:** https://docs.trade.mudrex.com  
**Instructions:** Copy paste the content from the Mudrex docs website here

---

## Overview

[Copy the overview section here]

## Authentication

[Copy authentication details here]

### API Keys

[Copy API key information]

### Headers Required

[Copy required headers]

## Endpoints

### Wallet Endpoints

[Copy wallet endpoint documentation]

### Futures Endpoints

[Copy futures endpoint documentation]

### Orders Endpoints

[Copy order management documentation]

### Positions Endpoints

[Copy position management documentation]

## Error Codes

[Copy error code documentation]

## Rate Limits

[Copy rate limit information]

## Examples

[Copy code examples]

---

**Instructions:**
1. Visit: https://docs.trade.mudrex.com
2. Copy ALL sections of the documentation
3. Paste them in appropriate sections above
4. Keep code examples, error messages, endpoint details
5. Save this file
6. Run: python scripts/ingest_docs.py
"""
    
    template_file.write_text(template, encoding='utf-8')
    print(f"✓ Created manual template: {template_file}")
    print("  Fill this file if automatic fetching doesn't work well")
    
    return template_file


def main():
    """Main function"""
    print("=" * 60)
    print("Mudrex API Documentation Fetcher")
    print("=" * 60)
    
    # Fetch documentation
    content = fetch_mudrex_docs()
    
    # Save to file
    if content:
        output_file = save_documentation(content)
        
        print("\n" + "=" * 60)
        print("✓ Documentation fetched successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Review the file: docs/mudrex-api-documentation.md")
        print("2. If content looks good, run: python scripts/ingest_docs.py")
        print("3. If content is incomplete, use the manual template")
        print("4. Start the bot: python main.py")
    else:
        # Create manual template
        template_file = create_manual_template()
        
        print("\n" + "=" * 60)
        print("⚠ Automatic fetch had issues")
        print("=" * 60)
        print("\n📝 MANUAL OPTION:")
        print(f"1. Edit: {template_file}")
        print("2. Visit: https://docs.trade.mudrex.com")
        print("3. Copy paste all documentation into the template")
        print("4. Save the file")
        print("5. Run: python scripts/ingest_docs.py")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
