from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Define base model class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with our Base model
db = SQLAlchemy(model_class=Base)

# Import models to ensure they're registered with SQLAlchemy
from app import models
