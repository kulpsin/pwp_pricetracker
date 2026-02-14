#/usr/bin/env python3
"""
Collection of Database testing scripts using pytest
"""

import os
import tempfile
from datetime import datetime

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy import event

from pricetracker.models import Product, Price, User
from pricetracker.db import db
from pricetracker import create_app, utils


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):  # pylint: disable=W0613 (unused-argument)
    """Enables Foreign Key support"""
    utils.set_sqlite_pragma(dbapi_connection)


# based on https://flask.palletsprojects.com/en/stable/testing/
# we don't need a client for database testing, just the db handle
@pytest.fixture(name="db_handle")
def fixture_db_handle():
    """Fixture: basic DB-handle"""
    db_fd, db_fname = tempfile.mkstemp()
    config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_fname,
        "TESTING": True,
        "SECRET_KEY": 'test',
    }

    app = create_app(config)

    ctx = app.app_context()
    ctx.push()
    db.create_all()

    yield db

    db.session.rollback()
    db.drop_all()
    db.session.remove()
    ctx.pop()
    os.close(db_fd)
    os.unlink(db_fname)


def _get_user() -> User:
    """Returns default user"""
    return User(
        email="test-user-1@localhost",
        password="placeholder",
    )


def _get_product(active: bool=True, product_str: str="1234", notes: str|None=None) -> Product:
    """
    Returns a new Product-model.

    :param active: Is the product active
    :type active: bool
    :param product_str: Appended to name and url
    :type product_str: str
    :param notes: Extra notes added to the product
    :type notes: str | None
    :return: New product model
    :rtype: Product
    """
    product = Product(
        name=f"TestProduct{product_str}",
        url=f"https://www.mytrackablestore.fi/product/{product_str}",
        active=active,
    )
    if notes is not None:
        product.notes = notes
    return product


def _get_price(timestamp: datetime=datetime.now(), value: float=123.45) -> Price:
    """
    Docstring for _get_price

    :param timestamp: Exact time when the price was checked (default: now())
    :type timestamp: datetime
    :param value: The price value (default: 123.45)
    :type value: float
    :return: New price model
    :rtype: Product
    """
    price = Price(
        timestamp=timestamp,
        value=value,
    )
    return price


def test_create_user(db_handle):
    """
    Tests that we can create an user
    """
    user = _get_user()
    db_handle.session.add(user)

    assert User.query.count() == 1


def test_create_all(db_handle):
    """
    Tests that we can
    1. create all objects: User, Product, Price
    2. set relationships between objects
    3. assert that objects and relationships can be queried
    """
    # Get default test objects
    user = _get_user()
    product = _get_product()
    price = _get_price()
    product.user = user
    price.product = product
    db_handle.session.add(user)
    db_handle.session.add(product)
    db_handle.session.add(price)
    db_handle.session.commit()

    assert User.query.count() == 1
    assert Product.query.count() == 1
    assert Price.query.count() == 1

    db_user = User.query.first()
    db_product = Product.query.first()
    db_price = Price.query.first()

    assert db_price.product == db_product
    assert db_price in db_product.prices
    assert db_product.user == db_user
    assert db_product in db_user.products
