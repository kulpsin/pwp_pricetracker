#/usr/bin/env python3
"""
Collection of Database testing scripts using pytest

Used
https://github.com/UniOulu-Ubicomp-Programming-Courses/pwp-sensorhub-example/blob/ex2-project-layout/tests/test_resource.py
as template for this file.
"""

import os
import hashlib
import json
import tempfile
from datetime import datetime

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy import event
from flask.testing import FlaskClient
from werkzeug.datastructures import Headers

from pricetracker.models import Product, Price, User
from pricetracker.db import db
from pricetracker import create_app, utils


TEST_KEY = "verysafetestkey"


# https://stackoverflow.com/questions/16416001/set-http-headers-for-all-requests-in-a-flask-test
class AuthHeaderClient(FlaskClient):
    """Placeholder for authentication testing"""
    def open(self, *args, **kwargs):
        headers = Headers({
            'X-Api-Key': TEST_KEY
        })
        extra_headers = kwargs.pop('headers', Headers())
        headers.extend(extra_headers)
        kwargs['headers'] = headers
        return super().open(*args, **kwargs)


@pytest.fixture(name="client")
def fixture_client():
    """Fixture: basic Client"""
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
    _populate_db()
    yield app.test_client()

    os.close(db_fd)
    os.unlink(db_fname)

    ctx.pop()


def _populate_db():
    """Populate the DB with two users and two products for each"""
    for user_idx in range(1, 3):
        user = User(
            email=f"test-resource-user-{user_idx}@localhost",
            password=hashlib.sha256(f"password{user_idx}".encode()).digest()
        )
        db.session.add(user)
        for product_idx in range(1, 3):
            product = Product(
                name=f"user-{user_idx}-product-{product_idx}",
                url=f"http://localhost/product-{product_idx}",
                active=True,
            )
            db.session.add(product)

    db.session.commit()


def _get_product_dict(user_idx: int=1, product_idx: int=3):
    """Creates a valid product dict object to be used for PUT and POST tests."""
    return {
        "user_id": user_idx,
        "name": f"user-{user_idx}-product-{product_idx}",
        "url": f"http://localhost/product-{product_idx}",
        "active": True,
    }

class TestProductCollection:
    """Group of all product collection related tests"""

    RESOURCE_URL = "/api/products/"

    def test_get(self, client):
        """Test that the GET route responds with correct data"""
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body) == 4
        for item in body:
            assert "name" in item
            assert "url" in item

    def test_post_valid_request(self, client):
        """Create new product"""
        valid = _get_product_dict()
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201

    def test_wrong_mediatype(self, client):
        """Only JSON mediatype is allowed"""
        valid = _get_product_dict()
        resp = client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

    def test_post_missing_field(self, client):
        """URL is required"""
        valid = _get_product_dict()
        valid.pop("url")
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_post_name_conflict(self, client):
        """Name conflict is ok"""
        valid = _get_product_dict(product_idx=2)
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201

class TestProductItem:
    """Group of all product item related tests"""
    RESOURCE_URL = "/api/products/1/"
    INVALID_RESOURCE_URL = "/api/products/5/"

    def test_get(self, client):
        """Test that the GET route responds with correct data"""
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)

        assert "name" in body
        assert "url" in body

    def test_get_not_found(self, client):
        """Get product which does not exist"""
        resp = client.get(self.INVALID_RESOURCE_URL)
        assert resp.status_code == 404

    def test_put_valid_request(self, client):
        """Modify existing product"""
        valid = _get_product_dict()
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204

    def test_wrong_mediatype(self, client):
        """Only JSON mediatype is allowed"""
        valid = _get_product_dict()
        resp = client.put(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

    def test_put_missing_field(self, client):
        """URL is required"""
        valid = _get_product_dict()
        valid.pop("url")
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_put_name_conflict(self, client):
        """Name conflict is ok"""
        valid = _get_product_dict(product_idx=2)
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204