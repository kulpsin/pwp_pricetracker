""" This module defines the resource module for products. """

import re

from flask import Response, request, url_for
from flask_restful import Resource
from jsonschema import ValidationError, validate
from werkzeug.exceptions import BadRequest, Conflict, NotFound
from werkzeug.routing import BaseConverter
from sqlalchemy.exc import IntegrityError

from .. import models
from ..db import db
from .. import auth

def slugify(text):
    ''' This helper function makes text URL-friendly
    by removing special characters '''
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text

class ProductCollection(Resource):

    """
    API Resource for managing products.
    Provides methods to create new products and list all products.
    """

    @auth.require()
    def post(self):

        """Create a new product."""

        if not request.is_json:
            return "Request content type must be JSON", 415

        try:
            validate(request.json, models.Product.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e)) from e

        hruid = models.Product.gen_hruid(request.json['name'])

        product = models.Product()
        product.deserialize(request.json)
        product.hruid = hruid
        key_hash = models.ApiKey.key_hash(request.headers.get("X-Api-Key").strip())
        product.user = models.User.query.join(models.ApiKey).filter(
            models.ApiKey.key == key_hash
        ).first()

        db.session.add(product)

        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise Conflict(description="Product already exists or violates constraints.") from e

        return Response(
            status=201,
            headers={
                "Location": url_for('api.productitem', product=product),
            },
        )

    def get(self):

        """Retrieve and return a list of all products."""

        response_data = []
        products = models.Product.query.all()
        for product in products:
            response_data.append(product.serialize())
        return response_data, 200

class ProductItem(Resource):

    """
    API Resource for a single product instance.
    Provides methods to retrieve, update, or delete a specific product.
    """

    def get(self, product):

        """Retrieve a specific product."""

        return product.serialize()

    @auth.require()
    def put(self, product):

        """Update an existing product."""

        if not request.json:
            return "Request content type must be JSON", 415

        try:
            validate(request.json, models.Product.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e)) from e
        product.deserialize(request.json)
        try:
            db.session.add(product)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise Conflict(description="Oops...Something went wrong.") from e

        return Response(status=204)

    @auth.require()
    def delete(self, product):

        """Delete a specific product."""

        db.session.delete(product)
        db.session.commit()

        return Response(status=204)


class ProductConverter(BaseConverter):
    def to_python(self, value):
        db_product = models.Product.query.filter_by(hruid=value).first()
        if db_product is None:
            raise NotFound
        return db_product

    def to_url(self, value):
        return value.hruid
