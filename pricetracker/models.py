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
