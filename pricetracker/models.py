#!/usr/bin/env python3
"""
Contains definations for all the database data models.
"""

import os
import re
import hashlib
import datetime
import uuid

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
    hruid = db.Column(db.String(160), unique=True, index=True, nullable=False)

    user = db.relationship("User", back_populates="products")
    prices = db.relationship("Price", back_populates="product")
    update_jobs = db.relationship("PriceUpdateJob", back_populates="product")

    @staticmethod
    def gen_hruid(text: str) -> str:
        """Generate human readable unique identifier"""
        # Make text URL-friendly by removing special characters
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)
        text = re.sub(r"^-+|-+$", "", text)
        counter = 1
        while Product.query.filter_by(hruid=f"{text}-{counter}").first():
            counter += 1
        return f"{text}-{counter}"

    def serialize(self) -> dict:
        """Convert the object into a serializable dictionary."""
        doc = {
            "id": self.id,
            "hruid": self.hruid,
            "user": self.user and str(self.user.uuid),
            "name": self.name,
            "url": self.url,
            "active": self.active
        }
        if self.notes:
            doc["notes"] = self.notes
        return doc

    def deserialize(self, doc: dict) -> None:
        """Update object attributes from a dictionary of values."""
        # Required fields
        self.name = doc["name"]
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
            "required": ["name", "url"]
        }

        props = schema["properties"] = {}

        props["name"] = {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
        }

        props["hruid"] = {
            "type": "string",
            "minLength": 1,
            "maxLength": 160,
        }

        props["url"] = {
            "type": "string",
            "format": "uri",
            "maxLength": 512
        }

        props["user"] = {
            "type": "string",
            "format": "uuid",
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
    __table_args__ = (db.UniqueConstraint("product_id", "timestamp"),)
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"))
    value = db.Column(db.Float, nullable=False)
    #TODO: support for different currencies? EUR,USD,...
    #      The currency could be converted on the fly and
    #      the value would be always stored as EUR?
    timestamp = db.Column(db.DateTime, nullable=False)

    product = db.relationship("Product", back_populates="prices")

    def serialize(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "value": self.value,
            "timestamp": self.timestamp.isoformat()
        }

    def deserialize(self, doc):
        self.value = doc["value"]
        self.timestamp = datetime.datetime.fromisoformat(doc["timestamp"])

    @staticmethod
    def json_schema():
        schema = {
            "type": "object",
            "required": ["value", "timestamp"]
        }

        props = schema["properties"] = {}

        props["value"] = {
            "type": "number"
        }
        props["timestamp"] = {
            "type": "string",
            "format": "date-time"
        }
        return schema

class User(db.Model):
    """User model"""
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.Uuid, unique=True)
    email = db.Column(db.String(128), nullable=False, unique=True)

    products = db.relationship("Product", back_populates="user")
    apikeys = db.relationship("ApiKey", back_populates="user")

    def serialize(self):
        return {
            "uuid": self.uuid and str(self.uuid),
            "email": self.email
        }

    def deserialize(self, doc):
        self.email = doc["email"]
        if "uuid" in doc:
            self.uuid = uuid.UUID(doc["uuid"])

    @staticmethod
    def json_schema():
        schema = {
            "type" : "object",
            "required": ["email"]
        }
        props = schema["properties"] = {}
        props["email"] = {
            "type": "string",
            "maxLength": 128
        }
        props["uuid"] = {
            "type": "string",
            "format": "uuid",
        }

        return schema


@event.listens_for(User, "before_insert", propagate=True)
def generate_user_uuid(mapper, connection, target):  # pylint: disable=W0613 (unused-argument)
    """Auto-generate UUID for new users that don't have one."""
    if target.uuid is None:
        target.uuid = uuid.uuid4()


@event.listens_for(User, "load", propagate=True)
def load_user_uuid(instance, context):  # pylint: disable=W0613 (unused-argument)
    """Fill in NULL uuid for users loaded from DB without one."""
    if instance.uuid is None:
        instance.uuid = uuid.uuid4()


class PriceUpdateJob(db.Model):
    """Price update queue job model"""
    __table_args__ = (
        db.UniqueConstraint("product_id", "status",
                            name="uq_product_pending"),
    )
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.String(512), nullable=True)
    url = db.Column(db.String(512), nullable=True)
    price_value = db.Column(db.Float, nullable=True)

    product = db.relationship("Product", back_populates="update_jobs")

    def serialize(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "url": self.url,
            "price_value": self.price_value,
        }

    @staticmethod
    def json_schema():
        schema = {
            "type": "object",
        }
        props = schema["properties"] = {}
        props["status"] = {
            "type": "string",
            "enum": ["pending", "processing", "completed", "failed"],
        }
        props["error_message"] = {
            "type": ["string", "null"],
            "maxLength": 512,
        }
        props["price_value"] = {
            "type": ["number", "null"],
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
