#/usr/bin/env python3
"""
This file defines all the /api-endpoints using
Flask Blueprints.
"""
from flask import Blueprint, jsonify
from flask_restful import Api
from .resources.product import ProductCollection, ProductItem

api_bp =  Blueprint("api", __name__)
api = Api(api_bp)

api.add_resource(ProductCollection, "/products/")
api.add_resource(ProductItem, "/products/<product:product>/")

@api_bp.route('/hello')
def hello():
    """
    Placeholder test route. Safe to be removed real endpoints
    have been added, or replace with /health endpoint.
    """
    return jsonify({"message":"Hello world"})
