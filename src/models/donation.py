from src.models.database import db, generate_uuid
from datetime import datetime
import json

class Donation(db.Model):
    __tablename__ = 'donations'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    campaign_id = db.Column(db.String(36), db.ForeignKey('campaigns.id'))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    payment_method = db.Column(db.String(50))  # 'stripe', 'paypal', 'bank_transfer'
    payment_processor_id = db.Column(db.String(255))
    payment_status = db.Column(db.String(50), default='pending')
    transaction_fee = db.Column(db.Numeric(10, 2))
    platform_fee = db.Column(db.Numeric(10, 2))
    net_amount = db.Column(db.Numeric(10, 2))
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_interval = db.Column(db.String(20))  # 'monthly', 'quarterly', 'yearly'
    subscription_id = db.Column(db.String(255))
    is_anonymous = db.Column(db.Boolean, default=False)
    donor_message = db.Column(db.Text)
    dedication = db.Column(db.Text)  # JSON string for in honor/memory of
    matching_gift_eligible = db.Column(db.Boolean, default=False)
    matching_gift_status = db.Column(db.String(50))
    matching_gift_amount = db.Column(db.Numeric(10, 2))
    tax_receipt_sent = db.Column(db.Boolean, default=False)
    tax_receipt_url = db.Column(db.String(500))
    extra_data = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    matching_gifts = db.relationship('MatchingGift', backref='donation', lazy=True)
    
    def get_dedication(self):
        return json.loads(self.dedication) if self.dedication else {}
    
    def set_dedication(self, dedication_dict):
        self.dedication = json.dumps(dedication_dict)
    
    def get_extra_data(self):
        return json.loads(self.extra_data) if self.extra_data else {}
    
    def set_extra_data(self, data_dict):
        self.extra_data = json.dumps(data_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'campaign_id': self.campaign_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'payment_method': self.payment_method,
            'payment_processor_id': self.payment_processor_id,
            'payment_status': self.payment_status,
            'transaction_fee': float(self.transaction_fee) if self.transaction_fee else None,
            'platform_fee': float(self.platform_fee) if self.platform_fee else None,
            'net_amount': float(self.net_amount) if self.net_amount else None,
            'is_recurring': self.is_recurring,
            'recurring_interval': self.recurring_interval,
            'subscription_id': self.subscription_id,
            'is_anonymous': self.is_anonymous,
            'donor_message': self.donor_message,
            'dedication': self.get_dedication(),
            'matching_gift_eligible': self.matching_gift_eligible,
            'matching_gift_status': self.matching_gift_status,
            'matching_gift_amount': float(self.matching_gift_amount) if self.matching_gift_amount else None,
            'tax_receipt_sent': self.tax_receipt_sent,
            'tax_receipt_url': self.tax_receipt_url,
            'extra_data': self.get_extra_data(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Donation {self.id}: ${self.amount}>'

class PaymentMethod(db.Model):
    __tablename__ = 'payment_methods'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50))  # 'card', 'bank_account', 'paypal'
    provider = db.Column(db.String(50))  # 'stripe', 'paypal'
    provider_payment_method_id = db.Column(db.String(255))
    last_four = db.Column(db.String(4))
    brand = db.Column(db.String(50))
    expiry_month = db.Column(db.Integer)
    expiry_year = db.Column(db.Integer)
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    extra_data = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_extra_data(self):
        return json.loads(self.extra_data) if self.extra_data else {}
    
    def set_extra_data(self, data_dict):
        self.extra_data = json.dumps(data_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'provider': self.provider,
            'provider_payment_method_id': self.provider_payment_method_id,
            'last_four': self.last_four,
            'brand': self.brand,
            'expiry_month': self.expiry_month,
            'expiry_year': self.expiry_year,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'extra_data': self.get_extra_data(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<PaymentMethod {self.type}: ****{self.last_four}>'

class MatchingGift(db.Model):
    __tablename__ = 'matching_gifts'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    donation_id = db.Column(db.String(36), db.ForeignKey('donations.id'), nullable=False)
    employer_name = db.Column(db.String(255))
    employer_ein = db.Column(db.String(20))
    employee_email = db.Column(db.String(255))
    match_ratio = db.Column(db.Numeric(3, 2))
    match_amount = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(50), default='pending')  # 'pending', 'submitted', 'approved', 'paid', 'denied'
    submission_date = db.Column(db.DateTime)
    approval_date = db.Column(db.DateTime)
    payment_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    extra_data = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_extra_data(self):
        return json.loads(self.extra_data) if self.extra_data else {}
    
    def set_extra_data(self, data_dict):
        self.extra_data = json.dumps(data_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'donation_id': self.donation_id,
            'employer_name': self.employer_name,
            'employer_ein': self.employer_ein,
            'employee_email': self.employee_email,
            'match_ratio': float(self.match_ratio) if self.match_ratio else None,
            'match_amount': float(self.match_amount) if self.match_amount else None,
            'status': self.status,
            'submission_date': self.submission_date.isoformat() if self.submission_date else None,
            'approval_date': self.approval_date.isoformat() if self.approval_date else None,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'notes': self.notes,
            'extra_data': self.get_extra_data(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<MatchingGift {self.id}: {self.employer_name}>'

