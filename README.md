# PWP SPRING 2026
# PROJECT NAME
# Group information
* Student 1. Name and email
* [Olli Puhakka](mailto:opuhakka@student.oulu.fi)
* [Nadira Tasnim](mailto:ntasnim25@student.oulu.fi)
* Student 4. Name and email

# Dependencies

- Flask
- pysqlite3
- flask-sqlalchemy

All the dependencies can be installed by running `pip install -r requirements.txt`.

# Database

We currently support SQLite 3 database. The database can be initialized by running `flask --app pricetracker init-db`. Test data can be populated by running `flask --app pricetracker testgen`. Pre-populated database can also be inspected at [test.db](test.db).

# Development Setup

```shell
# Clone the repository. You can use https, if you don't intend to push changes.
git clone git@github.com:kulpsin/pwp_pricetracker.git
cd pwp_pricetracker

# Create virtual environment and activate it
python3 -m venv .venv
. .venv/bin/activate

# Install the project in editable/development mode
pip install -e .

# Initialize database
flask --app pricetracker init-db

# Optional: populate database with test data
flask --app pricetracker testgen

# Start development server
flask --app pricetracker run --debug

# Test that you can send requests to the server
curl 'http://127.0.0.1:5000/hello'
```

---

__Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint, instructions on how to setup and run the client, instructions on how to setup and run the axiliary service and instructions on how to deploy the api in a production environment__


