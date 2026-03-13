#!/usr/bin/env python3
"""
CLI tools for Price Tracker
"""

import sys
import datetime
import random
import secrets

import click
from flask.cli import with_appcontext
from sqlalchemy import exc

from .db import db
from .models import User, Product, Price, ApiKey

sys.tracebacklimit = 0

@click.command("add-admin-user")
@click.argument("email")
@with_appcontext
def add_admin_user(email: str) -> None:
    """Creates an admin user"""
    u = User(
        email=email,
    )
    db.session.add(u)
    key = secrets.token_urlsafe(32)
    a = ApiKey(
        key=key,
        admin=True,
        user=u,
    )
    db.session.add(a)
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
        raise ValueError(f"User with email '{email}' already exists") from None
    print("Admin user has successfully been created, please store following ApiKey securely, "
          "it cannot be recovered.")
    print(key)


@click.command("add-worker-key")
@click.argument("email")
@with_appcontext
def add_worker_key(email: str) -> None:
    """Creates a new worker-apikey for the user"""
    u = User.query.filter_by(
        email=email,
    ).first()
    if not u:
        raise ValueError(f"User with email '{email}' does not exist")
    key = secrets.token_urlsafe(32)
    a = ApiKey(
        key=key,
        worker=True,
        user=u,
    )
    db.session.add(a)

    db.session.commit()
    print(f"A worker key has been created for user '{email}'. Please store the ApiKey securely, "
          "it cannot be recovered.")
    print(key)


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
    db.session.commit()
    print("Testdata has been removed")


@click.command("testgen")
@with_appcontext
def generate_test_data() -> None:
    """Generates testdata under email 'test-user-1@localhost'"""

    u = User(
        email="test-user-1@localhost",
    )
    db.session.add(u)
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
        raise RuntimeError("Testdata has already been generated") from None

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
            active=True,
            hruid=Product.gen_hruid("PS5"),
        ),
        Product(
            name="Ikea desk",
            url=("https://www.ikea.com/fi/fi/p/anfallare-alex-tyoepoeytae-bambu-mustanruskea-"
                 "s89417745/?recently_viewed=b"),
            active=True,
            hruid=Product.gen_hruid("Ikea desk"),
        ),
        Product(
            name="Broken product",
            url="https://www.outdated_url.com",
            notes="This is a product with a non-functional url.",
            active=False,
            hruid=Product.gen_hruid("Broken product"),
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
    except exc.IntegrityError:  # pragma: no cover
        # This should never happen
        print("Already exists")
        db.session.rollback()
        raise RuntimeError(
            "Testuser has been created but failed to generate product-data."
        ) from None
    print("Created successfully")
