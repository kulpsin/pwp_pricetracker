#/usr/bin/env python3
"""
Collection of Database testing scripts using pytest

Used
https://github.com/UniOulu-Ubicomp-Programming-Courses/pwp-sensorhub-example/blob/ex2-project-layout/tests/test_resource.py
as template for this file.
"""

import os
import json
import tempfile

import pytest

from flask.testing import FlaskClient
from werkzeug.datastructures import Headers

from pricetracker.models import Product, Price, User, ApiKey
from pricetracker.db import db
from pricetracker import create_app


TEST_KEYS = [
    "verysafetestkey1",
    "verysafetestkey2",
    "verysafetestkey3",
]


# https://stackoverflow.com/questions/16416001/set-http-headers-for-all-requests-in-a-flask-test
class AuthHeaderClient(FlaskClient):
    """Placeholder for authentication testing"""
    def open(self, *args, **kwargs):
        headers = Headers({
            'X-Api-Key': TEST_KEYS[0]
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
    app.test_client_class = AuthHeaderClient
    yield app.test_client()

    os.close(db_fd)
    os.unlink(db_fname)

    ctx.pop()


def _populate_db():
    """Populate the DB with two users and two products for each"""
    for user_idx in range(2):
        user = User(
            email=f"test-resource-user-{user_idx}@localhost",
        )
        db.session.add(user)

        # Generate unique key for a user
        key = ApiKey(key=TEST_KEYS[user_idx])
        key.user = user
        db.session.add(key)

        for product_idx in range(2):
            product = Product(
                name=f"user-{user_idx}-product-{product_idx}",
                url=f"http://localhost/product-{product_idx}",
                active=True,
            )
            product.user = user
            db.session.add(product)


    db.session.commit()


def _get_product_dict(user_idx: int=1, product_idx: int=0):
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

    def test_post_product_as_other(self, client):
        """X-Api-Key and user_id do not match"""
        valid = _get_product_dict(user_idx=2)
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 403


class TestProductItem:
    """Group of all product item related tests"""
    RESOURCE_URL = "/api/products/1/"
    INVALID_RESOURCE_URL = "/api/products/34/"

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
        valid = _get_product_dict(product_idx=1)
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204

    def test_put_product_owned_by_other(self, client):
        """Name conflict is ok"""
        user_id = 1
        # Get a product from different user:
        resp = client.get(TestProductCollection.RESOURCE_URL)
        body = resp.json
        product = None
        for item in body:
            if item['user_id'] != user_id:
                product = item
                break
        assert product is not None
        # Construct url:
        resource_url = f"{TestProductCollection.RESOURCE_URL}{product['id']}/"

        # Get valid product dict with user's id
        valid = _get_product_dict(user_idx=user_id)
        resp = client.put(resource_url, json=valid)
        assert resp.status_code == 403
