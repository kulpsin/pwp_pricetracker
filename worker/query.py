#!/usr/bin/env python3
"""
CLI wrapper for price extraction.

Usage:
    python query.py [-M METHOD] [-m MODALITY] URL

Examples:
    python query.py -M openrouter -m vision URL
    python query.py -M ollama -m text URL
"""

import argparse
import sys

sys.tracebacklimit = 0

from worker.extractor import PriceExtractor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-M", "--method",
                        help="Method for price extraction: 'or'/'openrouter' for OpenRouter API, "
                             "'ol'/'ollama' for Ollama API, or 'auto' to try OpenRouter first "
                             "and fall back to Ollama if it fails",
                        default="auto")
    parser.add_argument("-m", "--modality",
                        default="auto",
                        help="Modality: 'vision', 'text', or 'auto' to try vision first "
                             "and fall back to text if it fails")
    parser.add_argument("url", help="The URL of the product page")
    args = parser.parse_args()

    extractor = PriceExtractor()

    try:
        price = extractor.run(args.url, method=args.method, modality=args.modality)
        print(f"Final price: {price:.2f}")
    except Exception as e:
        print(f"Failed to extract price: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
