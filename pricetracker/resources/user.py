# This code has the same structure as the Sensorhub example provided in the course material
# (https://github.com/UniOulu-Ubicomp-Programming-Courses/pwp-sensorhub-example/blob/ex2-05-validation/app.py)

import secrets
import uuid

from flask import Response, request, url_for
from flask_restful import Resource
from jsonschema import ValidationError, validate
from werkzeug.exceptions import BadRequest, Conflict, NotFound
from werkzeug.routing import BaseConverter
from sqlalchemy.exc import IntegrityError

from .. import models
from ..db import db
from .. import auth

class UserCollection(Resource):

    def post(self):
        if not request.json:
            return "Request content type must be JSON", 415
        try:
            validate(request.json, models.User.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        user = models.User()
        user.deserialize(request.json)
        user.uuid = uuid.uuid4()
        db.session.add(user)

        key = secrets.token_urlsafe(32)
        apikey = models.ApiKey(
            key=key,
            user=user,
        )
        db.session.add(apikey)

        try:
            db.session.commit()
        except IntegrityError:
            raise Conflict(description="Email already exists.")

        return Response(
            status=201,
            headers={
                "X-Api-Key": key,
                "Location": url_for('api.useritem', user=user) 
            },
        )

    def get(self):
        response_data = []
        users = models.User.query.all()
        for user in users:
            response_data.append(user.serialize())
        return response_data, 200

class UserItem(Resource):

    def get(self, user):
        return user.serialize()

    def put(self, user):
        if not request.json:
            return "Request content type must be JSON", 415

        try:
            validate(request.json, models.User.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        user.deserialize(request.json)

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            raise Conflict(description="Email already exists.")
        return Response(status=204)

    @auth.require()
    def delete(self, user):
        db.session.delete(user)
        db.session.commit()

        return Response(status=204)


class UserConverter(BaseConverter):
    def to_python(self, value):
        try:
            uuid_obj = uuid.UUID(value)
        except ValueError as e:
            raise NotFound("Invalid UUID format") from e
        db_product = models.User.query.filter_by(uuid=uuid_obj).first()
        if db_product is None:
            raise NotFound
        return db_product

    def to_url(self, value):
        return str(value.uuid)
