"""
Price extraction using LLM vision or text analysis.

An OpenAI-compatible API key, OpenRouter API key, or an Ollama setup is required.
    To use OpenAI-compatible API, set your API key: OPENAI_API_KEY=your_api_key_here
    To use a custom endpoint: OPENAI_BASE_URL=http://localhost:8000/v1
    To specify the model: OPENAI_MODEL=gpt-4o
    To use OpenRouter, set your API key: OPENROUTER_API_KEY=your_api_key_here
    To use Ollama, make sure you have the Ministral-3 model installed locally
"""

import base64
import os

from bs4 import BeautifulSoup
from ollama import chat
from openai import OpenAI
from playwright.sync_api import sync_playwright


class PriceExtractor:
    def __init__(self):
        self.openrouter_client = None
        self.openai_client = None

    def get_openai_client(self):
        if self.openai_client is None:
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OpenAI API key not found in environment variables.")

            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.openai_client = OpenAI(
                base_url=base_url,
                api_key=os.getenv("OPENAI_API_KEY"),
                timeout=10.0,
                max_retries=0
            )

        return self.openai_client

    def get_openrouter_client(self):
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

                page.mouse.wheel(0, 500)
                page.wait_for_timeout(1000)

                self.nuke_cookie_banners(page)

                page.evaluate("window.scrollTo(0, 0)")

                if scroll > 0:
                    page.mouse.wheel(0, scroll)
                    page.wait_for_timeout(1000)

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
        if method not in ["or", "openrouter", "openai", "ollama", "ol", "auto"]:
            raise ValueError(f"Unsupported method: '{method}'")

        or_error = None

        for script in soup(["script", "style", "meta", "noscript"]):
            script.extract()

        cookie_terms = ['cookie', 'consent', 'onetrust', 'cybotcookiebot', 'usercentrics']
        for banner in soup.find_all(attrs={"id": lambda x: x and any(w in x.lower() for w in cookie_terms)}):
            banner.extract()
        for banner in soup.find_all(attrs={"class": lambda x: x and any(w in (x if isinstance(x, str) else ' '.join(x)).lower() for w in cookie_terms)}):
            banner.extract()

        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_content = '\n'.join(lines)
        clean_content = clean_content[:5000]

        if method in ["openai", "auto"]:
            try:
                client = self.get_openai_client()
                print("Sending HTML to OpenAI-compatible API for Analysis...")

                response = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "google/gemma-4-31b-it:free"),
                    messages=[{
                        "role": "user",
                        "content": f"You are part of a price tracker API. Look at the text content of the given web page and identify the current main price of the product. Output ONLY the number (e.g. 499.00) using a dot as the decimal separator, or the text 'NaN' if you cannot find a price. Here is the text content:\n\n{clean_content}"
                    }],
                )
                content = response.choices[0].message.content
                return content.strip(" \u20ac$") if content else "NaN"

            except Exception as e:
                or_error = e
                print(f"Error with OpenAI-compatible API: {e}")

                if method == "auto":
                    print("Falling back to OpenRouter for text analysis...")
                    method = "or"
                else:
                    raise Exception(f"OpenAI-compatible API encountered an error: {e}")

        if method in ["or", "openrouter", "auto"]:
            try:
                client = self.get_openrouter_client()
                print("Sending HTML to OpenRouter for Analysis...")

                response = client.chat.completions.create(
                    model="google/gemma-4-31b-it:free",
                    messages=[{
                        "role": "user",
                        "content": f"You are part of a price tracker API. Look at the text content of the given web page and identify the current main price of the product. Output ONLY the number (e.g. 499.00) using a dot as the decimal separator, or the text 'NaN' if you cannot find a price. Here is the text content:\n\n{clean_content}"
                    }],
                    extra_body={
                        "models": ["google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-nano-12b-v2-vl:free"],
                    }
                )
                content = response.choices[0].message.content
                return content.strip(" \u20ac$") if content else "NaN"

            except Exception as e:
                or_error = e
                print(f"Error with OpenRouter: {e}")

                if method == "auto":
                    print("Falling back to Ollama for text analysis...")
                    method = "ollama"
                else:
                    raise Exception(f"OpenRouter encountered an error: {e}")

        if method in ["ollama", "ol"]:
            try:
                print("Analyzing HTML with Ministral-3...")
                response = chat(
                    model="ministral-3",
                    messages=[{
                        "role": "user",
                        "content": f"You are part of a price tracker API. Look at the text content of the given web page and identify the current main price of the product. Output ONLY the number (e.g. 499.00) using a dot as the decimal separator, or the text 'NaN' if you cannot find a price. Here is the text content:\n\n{clean_content}"
                    }]
                )

                content = response.message.content
                return content.strip(" \u20ac$") if content else "NaN"

            except Exception as e2:
                print(f"Error with Ollama: {e2}")

                if or_error and e2:
                    raise Exception("Both language models encountered errors. See above for details.")
                else:
                    raise Exception(f"Ollama encountered an error: {e2}")

    def nuke_cookie_banners(self, page):
        page.add_style_tag(content="""
            [id*="cookie"], [class*="cookie"],
            [id*="consent"], [class*="consent"],
            [id*="onetrust"], .fc-consent-root,
            #CybotCookiebotDialog, #usercentrics-root
            {
                display: none !important;
                visibility: hidden !important;
            }
            body { overflow: auto !important; }
        """)

    def extract_price_vision(self, method, image_bytes):
        if method not in ["or", "openrouter", "openai", "ollama", "ol", "auto"]:
            raise ValueError(f"Unsupported method: '{method}'")

        or_error = None

        if method in ["openai", "auto"]:
            try:
                client = self.get_openai_client()
                print("Sending image to OpenAI-compatible API for analysis...")

                base64_image = base64.b64encode(image_bytes).decode('utf-8')

                response = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "google/gemma-4-31b-it:free"),
                    messages=[{
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
                    }],
                )

                content = response.choices[0].message.content
                return content.strip(" \u20ac$") if content else "NaN"

            except Exception as e:
                or_error = e
                print(f"Error with OpenAI-compatible API: {e}")

                if method == "auto":
                    print("Falling back to OpenRouter for vision analysis...")
                    method = "or"
                else:
                    raise Exception(f"OpenAI-compatible API encountered an error: {e}")

        if method in ["or", "openrouter", "auto"]:
            try:
                client = self.get_openrouter_client()
                print("Sending image to OpenRouter for analysis...")

                base64_image = base64.b64encode(image_bytes).decode('utf-8')

                response = client.chat.completions.create(
                    model="google/gemma-4-31b-it:free",
                    messages=[{
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
                    }],
                    extra_body={
                        "models": ["google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-nano-12b-v2-vl:free"],
                    }
                )

                content = response.choices[0].message.content
                return content.strip(" \u20ac$") if content else "NaN"

            except Exception as e:
                or_error = e
                print(f"Error with OpenRouter: {e}")

                if method == "auto":
                    print("Falling back to Ollama for vision analysis...")
                    method = "ollama"
                else:
                    raise Exception(f"OpenRouter encountered an error: {e}")

        if method in ["ollama", "ol"]:
            try:
                print("Analyzing image with Ministral-3...")
                response = chat(
                    model="ministral-3",
                    messages=[{
                        "role": "user",
                        "content": "You are part of a price tracker API. Look at this product page and identify the current main price. Output ONLY the number (e.g. 499.00) using a dot as the decimal separator, or the text 'NaN' if you cannot find a price.",
                        "images": [image_bytes]
                    }]
                )
                content = response.message.content
                return content.strip(" \u20ac$") if content else "NaN"

            except Exception as e2:
                print(f"Error with Ministral-3: {e2}")

                if or_error and e2:
                    raise Exception("Both vision models encountered errors. See above for details.")
                else:
                    raise Exception(f"Ollama encountered an error: {e2}")

    def run(self, url, method="auto", modality="auto"):
        page_data = self.fetch_page_data(url, modality)
        img_bytes = page_data.get("screenshot")
        html_text = page_data.get("html")
        page_data_scroll = None
        price = None

        if modality in ["vision", "auto"]:
            if img_bytes:
                price_text = self.extract_price_vision(method, img_bytes)
                if price_text.lower() == "nan":
                    print("Price not found in initial screenshot, trying again after scrolling down...")
                    page_data_scroll = self.fetch_page_data(url, modality, scroll=800)
                    img_bytes = page_data_scroll.get("screenshot")

                    if img_bytes:
                        price_text = self.extract_price_vision(method, img_bytes)
                try:
                    if price_text.lower() == "nan":
                        raise ValueError("Price not found")
                    price = round(float(price_text), 2)
                    print(f"Extracted price (vision model): {price:.2f}")
                except ValueError:
                    print(f"Could not extract a valid price from vision model. Output was: '{price_text}'")
                    if modality == "auto":
                        modality = "text"

        if modality == "text" or (modality == "auto" and price is None):
            if not html_text and modality == "text" and page_data_scroll:
                html_text = page_data_scroll.get("html")

            if html_text:
                soup = BeautifulSoup(html_text, "html.parser")
                price_text = self.extract_price_text(method, soup)

                try:
                    if price_text.lower() == "nan":
                        raise ValueError("Price not found")
                    price = round(float(price_text), 2)
                    print(f"Extracted price (text model): {price:.2f}")
                except ValueError:
                    print(f"Could not extract a valid price from text model. Output was: '{price_text}'")
            else:
                print("Could not fetch HTML to extract price.")

        if price is None:
            raise ValueError(f"Could not extract price from {url}")

        return price
