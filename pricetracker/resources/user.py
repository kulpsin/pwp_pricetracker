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
        """Create a new user
        ---
        security: []
        requestBody:
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/components/schemas/User'
        responses:
            '201':
                description: New user has been created
                headers:
                    X-Api-Key:
                        $ref: '#/components/headers/X-Api-Key'
                    Location:
                        schema:
                            type: string
                            format: uri
            '400':
                description: BadRequest - Invalid JSON or Schema
            '409':
                description: Conflict - User with this email already exists
            '415':
                description: Request content type must be JSON
        """
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

    @auth.require(admin=True)
    def get(self):
        """List all users (Admin only)
        ---
        security:
            - api_key: []
        responses:
            '200':
                description: List of all users
                content:
                    application/json:
                        schema:
                            type: array
                            items:
                                $ref: '#/components/schemas/User'
            '401':
                description: Authentication required
            '403':
                description: Admin privileges required
        """
        response_data = []
        users = models.User.query.all()
        for user in users:
            response_data.append(user.serialize())
        return response_data, 200

class UserItem(Resource):

    @auth.require(owner=True)
    def get(self, user):
        """Get user details
        ---
        security:
            - api_key: []
        parameters:
            - $ref: '#/components/parameters/user'
        responses:
            '200':
                description: User details retrieved
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/User'
            '404':
                description: User not found
        """
        return user.serialize()

    @auth.require(owner=True)
    def put(self, user):
        """Update user details
        ---
        security:
            - api_key: []
        parameters:
            - $ref: '#/components/parameters/user'
        requestBody:
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/components/schemas/User'
        responses:
            '204':
                description: User updated successfully
            '400':
                description: Invalid input
            '409':
                description: Email already exists
            '409':
                description: Request content type must be JSON
        """
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

    @auth.require(owner=True)
    def delete(self, user):
        """Delete a user
        ---
        security:
            - api_key: []
        parameters:
            - $ref: '#/components/parameters/user'
        responses:
            '204':
                description: User deleted successfully
            '404':
                description: User not found
        """
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
