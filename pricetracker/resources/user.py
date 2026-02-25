# This code has the same structure as the Sensorhub example provided in the course material
# (https://github.com/UniOulu-Ubicomp-Programming-Courses/pwp-sensorhub-example/blob/ex2-05-validation/app.py)

from flask import Response, request
from flask_restful import Resource
from jsonschema import ValidationError, validate
from werkzeug.exceptions import BadRequest, Conflict
from sqlalchemy.exc import IntegrityError

from .. import models
from ..db import db

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

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            raise Conflict(description="Email already exists.")

        return Response(status=201)

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

    def delete(self, user):
        db.session.delete(user)
        db.session.commit()

        return Response(status=204)
    
