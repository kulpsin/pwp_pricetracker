#/usr/bin/env python3
"""
This file defines all the /api-endpoints using
Flask Blueprints.
"""
from flask import Blueprint, jsonify
from flask_restful import Api
from .resources.user import UserCollection, UserItem, UserProducts
from .resources.product import ProductCollection, ProductItem
from .resources.price import PriceCollection, PriceItem

api_bp =  Blueprint("api", __name__)
api = Api(api_bp)

api.add_resource(UserCollection, "/users/")
api.add_resource(UserItem, "/users/<user:user>/")
api.add_resource(UserProducts, "/users/<user:user>/products/")
api.add_resource(ProductCollection, "/products/")
api.add_resource(ProductItem, "/products/<product:product>/")
api.add_resource(PriceCollection, "/products/<product:product>/prices/")
api.add_resource(PriceItem, "/products/<product:product>/prices/<price:price>/")

@api_bp.route('/hello')
def hello():  # pragma: no cover
    """
    Placeholder test route. Safe to be removed real endpoints
    have been added, or replace with /health endpoint.
    """
    return jsonify({"message":"Hello world"})
