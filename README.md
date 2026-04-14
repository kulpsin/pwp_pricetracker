# PWP SPRING 2026
# Price Tracker API
# Group information
* Miro Kakkonen
* [Olli Puhakka](mailto:opuhakka@student.oulu.fi)
* Jeremias Nevalainen

# Dependencies

Full list of the required and optional dependancies can be found at [`pyproject.toml`](pyproject.toml).

Required dependancies:

- Flask
- Flask-SQLAlchemy
- flask-restful
- jsonschema
- flask-caching
- flasgger
- gunicorn

Optional dependancies:

- pylint
- pytest
- pytest-cov

All the required dependencies will be installed when installing the main package by running `pip install .`.

# Environment setup

## Local installation

Running these commands will install the environment in development mode

```shell
# Clone the repository. You can use https, if you don't intend to push changes.
git clone git@github.com:kulpsin/pwp_pricetracker.git
cd pwp_pricetracker

# Create virtual environment and activate it
python3 -m venv .venv
. .venv/bin/activate

# Install the project in editable/development mode
pip install -e .[dev]

# Initialize database
flask --app pricetracker init-db

# Optional: populate database with test data
flask --app pricetracker testgen

# Start development server
flask --app pricetracker run --debug

# Test that you can send requests to the server
curl 'http://127.0.0.1:5000/hello'
```

## Docker installation

```shell
# Clone the repository. You can use https, if you don't intend to push changes.
git clone git@github.com:kulpsin/pwp_pricetracker.git
cd pwp_pricetracker

# Build the docker image
docker compose build

# Set the port you want to serve the app from
echo "APP_PORT=8000" > .env

# Start the docker container in detached mode
docker compose up -d

# Test that you can send requests to the server
curl 'http://127.0.0.1:8000/hello'
```

The reverse proxy can be setup to handle the traffic from outside of the node to the localhost:8000.
For example, Nginx provides guide for configuring a [Reverse Proxy](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/).

If you wish to populate the server with test data, you can do that by running `docker compose exec app flask --app pricetracker testgen`.


# Credentials

Anyone can create users and api keys will be provided on user creation. Some endpoints might require admin or worker api keys
and those can be created only via cli-commands:

- Create an admin user: `flask --app pricetracker add-admin-user <EMAIL>`
- Create a worker key for an user: `flask --app pricetracker add-worker-key <EMAIL>`

# Database

We currently support SQLite 3 database. The database can be initialized by running `flask --app pricetracker init-db`. Test data can be populated by running `flask --app pricetracker testgen`. Pre-populated database can also be inspected at [test.db](test.db).

# Testing

You can run tests by running following commands in root directory.

```shell
# pytest: runs tests/test*.py files
pytest .
# pytest-cov
pytest --cov=.

# pylint: static code analysis.
pylint .
```

Pylint can be configured by modifying [`pylintrc.toml`](pylintrc.toml)-file.

---

__Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint, instructions on how to setup and run the client, instructions on how to setup and run the axiliary service and instructions on how to deploy the api in a production environment__
