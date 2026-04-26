#!/usr/bin/env python3
"""
Miscellanious utils and URL converters
"""

import datetime
from .db import db
from . import models


def set_sqlite_pragma(dbapi_connection):
    """Enables Foreign Key support"""
    # Source: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#foreign-key-support
    # the sqlite3 driver will not set PRAGMA foreign_keys
    # if autocommit=False; set to True temporarily
    ac = dbapi_connection.autocommit
    dbapi_connection.autocommit = True

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

    # restore previous autocommit setting
    dbapi_connection.autocommit = ac


def call_llm_fetch_price(url: str) -> float:
    """
    Call the LLM service to fetch price from a given URL.
    
    This uses the PriceExtractor from query.py
    
    Args:
        url: Product URL to fetch price from
        
    Returns:
        float: The fetched price value
        
    Raises:
        ValueError: If LLM fails to extract price or URL is invalid
    """
    from .query import PriceExtractor
    from bs4 import BeautifulSoup
    
    try:
        extractor = PriceExtractor()
        
        # Fetch page data (try vision first, then fall back to text)
        page_data = extractor.fetch_page_data(url, modality="auto")
        
        price_text = None
        
        # Try vision extraction first
        if page_data.get("screenshot"):
            try:
                price_text = extractor.extract_price_vision("auto", page_data["screenshot"])
                if price_text.lower() != "nan":
                    price = float(price_text)
                    print(f"✓ Price extracted via vision: €{price}")
                    return price
            except Exception as e:
                print(f"Vision extraction failed: {e}")
        
        # Fall back to text extraction
        if page_data.get("html") and price_text is None:
            try:
                soup = BeautifulSoup(page_data["html"], "html.parser")
                price_text = extractor.extract_price_text("auto", soup)
                if price_text.lower() != "nan":
                    price = float(price_text)
                    print(f"✓ Price extracted via text: €{price}")
                    return price
            except Exception as e:
                print(f"Text extraction failed: {e}")
        
        raise ValueError(f"Could not extract price from {url}")
    
    except Exception as e:
        raise ValueError(f"LLM price extraction failed for {url}: {str(e)}") from e


def get_price_from_llm(hruid: str) -> models.Price:
    """
    Fetch price from LLM for a product and store it in the database.
    """
    # Fetch the product
    product = models.Product.query.filter_by(hruid=hruid).first()
    if not product:
        raise ValueError(f"Product with hruid '{hruid}' not found")
    
    # Call LLM to fetch price from product URL
    try:
        price_value = call_llm_fetch_price(product.url)
    except Exception as e:
        raise ValueError(f"Failed to fetch price from LLM for URL {product.url}: {str(e)}") from e
    
    # Create new Price entry
    new_price = models.Price(
        product_id=product.id,
        value=price_value,
        timestamp=datetime.datetime.now()
    )
    
    # Save to database
    try:
        db.session.add(new_price)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Failed to save price to database: {str(e)}") from e
    
    return new_price
