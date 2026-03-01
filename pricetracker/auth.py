#!/usr/bin/env pyhton3
"""
Implements authentication decorators

This code has been used:
https://lovelace.oulu.fi/ohjelmoitava-web/ohjelmoitava-web/implementing-rest-apis-with-flask/#api-authentication
"""

import logging

from flask import request
from werkzeug.exceptions import Forbidden, Unauthorized

from .models import ApiKey

logger = logging.getLogger(__name__)


def require(user=None, resource=None, admin=False, worker=False):
    def decorator(func):
        def wrapped(*args, **kwargs):

            if "X-Api-Key" not in request.headers:
                logger.info("Request without X-Api-Key: %s", request.endpoint)
                raise Unauthorized
            key_hash = ApiKey.key_hash(request.headers.get("X-Api-Key").strip())
            db_key = ApiKey.query.where(ApiKey.key == key_hash).first()
            if db_key is None:
                logger.info("Request with invalid X-Api-Key: %s", request.endpoint)
                raise Forbidden

            if admin:
                # Admin key is required, skip rest of the rules if success
                if not db_key.admin:
                    logger.info("Admin endpoint requested without admin X-Api-Key: %s",
                                request.endpoint)
                    raise Forbidden
                return func(*args, **kwargs)
            if worker:
                # Worker key is required, skip rest of the rules if success
                if not db_key.worker:
                    logger.info("Worker endpoint requested without worker X-Api-Key: %s",
                                request.endpoint)
                    raise Forbidden
                return func(*args, **kwargs)

            # If specific user is given, check that
            if user is not None:
                # Specific user is needed
                if db_key.user != user:
                    logger.info("Wrong user X-Api-Key: %s", request.endpoint)
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
                        logger.info("Wrong user (arg) X-Api-Key: %s", request.endpoint)
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
                        logger.info("Wrong user (kwarg) X-Api-Key: %s", request.endpoint)
                        raise Forbidden

            if resource is not None:
                # Ownership of the resource is needed
                if db_key.user != resource.user:
                    logger.info("Wrong user (resource) X-Api-Key: %s", request.endpoint)
                    raise Forbidden
            return func(*args, **kwargs)
        return wrapped
    return decorator
