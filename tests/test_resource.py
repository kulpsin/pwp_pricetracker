#/usr/bin/env python3
"""
Collection of Database testing scripts using pytest

Used
https://github.com/UniOulu-Ubicomp-Programming-Courses/pwp-sensorhub-example/blob/ex2-project-layout/tests/test_resource.py
as template for this file.
"""

import json

import pytest


def _get_product_dict(user_idx: int=1, product_idx: int=0):
    """Creates a valid product dict object to be used for PUT and POST tests."""
    return {
        "name": f"user-{user_idx}-product",
        "url": f"http://localhost/product-{product_idx}",
    }

def _get_user_dict(email: str="test-user-1@localhost"):
    """Creates a valid user dict object to be used for POST request."""
    return {
        "email": email,
    }

@pytest.fixture(name="user")
def fixture_user(client):
    """Creates new user"""
    email = "new-test-user-1@localhost"
    resp = client.post("/api/users/", json={"email": email})
    assert resp.status_code == 201
    key = resp.headers.get('X-Api-Key')
    location = resp.headers.get('Location')
    headers = {'X-Api-Key': key}

    yield {
        "email": email,
        "key": key,
        "location": location,
        "client": client,
        "headers": headers
    }

    # Clean up if needed: user might already be gone at this point
    try:
        client.delete(location, headers=headers)
    except Exception:
        pass


@pytest.fixture(name="product")
def fixture_product(user):
    """Creates new product"""
    req = _get_product_dict()
    headers = {'X-Api-Key': user['key']}
    resp = user['client'].post("/api/products/", json=req, headers=headers)
    assert resp.status_code == 201
    location = resp.headers.get('Location')

    yield {
        "req": req,
        "location": location,
        "user": user,
        "client": user['client'],
        "headers": headers,
    }

    # Clean up if needed: user might already be gone at this point
    try:
        user['client'].delete(location, headers=headers)
    except Exception:
        pass


class TestProductCollection:
    """Group of all product collection related tests"""

    RESOURCE_URL = "/api/products/"

    def test_get(self, auth_client):
        """Test that the GET route responds with correct data"""
        resp = auth_client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body) == 4
        for item in body:
            assert "name" in item
            assert "url" in item

    def test_post_valid_request(self, auth_client, db_data):
        """Create new product"""
        user = db_data["users"][0]
        valid = _get_product_dict(user_idx=user.id)
        valid_key = db_data["keys"][0]

        resp = auth_client.post(self.RESOURCE_URL, json=valid, headers={"X-Api-Key": valid_key})
        assert resp.status_code == 201

    def test_wrong_mediatype(self, auth_client):
        """Only JSON mediatype is allowed"""
        valid = _get_product_dict()
        resp = auth_client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

    def test_post_missing_field(self, auth_client):
        """URL is required"""
        valid = _get_product_dict()
        valid.pop("url")
        resp = auth_client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_post_name_conflict(self, auth_client):
        """Name conflict is ok"""
        valid = _get_product_dict(product_idx=2)
        resp = auth_client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201

    def test_post_product_as_other(self, auth_client):
        """X-Api-Key and user_id do not match"""
        valid = _get_product_dict(user_idx=2)
        resp = auth_client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 403


class TestProductItem:
    """Group of all product item related tests"""

    def test_get(self, auth_client, product):
        """Test that the GET route responds with correct data"""
        resp = auth_client.get(product['location'])
        assert resp.status_code == 200
        body = json.loads(resp.data)

        assert "name" in body
        assert "url" in body

    def test_get_not_found(self, auth_client, product):
        """Get product which does not exist"""
        invalid_url = product['location'] + 'invalid'
        resp = auth_client.get(invalid_url)
        assert resp.status_code == 404

    def test_put_valid_request(self, product):
        """Modify existing product"""
        resp = product['client'].get(product['location'], headers=product['headers'])
        prod = resp.json
        prod['name'] = "Changed-product-name"
        resp = product['client'].put(product['location'], json=prod, headers=product['headers'])
        assert resp.status_code == 204

    def test_wrong_mediatype(self,  product):
        """Only JSON mediatype is allowed"""
        resp = product['client'].get(product['location'], headers=product['headers'])
        prod = resp.json
        prod['name'] = "Changed-product-name"
        resp = product['client'].put(
            product['location'],
            data=json.dumps(prod),
            headers=product['headers']
        )
        assert resp.status_code == 415

    def test_put_missing_field(self, product):
        """URL is required"""
        resp = product['client'].get(product['location'], headers=product['headers'])
        prod = resp.json
        prod.pop("url")
        resp = product['client'].put(
            product['location'],
            json=prod,
            headers=product['headers']
        )
        assert resp.status_code == 400

    def test_put_product_owned_by_other(self, auth_client, product):
        """Name conflict is ok"""
        valid = _get_product_dict()
        resp = auth_client.put(product['location'], json=valid)
        assert resp.status_code == 403


class TestUserCollection:
    RESOURCE_URL = "/api/users/"

    def test_get(self, auth_client):
        """Who has access to user-listing? Admin?"""
        resp = auth_client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        for item in body:
            assert "email" in item

    def test_post_valid_request(self, client):
        """Create new product"""
        valid = _get_user_dict()
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201

    def test_post_wrong_mediatype(self, client):
        """Only JSON mediatype is allowed"""
        valid = _get_user_dict()
        resp = client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

    def test_post_empty(self, client):
        """email is required"""
        resp = client.post(self.RESOURCE_URL, json=dict())
        # Empty dict gets removed I suppose, hence 415
        assert resp.status_code in (400, 415)

    def test_post_name_conflict(self, client):
        """User account already exist for the email"""
        valid = _get_user_dict()
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409  # Conflict


class TestUserItem:
    def test_get(self, client, user):
        resp = client.get(user['location'], headers={"X-Api-Key": user['key']})
        body = resp.json
        assert body["email"] == user['email']
        assert body['uuid'] in user['location']

    def test_change_own_email(self, client, user):
        valid = _get_user_dict("another-mail@localhost")
        resp = client.put(user['location'], json=valid, headers={"X-Api-Key": user['key']})
        assert resp.status_code == 204

    def test_delete_user(self, client, user):
        resp = client.delete(user['location'], headers={"X-Api-Key": user['key']})
        assert resp.status_code == 204

    def test_delete_user(self, auth_client, user):
        resp = auth_client.delete(user['location'])
        assert resp.status_code == 403

    """
    def test_change_other_email(self, auth_client, user):
        valid = _get_user_dict("another-mail@localhost")
        #valid_key = db_data["keys"][0]
        url = f"{self.RESOURCE_URL}{user.id}/"
        resp = auth_client.put(url, json=valid, headers={"X-Api-Key": valid_key})
        assert resp.status_code == 204"""
