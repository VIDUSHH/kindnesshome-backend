from src.models.database import db, generate_uuid, organization_categories
from datetime import datetime
import json

class Organization(db.Model):
    __tablename__ = 'organizations'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    ein = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    mission_statement = db.Column(db.Text)
    website_url = db.Column(db.String(500))
    logo_url = db.Column(db.String(500))
    cover_image_url = db.Column(db.String(500))
    address = db.Column(db.Text)  # JSON string
    contact_info = db.Column(db.Text)  # JSON string
    ntee_codes = db.Column(db.Text)  # JSON array as string
    tax_exempt_status = db.Column(db.String(50))
    deductibility_status = db.Column(db.String(50))
    verification_status = db.Column(db.String(50), default='pending')
    verification_date = db.Column(db.DateTime)
    irs_data = db.Column(db.Text)  # JSON string
    financial_data = db.Column(db.Text)  # JSON string
    social_media = db.Column(db.Text)  # JSON string
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    donations = db.relationship('Donation', backref='organization', lazy=True)
    campaigns = db.relationship('Campaign', backref='organization', lazy=True)
    categories = db.relationship('Category', secondary=organization_categories, backref='organizations')
    
    def get_address(self):
        return json.loads(self.address) if self.address else {}
    
    def set_address(self, address_dict):
        self.address = json.dumps(address_dict)
    
    def get_contact_info(self):
        return json.loads(self.contact_info) if self.contact_info else {}
    
    def set_contact_info(self, contact_dict):
        self.contact_info = json.dumps(contact_dict)
    
    def get_ntee_codes(self):
        return json.loads(self.ntee_codes) if self.ntee_codes else []
    
    def set_ntee_codes(self, codes_list):
        self.ntee_codes = json.dumps(codes_list)
    
    def get_irs_data(self):
        return json.loads(self.irs_data) if self.irs_data else {}
    
    def set_irs_data(self, data_dict):
        self.irs_data = json.dumps(data_dict)
    
    def get_financial_data(self):
        return json.loads(self.financial_data) if self.financial_data else {}
    
    def set_financial_data(self, data_dict):
        self.financial_data = json.dumps(data_dict)
    
    def get_social_media(self):
        return json.loads(self.social_media) if self.social_media else {}
    
    def set_social_media(self, social_dict):
        self.social_media = json.dumps(social_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ein': self.ein,
            'name': self.name,
            'description': self.description,
            'mission_statement': self.mission_statement,
            'website_url': self.website_url,
            'logo_url': self.logo_url,
            'cover_image_url': self.cover_image_url,
            'address': self.get_address(),
            'contact_info': self.get_contact_info(),
            'ntee_codes': self.get_ntee_codes(),
            'tax_exempt_status': self.tax_exempt_status,
            'deductibility_status': self.deductibility_status,
            'verification_status': self.verification_status,
            'verification_date': self.verification_date.isoformat() if self.verification_date else None,
            'irs_data': self.get_irs_data(),
            'financial_data': self.get_financial_data(),
            'social_media': self.get_social_media(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'categories': [cat.to_dict() for cat in self.categories]
        }
    
    def __repr__(self):
        return f'<Organization {self.name}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.String(36), db.ForeignKey('categories.id'))
    icon_url = db.Column(db.String(500))
    color = db.Column(db.String(7))  # hex color
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Self-referential relationship for parent/child categories
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'parent_id': self.parent_id,
            'icon_url': self.icon_url,
            'color': self.color,
            'sort_order': self.sort_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Category {self.name}>'

class NTEECode(db.Model):
    __tablename__ = 'ntee_codes'
    
    code = db.Column(db.String(10), primary_key=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))
    subcategory = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'code': self.code,
            'description': self.description,
            'category': self.category,
            'subcategory': self.subcategory,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<NTEECode {self.code}>'

