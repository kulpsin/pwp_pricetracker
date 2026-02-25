#!/usr/bin/env python3
"""
Contains definations for all the database data models.
"""

import os
import hashlib

from sqlalchemy.engine import Engine
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import event

from . import utils
from .db import db

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):  # pylint: disable=W0613 (unused-argument)
    """Enables Foreign Key support"""
    utils.set_sqlite_pragma(dbapi_connection)


class Product(db.Model):
    """Product model"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    name = db.Column(db.String(128), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    notes = db.Column(db.String(512), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    user = db.relationship("User", back_populates="products")
    prices = db.relationship("Price", back_populates="product")

    def serialize(self) -> dict:

        """Convert the object into a serializable dictionary."""

        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "url": self.url,
            "notes": self.notes,
            "active": self.active
        }

    def deserialize(self, doc: dict) -> None:

        """Update object attributes from a dictionary of values."""

        # Required fields
        if "user_id" in doc:
            self.user_id = int(doc["user_id"]) # Ensure integer
        if "name" in doc:
            self.name = doc["name"]
        if "url" in doc:
            self.url = doc["url"]

        # Optional fields
        if "notes" in doc:
            self.notes = doc["notes"]
        if "active" in doc:
            self.active = bool(doc["active"]) # Ensure bool

    @staticmethod
    def json_schema() -> dict:

        """Return the JSON schema rules for this object's data."""

        # Required fields
        schema = {
            "type": "object",
            "required": ["user_id", "name", "url"]
        }


        props = schema["properties"] = {}

        props["name"] = {
        "type": "string",
        "minLength": 1,
        "maxLength": 128
        }

        props["url"] = {
            "type": "string",
            "format": "uri",
            "maxLength": 512
        }

        props["user_id"] = {
            "type": "integer"
        }

        props["notes"] = {
            "type": ["string", "null"],
            "maxLength": 512
        }

        props["active"] = {
            "type": "boolean"
        }

        return schema


class Price(db.Model):
    """Price model"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"))
    value = db.Column(db.Float, nullable=False)
    #TODO: support for different currencies? EUR,USD,...
    #      The currency could be converted on the fly and
    #      the value would be always stored as EUR?
    timestamp = db.Column(db.DateTime, nullable=False)

    product = db.relationship("Product", back_populates="prices")


class User(db.Model):
    """User model"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), nullable=False, unique=True)

    products = db.relationship("Product", back_populates="user")
    apikeys = db.relationship("ApiKey", back_populates="user")

    def serialize(self):
        return {
            "id" : self.id,
            "email" : self.email
        }
    
    def deserialize(self, doc):
        self.email = doc["email"]

    @staticmethod
    def json_schema():
        schema = {
            "type" : "object",
            "required": ["email", ]
        }
        props = schema["properties"] = {}
        props["email"] = {
            "type": "string",
            "maxLength": 128
        }

        return schema


# Source:
# https://lovelace.oulu.fi/ohjelmoitava-web/ohjelmoitava-web/implementing-rest-apis-with-flask/#implementing-api-key-authentication
class ApiKey(db.Model):
    """
    APiKey model

    User could technically have multiple apikeys at some point.

    """
    id = db.Column(db.Integer, primary_key=True)
    _key_hash = db.Column("key", db.String(32), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))  # NULL is ok
    admin =  db.Column(db.Boolean, default=False)
    worker =  db.Column(db.Boolean, default=False)
    allowed_to_post_prices = db.Column(db.Boolean, default=False)

    user = db.relationship("User", back_populates="apikeys")

    @hybrid_property
    def key(self) -> str:
        return self._key_hash

    @key.inplace.setter
    def _key_setter(self, key: str) -> None:
        """Generates salt for storing the key safely"""
        self._key_hash = self.key_hash(key)

    @staticmethod
    def key_hash(key: str) -> str:
        """Generate hash for a key"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            key.encode(),
            os.getenv('PEPPER', 'mintIsGood').encode(),
            102_074,
        )
