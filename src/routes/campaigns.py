from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.database import db
from src.models.campaign import Campaign
from src.models.organization import Organization
from src.models.user import User
from datetime import datetime
from decimal import Decimal

campaigns_bp = Blueprint('campaigns', __name__)

@campaigns_bp.route('', methods=['GET'])
def get_campaigns():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', 'active')
        category = request.args.get('category', '')
        search = request.args.get('search', '')
        featured = request.args.get('featured', 'false').lower() == 'true'
        
        query = Campaign.query
        
        # Apply status filter
        if status:
            query = query.filter_by(status=status)
        
        # Apply category filter
        if category:
            query = query.filter_by(category=category)
        
        # Apply search filter
        if search:
            query = query.filter(
                db.or_(
                    Campaign.title.ilike(f'%{search}%'),
                    Campaign.description.ilike(f'%{search}%')
                )
            )
        
        # Apply featured filter (would need a featured field in production)
        # For now, we'll order by raised amount as a proxy for featured
        if featured:
            query = query.order_by(Campaign.raised_amount.desc())
        else:
            query = query.order_by(Campaign.created_at.desc())
        
        campaigns = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'campaigns': [campaign.to_dict() for campaign in campaigns.items],
            'total': campaigns.total,
            'pages': campaigns.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@campaigns_bp.route('/<campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    try:
        campaign = Campaign.query.get(campaign_id)
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Include organization and creator details
        campaign_data = campaign.to_dict()
        
        if campaign.organization:
            campaign_data['organization'] = {
                'id': campaign.organization.id,
                'name': campaign.organization.name,
                'logo_url': campaign.organization.logo_url,
                'verification_status': campaign.organization.verification_status
            }
        
        if campaign.creator:
            campaign_data['creator'] = {
                'id': campaign.creator.id,
                'name': f"{campaign.creator.first_name} {campaign.creator.last_name}",
                'profile_image_url': campaign.creator.profile_image_url
            }
        
        return jsonify({
            'campaign': campaign_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@campaigns_bp.route('', methods=['POST'])
@jwt_required()
def create_campaign():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['organization_id', 'title', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate organization exists
        organization = Organization.query.get(data['organization_id'])
        if not organization or not organization.is_active:
            return jsonify({'error': 'Organization not found'}), 404
        
        # Parse dates
        start_date = None
        end_date = None
        
        if data.get('start_date'):
            try:
                start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
            except:
                return jsonify({'error': 'Invalid start_date format'}), 400
        
        if data.get('end_date'):
            try:
                end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
            except:
                return jsonify({'error': 'Invalid end_date format'}), 400
        
        campaign = Campaign(
            organization_id=data['organization_id'],
            creator_id=current_user_id,
            title=data['title'],
            description=data['description'],
            story=data.get('story'),
            goal_amount=Decimal(str(data['goal_amount'])) if data.get('goal_amount') else None,
            currency=data.get('currency', 'USD'),
            category=data.get('category'),
            start_date=start_date,
            end_date=end_date,
            status=data.get('status', 'draft'),
            campaign_type=data.get('campaign_type', 'general'),
            featured_image_url=data.get('featured_image_url'),
            video_url=data.get('video_url'),
            matching_enabled=data.get('matching_enabled', False),
            matching_pool=Decimal(str(data['matching_pool'])) if data.get('matching_pool') else Decimal('0'),
            matching_ratio=Decimal(str(data['matching_ratio'])) if data.get('matching_ratio') else Decimal('1.00'),
            social_sharing_enabled=data.get('social_sharing_enabled', True),
            allow_anonymous=data.get('allow_anonymous', True)
        )
        
        # Handle tags
        if 'tags' in data:
            campaign.set_tags(data['tags'])
        
        # Handle gallery images
        if 'gallery_images' in data:
            campaign.set_gallery_images(data['gallery_images'])
        
        # Handle rewards
        if 'rewards' in data:
            campaign.set_rewards(data['rewards'])
        
        # Handle metadata
        if 'metadata' in data:
            campaign.set_metadata(data['metadata'])
        
        db.session.add(campaign)
        db.session.commit()
        
        return jsonify({
            'message': 'Campaign created successfully',
            'campaign': campaign.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@campaigns_bp.route('/<campaign_id>', methods=['PUT'])
@jwt_required()
def update_campaign(campaign_id):
    try:
        current_user_id = get_jwt_identity()
        
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            creator_id=current_user_id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found or access denied'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        allowed_fields = [
            'title', 'description', 'story', 'goal_amount', 'category',
            'featured_image_url', 'video_url', 'status', 'matching_enabled',
            'matching_pool', 'matching_ratio', 'social_sharing_enabled', 'allow_anonymous'
        ]
        
        for field in allowed_fields:
            if field in data:
                if field in ['goal_amount', 'matching_pool', 'matching_ratio']:
                    setattr(campaign, field, Decimal(str(data[field])) if data[field] else None)
                else:
                    setattr(campaign, field, data[field])
        
        # Handle date updates
        if 'start_date' in data:
            try:
                campaign.start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00')) if data['start_date'] else None
            except:
                return jsonify({'error': 'Invalid start_date format'}), 400
        
        if 'end_date' in data:
            try:
                campaign.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00')) if data['end_date'] else None
            except:
                return jsonify({'error': 'Invalid end_date format'}), 400
        
        # Handle array fields
        if 'tags' in data:
            campaign.set_tags(data['tags'])
        
        if 'gallery_images' in data:
            campaign.set_gallery_images(data['gallery_images'])
        
        if 'rewards' in data:
            campaign.set_rewards(data['rewards'])
        
        if 'metadata' in data:
            campaign.set_metadata(data['metadata'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Campaign updated successfully',
            'campaign': campaign.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@campaigns_bp.route('/<campaign_id>', methods=['DELETE'])
@jwt_required()
def delete_campaign(campaign_id):
    try:
        current_user_id = get_jwt_identity()
        
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            creator_id=current_user_id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found or access denied'}), 404
        
        # Check if campaign has donations
        if campaign.donations:
            return jsonify({'error': 'Cannot delete campaign with existing donations'}), 400
        
        db.session.delete(campaign)
        db.session.commit()
        
        return jsonify({
            'message': 'Campaign deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@campaigns_bp.route('/<campaign_id>/donate', methods=['POST'])
@jwt_required()
def donate_to_campaign(campaign_id):
    try:
        current_user_id = get_jwt_identity()
        
        campaign = Campaign.query.get(campaign_id)
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        if not campaign.is_active():
            return jsonify({'error': 'Campaign is not currently active'}), 400
        
        data = request.get_json()
        
        # Validate amount
        if not data.get('amount'):
            return jsonify({'error': 'Amount is required'}), 400
        
        try:
            amount = Decimal(str(data['amount']))
            if amount <= 0:
                return jsonify({'error': 'Amount must be greater than 0'}), 400
        except:
            return jsonify({'error': 'Invalid amount format'}), 400
        
        # Create donation (reuse donation creation logic)
        from src.models.donation import Donation
        
        transaction_fee = amount * Decimal('0.029') + Decimal('0.30')
        platform_fee = amount * Decimal('0.01') if data.get('cover_fees', False) else Decimal('0')
        net_amount = amount - transaction_fee - platform_fee
        
        donation = Donation(
            user_id=current_user_id,
            organization_id=campaign.organization_id,
            campaign_id=campaign_id,
            amount=amount,
            currency=data.get('currency', 'USD'),
            payment_method=data.get('payment_method', 'stripe'),
            payment_processor_id=f"camp_{campaign_id}_{current_user_id}",
            payment_status='completed',  # Simplified for demo
            transaction_fee=transaction_fee,
            platform_fee=platform_fee,
            net_amount=net_amount,
            is_anonymous=data.get('is_anonymous', False),
            donor_message=data.get('donor_message')
        )
        
        db.session.add(donation)
        
        # Update campaign raised amount
        campaign.raised_amount = (campaign.raised_amount or 0) + amount
        
        # Handle matching if enabled
        if campaign.matching_enabled and campaign.matching_pool > 0:
            match_amount = min(amount * campaign.matching_ratio, campaign.matching_pool)
            if match_amount > 0:
                campaign.matching_pool -= match_amount
                campaign.raised_amount += match_amount
                
                # Create a matching donation record
                matching_donation = Donation(
                    user_id=current_user_id,
                    organization_id=campaign.organization_id,
                    campaign_id=campaign_id,
                    amount=match_amount,
                    currency=data.get('currency', 'USD'),
                    payment_method='platform_matching',
                    payment_processor_id=f"match_{campaign_id}_{current_user_id}",
                    payment_status='completed',
                    transaction_fee=Decimal('0'),
                    platform_fee=Decimal('0'),
                    net_amount=match_amount,
                    is_anonymous=True,
                    donor_message='Platform matching donation'
                )
                db.session.add(matching_donation)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Donation to campaign successful',
            'donation': donation.to_dict(),
            'campaign': campaign.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@campaigns_bp.route('/featured', methods=['GET'])
def get_featured_campaigns():
    try:
        limit = request.args.get('limit', 6, type=int)
        
        # Get campaigns with highest raised amounts as featured
        campaigns = Campaign.query.filter_by(status='active')\
                                 .order_by(Campaign.raised_amount.desc())\
                                 .limit(limit).all()
        
        return jsonify({
            'campaigns': [campaign.to_dict() for campaign in campaigns]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@campaigns_bp.route('/<campaign_id>/updates', methods=['POST'])
@jwt_required()
def add_campaign_update(campaign_id):
    try:
        current_user_id = get_jwt_identity()
        
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            creator_id=current_user_id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found or access denied'}), 404
        
        data = request.get_json()
        
        if not data.get('title') or not data.get('content'):
            return jsonify({'error': 'Title and content are required'}), 400
        
        update = {
            'title': data['title'],
            'content': data['content'],
            'image_url': data.get('image_url')
        }
        
        campaign.add_update(update)
        db.session.commit()
        
        return jsonify({
            'message': 'Campaign update added successfully',
            'campaign': campaign.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@campaigns_bp.route('/<campaign_id>/analytics', methods=['GET'])
@jwt_required()
def get_campaign_analytics(campaign_id):
    try:
        current_user_id = get_jwt_identity()
        
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            creator_id=current_user_id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found or access denied'}), 404
        
        # Calculate analytics
        from src.models.donation import Donation
        
        donations = Donation.query.filter_by(campaign_id=campaign_id).all()
        
        total_donations = len(donations)
        total_raised = sum(float(d.amount) for d in donations)
        average_donation = total_raised / total_donations if total_donations > 0 else 0
        unique_donors = len(set(d.user_id for d in donations))
        
        # Group donations by date for chart data
        from collections import defaultdict
        daily_donations = defaultdict(lambda: {'count': 0, 'amount': 0})
        
        for donation in donations:
            date_key = donation.created_at.date().isoformat()
            daily_donations[date_key]['count'] += 1
            daily_donations[date_key]['amount'] += float(donation.amount)
        
        analytics = {
            'total_donations': total_donations,
            'total_raised': total_raised,
            'average_donation': average_donation,
            'unique_donors': unique_donors,
            'goal_amount': float(campaign.goal_amount) if campaign.goal_amount else None,
            'progress_percentage': campaign.calculate_progress_percentage(),
            'daily_data': dict(daily_donations),
            'top_donations': [d.to_dict() for d in sorted(donations, key=lambda x: x.amount, reverse=True)[:5]]
        }
        
        return jsonify({
            'analytics': analytics
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

