from datetime import datetime
from flask import Response, request
from flask_restful import Resource
from jsonschema import ValidationError, validate
from werkzeug.exceptions import BadRequest, Conflict, NotFound
from werkzeug.routing import BaseConverter
from sqlalchemy.exc import IntegrityError

from .. import models
from ..db import db
from .. import auth, cache

class PriceCollection(Resource):
    @cache.cached(timeout=60)
    def get(self, product):
        """Get the entire price history associated with a product sorted by timestamp"""
        history = []
        for price in product.prices:
            history.append({
                "timestamp": price.timestamp.isoformat(),
                "price": price.value
            })
        history.sort(key=lambda x: x["timestamp"])
        return history, 200

    @auth.require(owner=False)
    def post(self, product):
        """Post a new snapshot to an existing price history"""
        if not request.is_json:
            return "Request content type must be JSON", 415
        
        try:
            validate(request.json, models.Price.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))
        
        price = models.Price()
        price.deserialize(request.json)
        price.product_id = product.id

        try:
            db.session.add(price)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise Conflict(description="Price entry error.")
        
        return Response(status=201)

class PriceItem(Resource):
    @cache.cached(timeout=3600)
    def get(self, product, price):
        """Get a particular price from the history at a specific timestamp"""

        return price.serialize()

    @auth.require()
    def delete(self, product, price):
        """Delete an existing snapshot from the price history"""

        db.session.delete(price)
        db.session.commit()
        return Response(status=204)
    

class PriceConverter(BaseConverter):
    def to_python(self, value):
        try:
            timestamp = datetime.fromisoformat(value)
        except ValueError as e:
            raise NotFound("Invalid timestamp format") from e
        
        db_price = models.Price.query.filter_by(timestamp=timestamp).first()
        if db_price is None:
            raise NotFound
        return db_price

    def to_url(self, value):
        return str(value.timestamp)