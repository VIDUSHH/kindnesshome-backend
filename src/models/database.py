from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())

# Association table for many-to-many relationship between organizations and categories
organization_categories = db.Table('organization_categories',
    db.Column('organization_id', db.String(36), db.ForeignKey('organizations.id'), primary_key=True),
    db.Column('category_id', db.String(36), db.ForeignKey('categories.id'), primary_key=True)
)

