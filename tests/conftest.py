"""
This module contains functions shared with multiple tests
"""
import os
import tempfile

import pytest
from flask.testing import FlaskClient
from werkzeug.datastructures import Headers

from pricetracker.models import Product, User, ApiKey
from pricetracker.db import db
from pricetracker import create_app

TEST_KEYS = [
    "verysafetestkey1",
    "verysafetestkey2",
    "verysafetestkey3",
]


def _populate_db():
    """Populate the DB with two users and two products for each"""

    _test_data = {
        "users": [],
        "keys": [],
        "products": [],
    }

    for user_idx in range(2):
        user = User(
            email=f"test-resource-user-{user_idx}@localhost",
        )
        db.session.add(user)
        _test_data["users"].append(user)

        # Generate unique key for a user
        key = TEST_KEYS[user_idx]
        apikey = ApiKey(key=key)
        apikey.user = user
        db.session.add(apikey)
        db.session.commit()
        _test_data["keys"].append(key)

        for product_idx in range(2):
            name = "user-{user_idx}-test-product"
            hruid = Product.gen_hruid(name)
            product = Product(
                name=name,
                url=f"http://localhost/product-{product_idx}",
                active=True,
                user = user,
                hruid = hruid,
            )
            db.session.add(product)
            db.session.commit()
            _test_data["products"].append(product)

    return _test_data


# https://stackoverflow.com/questions/16416001/set-http-headers-for-all-requests-in-a-flask-test
class AuthHeaderClient(FlaskClient):
    """Placeholder for authentication testing"""
    def __init__(self, *args, default_key=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_key = default_key

    def open(self, *args, **kwargs):
        headers = kwargs.pop('headers', Headers())

        # Use default_key if X-Api-Key header is missing
        if not headers.get('X-Api-Key') and self.default_key:
            headers['X-Api-Key'] = self.default_key

        kwargs['headers'] = headers
        return super().open(*args, **kwargs)


@pytest.fixture(name="test_app")
def fixture_test_app():
    """Fixture: basic app"""
    db_fd, db_fname = tempfile.mkstemp()
    config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_fname,
        "TESTING": True,
        "SECRET_KEY": 'test',
        "CACHE_TYPE": 'SimpleCache',
    }

    app = create_app(config)

    ctx = app.app_context()
    ctx.push()
    db.create_all()

    yield app

    db.session.rollback()
    db.drop_all()
    db.session.remove()
    ctx.pop()
    os.close(db_fd)
    os.unlink(db_fname)


@pytest.fixture(name="test_db")
def fixture_test_db(test_app):
    """Fixture with empty db"""
    yield db


@pytest.fixture(name="db_data")
def fixture_populate_test_db(test_db):
    """Fixture with populated db"""
    yield _populate_db()


@pytest.fixture(name="client")
def fixture_client(test_app, db_data):
    """Fixture with populated db without authentication key"""
    yield test_app.test_client()


@pytest.fixture(name="auth_client")
def fixture_auth_client(test_app, db_data):
    """Fixture with populated db with authentication key"""
    first_key = db_data["keys"][0]
    test_app.test_client_class = AuthHeaderClient
    yield test_app.test_client(default_key=first_key)
