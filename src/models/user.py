from src.models.database import db, generate_uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    address = db.Column(db.Text)  # JSON string
    profile_image_url = db.Column(db.String(500))
    auth_provider = db.Column(db.String(50))  # 'google', 'facebook', 'email'
    auth_provider_id = db.Column(db.String(255))
    email_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    preferences = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    donations = db.relationship('Donation', backref='donor', lazy=True)
    campaigns = db.relationship('Campaign', backref='creator', lazy=True)
    payment_methods = db.relationship('PaymentMethod', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_address(self):
        return json.loads(self.address) if self.address else {}
    
    def set_address(self, address_dict):
        self.address = json.dumps(address_dict)
    
    def get_preferences(self):
        return json.loads(self.preferences) if self.preferences else {}
    
    def set_preferences(self, preferences_dict):
        self.preferences = json.dumps(preferences_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'address': self.get_address(),
            'profile_image_url': self.profile_image_url,
            'auth_provider': self.auth_provider,
            'email_verified': self.email_verified,
            'is_active': self.is_active,
            'preferences': self.get_preferences(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<User {self.email}>'

