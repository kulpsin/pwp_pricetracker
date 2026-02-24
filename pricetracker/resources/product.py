import json

from flask import Flask, Response, request
from flask_restful import Api, Resource
from jsonschema import ValidationError, validate, draft7_format_checker
from werkzeug.exceptions import BadRequest, Conflict, NotFound, UnsupportedMediaType
from werkzeug.routing import BaseConverter
from sqlalchemy.exc import IntegrityError


from .. import models
from .. import db


class ProductCollection(Resource):

    def post(self):
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
            raise Conflict(
                description="Product with id '{id}' already exists.".format(
                    **request.json
                )
            )

        return Response(status=201)

    def get(self):
        response_data = []
        products = models.Product.query.all()
        for product in products:
            response_data.append(product.serialize())
        return response_data, 200
    
class ProductItem(Resource):
    def get(self, product):
        return product.serialize()
    
    def put(self, product):
        if not request.json:
            raise UnsupportedMediaType

        try:
            validate(request.json, models.Product.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        product.deserialize(request.json)
        try:
            db.session.add(product)
            db.session.commit()
        except IntegrityError:
            raise Conflict(
                description="Product with id '{id}' already exists.".format(
                    **request.json
                )
            )

        return Response(status=204)

    def delete(self, product):
        db.session.delete(product)
        db.session.commit()

        return Response(status=204)