""" This module defines the resource module for products. """

from flask import Response, request
from flask_restful import Resource
from jsonschema import ValidationError, validate
from werkzeug.exceptions import BadRequest, Conflict
from sqlalchemy.exc import IntegrityError


from .. import models
from ..db import db

class ProductCollection(Resource):

    """
    API Resource for managing products.
    Provides methods to create new products and list all products.
    """

    def post(self):

        """Create a new product."""

        if not request.is_json:
            return "Request content type must be JSON", 415

        try:
            validate(request.json, models.Product.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        product = models.Product()
        product.deserialize(request.json)

        try:
            db.session.add(product)
            db.session.commit()
        except IntegrityError:
            raise Conflict(description=f"Product with id '{request.json['id']}' already exists.")

        return Response(status=201)

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

    def put(self, product):

        """Update an existing product."""

        if not request.json:
            return "Request content type must be JSON", 415

        try:
            validate(request.json, models.Product.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        product.deserialize(request.json)
        try:
            db.session.add(product)
            db.session.commit()
        except IntegrityError:
            raise Conflict(description=f"Product with id '{request.json['id']}' already exists.")

        return Response(status=204)

    def delete(self, product):

        """Delete a specific product."""

        db.session.delete(product)
        db.session.commit()

        return Response(status=204)
