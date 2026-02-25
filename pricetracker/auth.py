#!/usr/bin/env pyhton3
"""
Implements authentication decorators

This code has been used:
https://lovelace.oulu.fi/ohjelmoitava-web/ohjelmoitava-web/implementing-rest-apis-with-flask/#api-authentication
"""

from flask import request
from werkzeug.exceptions import Forbidden, Unauthorized

from .models import ApiKey


def require(user=None, resource=None, admin=False):
    def decorator(func):
        def wrapped(*args, **kwargs):

            if "X-Api-Key" not in request.headers:
                raise Unauthorized
            key_hash = ApiKey.key_hash(request.headers.get("X-Api-Key").strip())
            db_key = ApiKey.query.where(ApiKey.key == key_hash).first()

            if admin:
                # Admin key is required
                if not db_key.admin:
                    raise Forbidden
                #return func(*args, **kwargs)  # Skip other rules?

            # If the request data contains user_id, we need to check that:
            if 'user_id' in request.json:
                if request.json['user_id'] != db_key.user.id:
                    raise Forbidden
            # If specific user is given, check that
            if user is not None:
                # Specific user is needed
                if db_key.user != user:
                    raise Forbidden
            # Lets go through *args, like ProductItem
            for item in args:
                try:
                    _user = item.user
                except AttributeError:  # pylint pls, this is ok
                    # item does not have user-attribute, that is expected
                    pass
                else:
                    if db_key.user != _user:
                        raise Forbidden
            # Lets go through *kwargs, like (Product)
            # This loop will detect direct ownerships and check if owned by the requesting user
            for _, item in kwargs.items():
                try:
                    _user = item.user
                except AttributeError:
                    # item does not have user-attribute, that is expected
                    pass
                else:
                    if db_key.user != _user:
                        raise Forbidden

            if resource is not None:
                # Ownership of the resource is needed
                if db_key.user != resource.user:
                    raise Forbidden
            return func(*args, **kwargs)
        return wrapped
    return decorator

