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
    product = db.Column(db.String(128), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    notes = db.Column(db.String(512), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    user = db.relationship("User", back_populates="products")
    prices = db.relationship("Price", back_populates="product")


class Price(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"))
    price = db.Column(db.Float, nullable=False)
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
    products = [
        Product(product="PS5", url="https://www.gigantti.fi/product/gaming/pelikonsolit-ja-tarvikkeet/playstation/playstation-konsolit/playstation-5-slim-standard-edition-e-runko-1-tb/988057iuoe", notes="Standard edition"),
        Product(product="Ikea desk", url="https://www.ikea.com/fi/fi/p/anfallare-alex-tyoepoeytae-bambu-mustanruskea-s89417745/?recently_viewed=b"),
        Product(product="Broken product", url="https://www.outdated_url.com", notes="This is a product with a non-functional url.", active=False),
    ]
    for product in products:
        count = 100
        interval = datetime.timedelta(days=1)
        now = datetime.datetime.now() - count * interval
        for i in range(count):
            price= Price(
                price=round(random.random() * 100, 2),
                timestamp=now,
            )
            now += interval
            product.prices.append(price)

        u.products.append(product)

    db.session.add(u)
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
