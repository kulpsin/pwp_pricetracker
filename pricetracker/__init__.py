#!/usr/bin/env python3
"""
Price Tracker is an Flask API application which
allows users to add tracking requests and workers can
add product price information to tracked products.
"""
import os

from flask import Flask

from . import utils


# Used https://flask.palletsprojects.com/en/stable/tutorial/factory/#the-application-factory
# and
# https://github.com/UniOulu-Ubicomp-Programming-Courses/pwp-sensorhub-example/blob/ex2-project-layout/sensorhub/__init__.py
# as base.
def create_app(test_config: dict|None=None) -> Flask:
    """
    Create and configure the application

    :param test_config: Configuration to be used. If not provided,
        'config.py' is loaded instead and if that does not exist,
        use defaults.
    :return: Flask application instance
    :rtype: Flask
    """
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "development.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    # pylint: disable=C0415 (wrong-import-position)
    from . import api
    app.register_blueprint(api.api_bp, url_prefix='/api')

    # pylint: disable=C0415 (wrong-import-position)
    from .db import db
    db.init_app(app)
    # pylint: disable=C0415 (wrong-import-position)
    from . import cli
    app.cli.add_command(cli.init_db_command)
    app.cli.add_command(cli.generate_test_data)
    app.cli.add_command(cli.remove_test_data)
    return app
