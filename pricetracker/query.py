"""
Usage:
    python query.py [-M METHOD] [-m MODALITY] URL

Examples:
    python query.py -M openrouter -m vision URL
    python query.py -M ollama -m text URL
"""

import argparse
import time
import base64
import os
from dotenv import load_dotenv
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from ollama import chat
from openai import OpenAI
from playwright.sync_api import sync_playwright

load_dotenv()

def fetch_page(url):
    """
    Fetches the HTML content of the given URL and returns a BeautifulSoup object for parsing.
    
    Args:
        url (str): The URL of the web page to fetch.
        
    Returns:
        BeautifulSoup: A BeautifulSoup object containing the parsed HTML of the page.
    """

    headers = {'User-Agent': 'Mozilla/5.0'}
    req = Request(url, headers=headers)
    page = urlopen(req)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    return soup

def extract_price_text(method, soup):
    """
    Extracts the price from the text content of the page using a language model. First tries using OpenRouter, but if that fails (e.g. due to token limits or other issues), falls back to using the Ministral 3 model via Ollama.
    
    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the parsed HTML of the page.
        
    Returns:
        str: The extracted price as a string (e.g. "499.00") or "NaN" if no price could be found. Hopefully.
    
    Raises:
        Exception: If both language models encounter errors, 
    """

    # Remove script and style elements
    for script in soup(["script", "style", "meta", "noscript"]):
        script.extract()

        # Preprocessing
        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_content = '\n'.join(lines)

        # Truncate content to save tokens (product info is usually near the top)
        clean_content = clean_content[:5000]

    if method in ["or", "openrouter"]:

        if not os.getenv("OPENROUTER_API_KEY"):
            raise Exception("OpenRouter API key not found.")
        
        try:
            print("🤖 Sending HTML to OpenRouter for Analysis...")
            client = OpenAI(
                base_url = "https://openrouter.ai/api/v1",
                api_key = os.getenv("OPENROUTER_API_KEY")
            )
            response = client.chat.completions.create(
                model = "google/gemma-4-31b-it:free",
                messages = [
                    {
                        "role": "user", 
                        "content": f"You are part of a price tracker API. Look at the text content of the given web page and identify the current main price of the product. Output ONLY the number (e.g. 499.00) using a dot as the decimal separator, or the text 'NaN' if you cannot find a price. Here is the text content:\n\n{clean_content}"
                    }
                ],
                extra_body = {
                    "models": ["google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-nano-12b-v2-vl:free"],
                }
            )
            return response.choices[0].message.content.strip()
        
        except Exception as e:

            print(f"Error with OpenRouter: {e}")

            if method == "auto":
                print(f"Falling back to Ollama for text analysis...")
                method = "ollama"
            else:
                raise Exception("OpenRouter encountered an error. See above for details.")
        
    if method in ["ollama", "ol"]:

        try:

            print("🤖 Analyzing HTML with LM...")

            response = chat(
                model = "ministral-3",
                messages=[
                    {
                        "role": "user",
                        "content": f"You are part of a price tracker API. Look at the text content of the given web page and identify the current main price of the product. Output ONLY the number (e.g. 499.00) using a dot as the decimal separator, or the text 'NaN' if you cannot find a price. Here is the text content:\n\n{clean_content}"
                    }
                ]
            )

            return response.message.content.strip() 
        
        except Exception as e2:

            print(f"Error with Ollama: {e2}")
            
            if e and e2:
                raise Exception("Both language models encountered errors. See above for details.")
            else:
                raise Exception("Ollama encountered an error. See above for details.")

