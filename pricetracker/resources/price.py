
# This code has the same structure as the Sensorhub example provided in the course material
# (https://github.com/UniOulu-Ubicomp-Programming-Courses/pwp-sensorhub-example/blob/ex2-05-validation/app.py)

from datetime import datetime

from flask import Response, request, url_for
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
        """Get the entire price history associated with a product sorted by timestamp
        ---
        security: []
        parameters:
          - name: product
            in: path
            required: true
        responses:
          200:
            description: A list of prices for the product
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Price'
                example:
                  - value: 0.72
                    timestamp: "2020-03-14T15:32:52"
                  - value: 4.9
                    timestamp: "2020-03-14T15:32:52"
        """
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
        
        return Response(
            status=201,
            headers={
                "Location": url_for('api.priceitem', product=product, price=price),
            },
        )

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
        # Extract product hruid from the request path
        # URL pattern: /api/products/<product_hruid>/prices/<timestamp>/
        product_hruid = request.path.split("/products/")[1].split("/prices/")[0]
        db_price = models.Price.query.join(models.Product).filter(
            models.Product.hruid == product_hruid,
            models.Price.timestamp == timestamp
        ).first()
        if db_price is None:
            raise NotFound
        return db_price

    def to_url(self, value):
        return value.timestamp.isoformat()
