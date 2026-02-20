import argparse
import time
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from ollama import chat
from playwright.sync_api import sync_playwright

def fetch_page(url):

    # Add a User-Agent header so the site doesn't block the bot immediately
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = Request(url, headers=headers)
    page = urlopen(req)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    return soup

def extract_price_text(soup):
    # Remove script and style elements
    for script in soup(["script", "style", "meta", "noscript"]):
        script.extract()

        # Preprocessing
        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_content = '\n'.join(lines)

        # Truncate content to save tokens (product info is usually near the top)
        clean_content = clean_content[:5000]

    print("🤖 Analyzing HTML with LM...")

    response = chat(
        model="ministral-3",
        messages=[
            {
                "role": "user",
                "content": f"You are part of a price tracker API. Look at the text content of the given web page and identify the current main price of the product. Output ONLY the number (e.g. 499.00) using a dot as the decimal separator, or the text 'NaN' if you cannot find a price. Here is the text content:\n\n{clean_content}"
            }
        ]
    )

    return response.message.content.strip() 

# Generated with Gemini 3.0 Pro
def nuke_cookie_banners(page):
    """
    Injects CSS to hide common cookie/consent banners and unlocks scrolling.
    """
    # Universal CSS to hide elements with 'cookie' or 'consent' in their ID/Class
    # We use !important to override the site's styles
    page.add_style_tag(content="""
        [id*="cookie"], [class*="cookie"],
        [id*="consent"], [class*="consent"],
        [id*="onetrust"], .fc-consent-root,
        #CybotCookiebotDialog, #usercentrics-root
        {
            display: none !important;
            visibility: hidden !important;
        }
        /* Restore scrolling if the banner locked the body */
        body { overflow: auto !important; }
    """)

def get_screenshot(url, scroll=0):
    print(f"📸 Snapping the web page...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Scroll down to trigger any lazy-loaded content
            page.mouse.wheel(0, 500)
            page.wait_for_timeout(1000)
            
            nuke_cookie_banners(page)
            
            # Scroll back to the top
            page.evaluate("window.scrollTo(0, 0)")

            # Scroll further down (if necessary)
            if scroll > 0:
                page.mouse.wheel(0, scroll)
                page.wait_for_timeout(1000)
            
            # Wait a moment for any sticky headers to reset
            page.wait_for_timeout(500) 

            return page.screenshot(full_page=False)
            
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None
        finally:
            browser.close()

def extract_price_vision(image_bytes):
    print("🤖 Analyzing image with VLM...")

    response = chat(
        model="ministral-3",
        messages=[
            {
                "role": "user",
                "content": "You are part of a price tracker API. Look at this product page and identify the current main price. Output ONLY the number (e.g. 499.00) using a dot as the decimal separator, or the text 'NaN' if you cannot find a price.",
                "images": [image_bytes]
            }
        ]
    )
    return response.message.content.strip()

# CLI usage: python query.py [url] (defaults to vision model, which seems to perform better)
# CLI usage: python query.py -m both [url] (to see both vision and text predictions)
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-m", default="vision", help="The model to use for price extraction: 'vision', 'text', or 'both'")
    parser.add_argument("url", help="The URL of the product page")
    args = parser.parse_args()
    img_bytes = None

    if args.m in ["vision", "both"]:
        
        img_bytes = get_screenshot(args.url)
        if img_bytes:

            # ---------------------------------------------------------
            # DEBUG: Uncomment the lines below to see what the LLM sees
            # ---------------------------------------------------------
            with open("debug_screenshot_1.png", "wb") as f:
                f.write(img_bytes)
            # ---------------------------------------------------------

            price_text = extract_price_vision(img_bytes)
            if price_text.lower() == "nan":

                # Try again after scrolling down, in case the price is further down the page
                print(f"└──Price not found in initial screenshot, trying again after scrolling down...")
                img_bytes = get_screenshot(args.url, scroll=800)

                if img_bytes:
                    # -------------------------------------------------------------
                    # DEBUG: Uncomment the lines below to see the second screenshot
                    # -------------------------------------------------------------
                    with open("debug_screenshot_2.png", "wb") as f:
                        f.write(img_bytes)
                    # -------------------------------------------------------------

                    price_text = extract_price_vision(img_bytes)
            try:
                price = round(float(price_text), 2)
                print(f"└──Extracted price (vision model): {price:.2f}")
            except ValueError:
                print(f"Could not extract a valid price from vision model. Output was: '{price_text:.2f}'")

    if (args.m in ["text", "both"]):

        time.sleep(1)
        soup = fetch_page(args.url)
        price_text = extract_price_text(soup)

        try:
            price = round(float(price_text), 2)
            print(f"└──Extracted price (text model): {price:.2f}")
        except ValueError:
            print(f"Could not extract a valid price from text model. Output was: '{price_text:.2f}'")