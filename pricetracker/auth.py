#!/usr/bin/env pyhton3
"""
Implements authentication decorators
"""

from .models import ApiKey

# Original source:
# https://lovelace.oulu.fi/ohjelmoitava-web/ohjelmoitava-web/implementing-rest-apis-with-flask/#implementing-api-key-authentication
def require_admin(func):
    def wrapper(*args, **kwargs):
        apikey = ApiKey.query.where(key=request.headers.get("X-Api-Key").strip()).first()
        if apikey.admin:
            return func(*args, **kwargs)
        raise Forbidden
    return wrapper


