from src.models.database import db, generate_uuid
from datetime import datetime
import json

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    creator_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    story = db.Column(db.Text)
    goal_amount = db.Column(db.Numeric(12, 2))
    raised_amount = db.Column(db.Numeric(12, 2), default=0)
    currency = db.Column(db.String(3), default='USD')
    category = db.Column(db.String(100))
    tags = db.Column(db.Text)  # JSON array as string
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='draft')  # 'draft', 'active', 'paused', 'completed', 'cancelled'
    campaign_type = db.Column(db.String(50))  # 'general', 'emergency', 'project', 'peer_to_peer'
    featured_image_url = db.Column(db.String(500))
    gallery_images = db.Column(db.Text)  # JSON array as string
    video_url = db.Column(db.String(500))
    updates = db.Column(db.Text)  # JSON array as string
    rewards = db.Column(db.Text)  # JSON array as string
    matching_enabled = db.Column(db.Boolean, default=False)
    matching_pool = db.Column(db.Numeric(12, 2), default=0)
    matching_ratio = db.Column(db.Numeric(3, 2), default=1.00)
    social_sharing_enabled = db.Column(db.Boolean, default=True)
    allow_anonymous = db.Column(db.Boolean, default=True)
    extra_data = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    donations = db.relationship('Donation', backref='campaign', lazy=True)
    
    def get_tags(self):
        return json.loads(self.tags) if self.tags else []
    
    def set_tags(self, tags_list):
        self.tags = json.dumps(tags_list)
    
    def get_gallery_images(self):
        return json.loads(self.gallery_images) if self.gallery_images else []
    
    def set_gallery_images(self, images_list):
        self.gallery_images = json.dumps(images_list)
    
    def get_updates(self):
        return json.loads(self.updates) if self.updates else []
    
    def set_updates(self, updates_list):
        self.updates = json.dumps(updates_list)
    
    def add_update(self, update_dict):
        current_updates = self.get_updates()
        update_dict['date'] = datetime.utcnow().isoformat()
        current_updates.append(update_dict)
        self.set_updates(current_updates)
    
    def get_rewards(self):
        return json.loads(self.rewards) if self.rewards else []
    
    def set_rewards(self, rewards_list):
        self.rewards = json.dumps(rewards_list)
    
    def get_extra_data(self):
        return json.loads(self.extra_data) if self.extra_data else {}
    
    def set_extra_data(self, data_dict):
        self.extra_data = json.dumps(data_dict)
    
    def calculate_progress_percentage(self):
        if not self.goal_amount or self.goal_amount == 0:
            return 0
        return min(100, (float(self.raised_amount) / float(self.goal_amount)) * 100)
    
    def is_active(self):
        now = datetime.utcnow()
        if self.status != 'active':
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'creator_id': self.creator_id,
            'title': self.title,
            'description': self.description,
            'story': self.story,
            'goal_amount': float(self.goal_amount) if self.goal_amount else None,
            'raised_amount': float(self.raised_amount),
            'currency': self.currency,
            'category': self.category,
            'tags': self.get_tags(),
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'campaign_type': self.campaign_type,
            'featured_image_url': self.featured_image_url,
            'gallery_images': self.get_gallery_images(),
            'video_url': self.video_url,
            'updates': self.get_updates(),
            'rewards': self.get_rewards(),
            'matching_enabled': self.matching_enabled,
            'matching_pool': float(self.matching_pool) if self.matching_pool else 0,
            'matching_ratio': float(self.matching_ratio),
            'social_sharing_enabled': self.social_sharing_enabled,
            'allow_anonymous': self.allow_anonymous,
            'extra_data': self.get_extra_data(),
            'progress_percentage': self.calculate_progress_percentage(),
            'is_active': self.is_active(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Campaign {self.title}>'

