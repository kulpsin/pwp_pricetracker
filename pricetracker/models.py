#!/usr/bin/env python3
"""
Contains definations for all the database data models.
"""


from sqlalchemy.engine import Engine
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

    def serialize(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "url": self.url,
            "notes": self.notes,
            "active": self.active
        }
    
    
    def deserialize(self, doc):
        # Required / Core fields
        if "name" in doc:
            self.name = doc["name"]
        if "url" in doc:
            self.url = doc["url"]
        if "user_id" in doc:
            self.user_id = doc["user_id"]
        
        # Optional fields
        if "notes" in doc:
            self.notes = doc["notes"]
        if "active" in doc:
            # Ensuring we store a boolean
            self.active = bool(doc["active"])
    
    @staticmethod
    def json_schema():
        schema = {
            "type": "object",
            "required": ["name", "url", "user_id"]
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
    password = db.Column(db.String(128), nullable=False)

    products = db.relationship("Product", back_populates="user")
