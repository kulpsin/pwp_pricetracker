"""
Contains the main logic for fetching a product page, extracting the price using either vision or text analysis with language models, and handling errors and fallbacks between different methods.

Either an OpenRouter API key or an Ollama setup is required to run this code.
    To use OpenRouter, set your API key in a .env file with the following content: OPENROUTER_API_KEY=your_api_key_here
    To use Ollama, make sure you have the Ministral-3 model installed locally

Usage:
    python query.py [-M METHOD] [-m MODALITY] URL

Examples:
    python query.py -M openrouter -m vision URL
    python query.py -M ollama -m text URL

(Most of the documentation for this code has been generated with GitHub Copilot)
"""

import argparse
import base64
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from ollama import chat
from openai import OpenAI
from playwright.sync_api import sync_playwright

load_dotenv()

class PriceExtractor:
    def __init__(self):
        self.openrouter_client = None

    def get_openrouter_client(self):
        """
        Initializes an OpenRouter client using the API key from environment variables.
        
        Returns:
            OpenAI: An instance of the OpenAI client configured for OpenRouter.
        
        Raises:
            ValueError: If the OpenRouter API key is not found in environment variables.
        """
        if self.openrouter_client is None:
            if not os.getenv("OPENROUTER_API_KEY"):
                raise ValueError("OpenRouter API key not found in environment variables.")
            
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                timeout=10.0,
                max_retries=0
            )

        return self.openrouter_client

    def fetch_page_data(self, url, modality, scroll=0):
        """
        Fetches the HTML content and/or screenshot of the given URL using Playwright.
        
        Args:
            url (str): The URL of the web page to fetch.
            modality (str): 'text' (html only), 'vision' (screenshot only), or 'auto' (both).
            scroll (int): Optional number of pixels to scroll down after the initial load.
            
        Returns:
            dict: A dictionary containing 'html' (str) and 'screenshot' (bytes).

        Raises:
            ValueError: If an unsupported modality is provided.

        (This function is mostly generated with Gemini 3.1 Pro, with some manual tweaks)
        """
        print(f"📸 Fetching the web page...")
        result = {"html": None, "screenshot": None}
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
                
                self.nuke_cookie_banners(page)
                
                # Scroll back to the top
                page.evaluate("window.scrollTo(0, 0)")

                # Scroll further down (if necessary)
                if scroll > 0:
                    page.mouse.wheel(0, scroll)
                    page.wait_for_timeout(1000)
                
                # Wait a moment for any sticky headers to reset
                page.wait_for_timeout(500) 

                if modality in ["text", "auto"]:
                    result["html"] = page.content()
                
                if modality in ["vision", "auto"]:
                    result["screenshot"] = page.screenshot(full_page=False)
                    
                return result
                
            except Exception as e:
                print(f"Error fetching page data: {e}")
                return result
            finally:
                browser.close()

    def extract_price_text(self, method, soup):
        """
        Extracts the price from the text content of the page using a language model. First tries using OpenRouter, but if that fails (e.g. due to token limits or other issues), falls back to using the Ministral 3 model via Ollama.
        
        Args:
            soup (BeautifulSoup): A BeautifulSoup object containing the parsed HTML of the page.
            
        Returns:
            str: The extracted price as a string (e.g. "499.00") or "NaN" if no price could be found. Hopefully.
        
        Raises:
            Exception: If both language models encounter errors, 
        """
        if method not in ["or", "openrouter", "ollama", "ol", "auto"]:
            raise ValueError(f"Unsupported method: '{method}'")

        or_error = None

        # vvv This part is generated with Gemini 3.1 Pro vvv

        # Remove script and style elements
        for script in soup(["script", "style", "meta", "noscript"]):
            script.extract()

        # Remove common cookie/consent banners to avoid feeding them to the text model
        cookie_terms = ['cookie', 'consent', 'onetrust', 'cybotcookiebot', 'usercentrics']
        for banner in soup.find_all(attrs={"id": lambda x: x and any(w in x.lower() for w in cookie_terms)}):
            banner.extract()
        for banner in soup.find_all(attrs={"class": lambda x: x and any(w in (x if isinstance(x, str) else ' '.join(x)).lower() for w in cookie_terms)}):
            banner.extract()

        # Preprocessing
        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_content = '\n'.join(lines)

        # Truncate content to save tokens (product info is usually near the top)
        clean_content = clean_content[:5000]
        
        # ^^^ This part is generated with Gemini 3.1 Pro ^^^

        if method in ["or", "openrouter", "auto"]:
            try:
                client = self.get_openrouter_client()
                print("🤖 Sending HTML to OpenRouter for Analysis...")
                
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
                content = response.choices[0].message.content
                return content.strip(" €$") if content else "NaN"
            
            except Exception as e:
                or_error = e
                print(f"Error with OpenRouter: {e}")

                if method == "auto":
                    print(f"Falling back to Ollama for text analysis...")
                    method = "ollama"
                else:
                    raise Exception(f"OpenRouter encountered an error: {e}")
            
        if method in ["ollama", "ol"]:
            try:
                print("🤖 Analyzing HTML with Ministral-3...")
                response = chat(
                    model = "ministral-3",
                    messages=[
                        {
                            "role": "user",
                            "content": f"You are part of a price tracker API. Look at the text content of the given web page and identify the current main price of the product. Output ONLY the number (e.g. 499.00) using a dot as the decimal separator, or the text 'NaN' if you cannot find a price. Here is the text content:\n\n{clean_content}"
                        }
                    ]
                )

                content = response.message.content
                return content.strip(" €$") if content else "NaN"
            
            except Exception as e2:
                print(f"Error with Ollama: {e2}")
                
                if or_error and e2:
                    raise Exception("Both language models encountered errors. See above for details.")
                else:
                    raise Exception(f"Ollama encountered an error: {e2}")

    def nuke_cookie_banners(self, page):
        """
        Injects CSS to hide common cookie/consent banners and restore scrolling if the banner locked the body.

        Args:
            page (playwright.sync_api.Page): The Playwright page object to modify.

        (Generated with Gemini 3.1 Pro)
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

    def extract_price_vision(self, method, image_bytes):
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
        if method not in ["or", "openrouter", "ollama", "ol", "auto"]:
            raise ValueError(f"Unsupported method: '{method}'")

        or_error = None

        if method in ["or", "openrouter", "auto"]:
            try:
                client = self.get_openrouter_client()
                print("🤖 Sending image to OpenRouter for analysis...")
                
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

                content = response.choices[0].message.content
                return content.strip(" €$") if content else "NaN"

            except Exception as e:
                or_error = e
                print(f"Error with OpenRouter: {e}")

                if method == "auto":
                    print(f"Falling back to Ollama for vision analysis...")
                    method = "ollama"
                else:
                    raise Exception(f"OpenRouter encountered an error: {e}")

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
                content = response.message.content
                return content.strip(" €$") if content else "NaN"
        
            except Exception as e2:
                print(f"Error with Ministral-3: {e2}")

                if or_error and e2:
                    raise Exception("Both vision models encountered errors. See above for details.")
                else:
                    raise Exception(f"Ollama encountered an error: {e2}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-M", "--method", help="The method to use for price extraction: 'or' or 'openrouter' for the OpenRouter API, 'ol' or 'ollama' for the Ollama API, or 'auto' to try OpenRouter first and fall back to Ollama if it fails", default="auto")
    parser.add_argument("-m", "--modality", default="auto", help="The modality to use for price extraction: 'vision', 'text', or 'auto' to try vision first and fall back to text if it fails")
    parser.add_argument("url", help="The URL of the product page")
    args = parser.parse_args()

    extractor = PriceExtractor()
    page_data = extractor.fetch_page_data(args.url, args.modality)
    img_bytes = page_data.get("screenshot")
    html_text = page_data.get("html")
    page_data_scroll = None
    price = None

    if args.modality in ["vision", "auto"]:
        if img_bytes:
            # ---------------------------------------------------------
            # DEBUG: Uncomment the lines below to see what the LLM sees
            # ---------------------------------------------------------
            with open("debug_screenshot_1.png", "wb") as f:
                f.write(img_bytes)
            # ---------------------------------------------------------

            price_text = extractor.extract_price_vision(args.method, img_bytes)
            if price_text.lower() == "nan":
                # Try again after scrolling down, in case the price is further down the page
                print(f"└──Price not found in initial screenshot, trying again after scrolling down...")
                page_data_scroll = extractor.fetch_page_data(args.url, args.modality, scroll=800)
                img_bytes = page_data_scroll.get("screenshot")

                if img_bytes:
                    # -------------------------------------------------------------
                    # DEBUG: Uncomment the lines below to see the second screenshot
                    # -------------------------------------------------------------
                    with open("debug_screenshot_2.png", "wb") as f:
                        f.write(img_bytes)
                    # -------------------------------------------------------------

                    price_text = extractor.extract_price_vision(args.method, img_bytes)
            try:
                if price_text.lower() == "nan":
                    raise ValueError("Price not found")
                price = round(float(price_text), 2)
                print(f"└──Extracted price (vision model): {price:.2f}")
            except ValueError:
                print(f"Could not extract a valid price from vision model. Output was: '{price_text}'")
                if args.modality == "auto":
                    print(f"Falling back to text extraction method...")
                    args.modality = "text"

    if args.modality == "text" or (args.modality == "auto" and price is None):
        if not html_text and args.modality == "text" and page_data_scroll:
            html_text = page_data_scroll.get("html")

        if html_text:
            soup = BeautifulSoup(html_text, "html.parser")
            price_text = extractor.extract_price_text(args.method, soup)

            try:
                if price_text.lower() == "nan":
                    raise ValueError("Price not found")
                price = round(float(price_text), 2)
                print(f"└──Extracted price (text model): {price:.2f}")
            except ValueError:
                print(f"Could not extract a valid price from text model. Output was: '{price_text}'")
        else:
            print("Could not fetch HTML to extract price.")
