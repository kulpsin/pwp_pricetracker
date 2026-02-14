#/usr/bin/env python3
"""
This file defines all the /api-endpoints using
Flask Blueprints.
"""
from flask import Blueprint, jsonify

api_bp =  Blueprint("api", __name__)


@api_bp.route('/hello')
def hello():
    """
    Placeholder test route. Safe to be removed real endpoints
    have been added, or replace with /health endpoint.
    """
    return jsonify({"message":"Hello world"})