def nuke_cookie_banners(page):
    """
    Injects CSS to hide common cookie/consent banners and restore scrolling if the banner locked the body.

    Args:
        page (playwright.sync_api.Page): The Playwright page object to modify.

    (Generated with Gemini 3.0 Pro)
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
    """
    Uses Playwright to load the web page and take a screenshot. Scrolls down if needed to trigger lazy loading of content.

    Args:
        url (str): The URL of the web page to screenshot.
        scroll (int): Optional number of pixels to scroll down after the initial load to trigger lazy loading of content. Default is 0 (no additional scrolling).

    Returns:
        bytes: The screenshot of the web page as bytes, or None if an error occurred.
    """
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

def extract_price_vision(method, image_bytes):
    """
    Finds the price in the product page screenshot using a vision-language model. The model is prompted to return only the price number or 'NaN' if it cannot find a price.

    First tries using OpenRouter, but if that fails (e.g. due to token limits or other issues), falls back to using the Ministral 3 model via Ollama.

    Args:
        image_bytes (bytes): The screenshot of the product page as bytes.

    Returns:
        str: The extracted price as a string (e.g. "499.00") or "NaN" if no price could be found. Hopefully.

    Raises:
        Exception: If both vision models encounter errors, an exception is raised with details printed to the console.
    """

    if method in ["or", "openrouter", "auto"]:

        if not os.getenv("OPENROUTER_API_KEY"):
            raise Exception("OpenRouter API key not found.")

        try:
            print("🤖 Sending image to OpenRouter for analysis...")
            client = OpenAI(
                base_url = "https://openrouter.ai/api/v1",
                api_key = os.getenv("OPENROUTER_API_KEY")
            )

            base64_image = base64.b64encode(image_bytes).decode('utf-8')

            response = client.chat.completions.create(
                model = "google/gemma-4-31b-it:free",
                messages = [
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "text",
                                "text": "You are part of a price tracker API. Look at this product page and identify the current main price. Output ONLY the number (e.g. 499.00) using a dot as the decimal separator, or the text 'NaN' if you cannot find a price."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                extra_body = {
                    "models": ["google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-nano-12b-v2-vl:free"],
                }
            )

            return response.choices[0].message.content.strip()

        except Exception as e:

            print(f"Error with OpenRouter: {e}")

            if method == "auto":
                print(f"Falling back to Ollama for vision analysis...")
                method = "ollama"
            else:
                raise Exception("OpenRouter encountered an error. See above for details.")

    if method in ["ollama", "ol"]:

        try:

            print("🤖 Analyzing image with Ministral-3...")
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
    
        except Exception as e2:

            print(f"Error with Ministral-3: {e2}")

            if e and e2:
                raise Exception("Both vision models encountered errors. See above for details.")
            else:
                raise Exception("Ollama encountered an error. See above for details.")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-M", "--method", help="The method to use for price extraction: 'or' or 'openrouter' for the OpenRouter API, 'ol' or 'ollama' for the Ollama API, or 'auto' to try OpenRouter first and fall back to Ollama if it fails", default="auto")
    parser.add_argument("-m", "--modality", default="auto", help="The modality to use for price extraction: 'vision', 'text', or 'auto' to try vision first and fall back to text if it fails")
    parser.add_argument("url", help="The URL of the product page")
    args = parser.parse_args()
    img_bytes = None

    if args.modality in ["vision", "auto"]:
        
        img_bytes = get_screenshot(args.url)
        
        if img_bytes:

            # ---------------------------------------------------------
            # DEBUG: Uncomment the lines below to see what the LLM sees
            # ---------------------------------------------------------
            with open("debug_screenshot_1.png", "wb") as f:
                f.write(img_bytes)
            # ---------------------------------------------------------

            price_text = extract_price_vision(args.method, img_bytes)
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

                    price_text = extract_price_vision(args.method, img_bytes)
            try:
                price = round(float(price_text), 2)
                print(f"└──Extracted price (vision model): {price:.2f}")
            except ValueError:
                print(f"Could not extract a valid price from vision model. Output was: '{price_text}'")
                if args.modality == "auto":
                    print(f"Falling back to text extraction method...")
                    args.modality = "text"

    if (args.modality in ["text"]):

        time.sleep(1)
        soup = fetch_page(args.url)
        price_text = extract_price_text(args.method, soup)

        try:
            price = round(float(price_text), 2)
            print(f"└──Extracted price (text model): {price:.2f}")
        except ValueError:
            print(f"Could not extract a valid price from text model. Output was: '{price_text}'")