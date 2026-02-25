#!/usr/bin/env python3
"""
Miscellanious utils and URL converters
"""

from werkzeug.routing import BaseConverter
from werkzeug.exceptions import NotFound

from .models import Product

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


class ProductConverter(BaseConverter):
    def to_python(self, value):
        db_product = Product.query.filter_by(id=value).first()
        if db_product is None:
            raise NotFound
        return db_product

    def to_url(self, value):
        return value.id