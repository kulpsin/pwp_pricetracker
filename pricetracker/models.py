#!/usr/bin/env python3

import click
import hashlib
from flask.cli import with_appcontext
from sqlalchemy.engine import Engine
from sqlalchemy import event, exc

from . import db

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    name = db.Column(db.String(128), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    notes = db.Column(db.String(512), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    user = db.relationship("User", back_populates="products")
    prices = db.relationship("Price", back_populates="product")


class Price(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"))
    value = db.Column(db.Float, nullable=False)
    #TODO: support for different currencies? EUR,USD,...
    #      The currency could be converted on the fly and
    #      the value would be always stored as EUR?
    timestamp = db.Column(db.DateTime, nullable=False)

    product = db.relationship("Product", back_populates="prices")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False)

    products = db.relationship("Product", back_populates="user")


@click.command("init-db")
@with_appcontext
def init_db_command():
    db.create_all()

@click.command("testgen")
@with_appcontext
def generate_test_data():
    import datetime
    import random

    u = User(
        email="test-user-1@localhost",
        password=hashlib.sha256("password".encode()).digest()
    )
    db.session.add(u)

    # fun bug: the default value of "True" for the "active" parameter is only set when the product is actually inserted into the database, so we have to explicitly set it here if we want to test for product.active in the code 
    products = [
        Product(name="PS5", url="https://www.gigantti.fi/product/gaming/pelikonsolit-ja-tarvikkeet/playstation/playstation-konsolit/playstation-5-slim-standard-edition-e-runko-1-tb/988057iuoe", notes="Standard edition", active=True),
        Product(name="Ikea desk", url="https://www.ikea.com/fi/fi/p/anfallare-alex-tyoepoeytae-bambu-mustanruskea-s89417745/?recently_viewed=b", active=True),
        Product(name="Broken product", url="https://www.outdated_url.com", notes="This is a product with a non-functional url.", active=False),
    ]

    for product in products:
        u.products.append(product)
        if product.active:
            count = 100
            interval = datetime.timedelta(days=1)
            now = datetime.datetime.now() - count * interval
            for i in range(count):
                price= Price(
                    value=round(random.random() * 100, 2),
                    timestamp=now,
                )
                now += interval
                product.prices.append(price)

    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
