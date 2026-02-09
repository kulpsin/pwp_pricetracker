from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    product = db.Column(db.String(128), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    notes = db.Column(db.String(512), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    user = db.relationship("User", back_populates="products")
    prices = db.relationship("Price", back_populates="product")

class Price(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"))
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

    product = db.relationship("Product", back_populates="prices")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False)

    products = db.relationship("Product", back_populates="user")
    

# Create the database with some test entries
with app.app_context():
    db.drop_all()
    db.create_all()

    user1 = User(email="user1@email.com", password="hash1")
    user2 = User(email="user2@email.com", password="hash2")
    db.session.add_all([user1, user2])
    db.session.commit()

    product1 = Product(product="PS5", url="https://www.gigantti.fi/product/gaming/pelikonsolit-ja-tarvikkeet/playstation/playstation-konsolit/playstation-5-slim-standard-edition-e-runko-1-tb/988057iuoe", user=user1, notes="Standard edition")
    product2 = Product(product="Ikea desk", url="https://www.ikea.com/fi/fi/p/anfallare-alex-tyoepoeytae-bambu-mustanruskea-s89417745/?recently_viewed=b", user=user2)
    product3 = Product(product="Broken product", url="https://www.outdated_url.com", user=user2, notes="This is a product with a non-functional url.", active=False)
    db.session.add_all([product1, product2, product3])
    db.session.commit()

    price1 = Price(price=599.0, timestamp=datetime.now(), product=product1)
    price2 = Price(price=188.0, timestamp=datetime.now(), product=product2)
    price3 = Price(price=599.0, timestamp=datetime.now() + timedelta(days=1), product=product1)
    price4 = Price(price=149.0, timestamp=datetime.now() + timedelta(days=1), product=product2)
    db.session.add_all([price1, price2, price3, price4])
    db.session.commit()
