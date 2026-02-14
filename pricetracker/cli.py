#!/usr/bin/env python3
"""
CLI tools for Price Tracker
"""

import hashlib
import click
from flask.cli import with_appcontext
from sqlalchemy import exc

from .db import db
from .models import User, Product, Price


# https://lovelace.oulu.fi/ohjelmoitava-web/ohjelmoitava-web/flask-api-project-layout/
@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """Creates the database tables"""
    db.create_all()


@click.command("testdel")
@with_appcontext
def remove_test_data() -> None:
    """Removes the user 'test-user-1@localhost'"""
    User.query.where(User.email == 'test-user-1@localhost').delete()
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
    print("DONE")


@click.command("testgen")
@with_appcontext
def generate_test_data() -> None:
    """Generates testdata under email 'test-user-1@localhost'"""
    # pylint: disable=C0415 (wrong-import-position)
    import datetime
    # pylint: disable=C0415 (wrong-import-position)
    import random

    u = User(
        email="test-user-1@localhost",
        password=hashlib.sha256("password".encode()).digest()
    )
    db.session.add(u)

    # fun bug: the default value of "True" for the "active" parameter is only set when the product
    #          is actually inserted into the database, so we have to explicitly set it here if we
    #          want to test for product.active in the code
    products = [
        Product(
            name="PS5",
            url=(
                "https://www.gigantti.fi/product/gaming/pelikonsolit-ja-tarvikkeet/playstation/"
                "playstation-konsolit/playstation-5-slim-standard-edition-e-runko-1-tb/988057iuoe"),
            notes="Standard edition",
            active=True
        ),
        Product(
            name="Ikea desk",
            url=("https://www.ikea.com/fi/fi/p/anfallare-alex-tyoepoeytae-bambu-mustanruskea-"
                 "s89417745/?recently_viewed=b"),
            active=True
        ),
        Product(
            name="Broken product",
            url="https://www.outdated_url.com",
            notes="This is a product with a non-functional url.",
            active=False
        ),
    ]

    for product in products:
        u.products.append(product)
        if product.active:
            count = 100
            interval = datetime.timedelta(days=1)
            now = datetime.datetime.now() - count * interval
            for _ in range(count):
                price= Price(
                    value=round(random.random() * 100, 2),
                    timestamp=now,
                )
                now += interval
                product.prices.append(price)
    try:
        db.session.commit()
    except exc.IntegrityError:
        print("Already exists")
        db.session.rollback()
    else:
        print("Created successfully")
