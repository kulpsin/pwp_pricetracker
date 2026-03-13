#!/usr/bin/env pyhton3
"""
Implements authentication decorators

This code has been used:
https://lovelace.oulu.fi/ohjelmoitava-web/ohjelmoitava-web/implementing-rest-apis-with-flask/#api-authentication
"""

import logging
from functools import wraps

from flask import request
from werkzeug.exceptions import Forbidden, Unauthorized

from .models import ApiKey, User

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def require(admin=False, worker=False, owner=True):
    """Test that the X-Api-Key header is set and correct"""
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):

            if "X-Api-Key" not in request.headers:
                logger.info("Request without X-Api-Key: %s", request.endpoint)
                raise Unauthorized
            key_hash = ApiKey.key_hash(request.headers.get("X-Api-Key").strip())
            db_key = ApiKey.query.where(ApiKey.key == key_hash).first()

            if db_key is None:
                logger.info("Request with invalid X-Api-Key: %s", request.endpoint)
                raise Forbidden

            current_user = db_key.user
            if admin:
                # Admin key is required, skip rest of the rules if success
                if not db_key.admin:
                    logger.info("Admin endpoint requested without admin X-Api-Key: %s",
                                request.endpoint)
                    raise Forbidden
                return func(*args, **kwargs)
            # Worker suppport will be added during worker development
            if worker:   # pragma: no cover
                # Worker key is required, skip rest of the rules if success
                if not db_key.worker:
                    logger.info("Worker endpoint requested without worker X-Api-Key: %s",
                                request.endpoint)
                    raise Forbidden
                return func(*args, **kwargs)

            if owner:
                # Ownership of the resource is required
                def get_owner(item):
                    """Attempts to get owner of the item"""
                    if item is None:
                        return None
                    if hasattr(item, 'user'):
                        return item.user
                    if isinstance(item, User):
                        return item
                    return None

                # Lets go through *args, like ProductItem
                for item in args:
                    _owner = get_owner(item)
                    if _owner and current_user != _owner:
                        logger.info("Wrong user (arg) X-Api-Key: %s", request.endpoint)
                        raise Forbidden

                # Lets go through *kwargs, like (Product)
                # This loop will detect direct ownerships and check if owned by the requesting user
                for _, item in kwargs.items():
                    _owner = get_owner(item)
                    if _owner and current_user != _owner:
                        logger.info("Wrong user (kwarg) X-Api-Key: %s", request.endpoint)
                        raise Forbidden
            return func(*args, **kwargs)
        return wrapped
    return decorator
