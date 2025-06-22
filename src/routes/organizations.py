from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.database import db
from src.models.organization import Organization, Category, NTEECode
from sqlalchemy import or_, and_

organizations_bp = Blueprint('organizations', __name__)

@organizations_bp.route('', methods=['GET'])
def get_organizations():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        ntee_code = request.args.get('ntee_code', '')
        verified_only = request.args.get('verified_only', 'false').lower() == 'true'
        
        query = Organization.query.filter_by(is_active=True)
        
        # Apply search filter
        if search:
            query = query.filter(
                or_(
                    Organization.name.ilike(f'%{search}%'),
                    Organization.description.ilike(f'%{search}%'),
                    Organization.mission_statement.ilike(f'%{search}%')
                )
            )
        
        # Apply verification filter
        if verified_only:
            query = query.filter_by(verification_status='verified')
        
        # Apply category filter
        if category:
            query = query.join(Organization.categories).filter(Category.slug == category)
        
        # Apply NTEE code filter
        if ntee_code:
            query = query.filter(Organization.ntee_codes.contains(f'"{ntee_code}"'))
        
        organizations = query.order_by(Organization.name)\
                            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'organizations': [org.to_dict() for org in organizations.items],
            'total': organizations.total,
            'pages': organizations.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@organizations_bp.route('/<organization_id>', methods=['GET'])
def get_organization(organization_id):
    try:
        organization = Organization.query.get(organization_id)
        
        if not organization or not organization.is_active:
            return jsonify({'error': 'Organization not found'}), 404
        
        return jsonify({
            'organization': organization.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@organizations_bp.route('', methods=['POST'])
@jwt_required()
def create_organization():
    try:
        # This would typically be admin-only in production
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['ein', 'name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if organization with EIN already exists
        existing_org = Organization.query.filter_by(ein=data['ein']).first()
        if existing_org:
            return jsonify({'error': 'Organization with this EIN already exists'}), 409
        
        organization = Organization(
            ein=data['ein'],
            name=data['name'],
            description=data.get('description'),
            mission_statement=data.get('mission_statement'),
            website_url=data.get('website_url'),
            logo_url=data.get('logo_url'),
            cover_image_url=data.get('cover_image_url'),
            tax_exempt_status=data.get('tax_exempt_status'),
            deductibility_status=data.get('deductibility_status')
        )
        
        # Handle address
        if 'address' in data:
            organization.set_address(data['address'])
        
        # Handle contact info
        if 'contact_info' in data:
            organization.set_contact_info(data['contact_info'])
        
        # Handle NTEE codes
        if 'ntee_codes' in data:
            organization.set_ntee_codes(data['ntee_codes'])
        
        # Handle social media
        if 'social_media' in data:
            organization.set_social_media(data['social_media'])
        
        db.session.add(organization)
        db.session.commit()
        
        return jsonify({
            'message': 'Organization created successfully',
            'organization': organization.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@organizations_bp.route('/search', methods=['GET'])
def search_organizations():
    try:
        query_text = request.args.get('q', '')
        limit = request.args.get('limit', 10, type=int)
        
        if not query_text:
            return jsonify({'organizations': []}), 200
        
        organizations = Organization.query.filter(
            and_(
                Organization.is_active == True,
                or_(
                    Organization.name.ilike(f'%{query_text}%'),
                    Organization.description.ilike(f'%{query_text}%')
                )
            )
        ).limit(limit).all()
        
        return jsonify({
            'organizations': [org.to_dict() for org in organizations]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@organizations_bp.route('/categories', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.filter_by(is_active=True)\
                                  .order_by(Category.sort_order, Category.name).all()
        
        return jsonify({
            'categories': [cat.to_dict() for cat in categories]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@organizations_bp.route('/<organization_id>/campaigns', methods=['GET'])
def get_organization_campaigns(organization_id):
    try:
        organization = Organization.query.get(organization_id)
        
        if not organization or not organization.is_active:
            return jsonify({'error': 'Organization not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status', 'active')
        
        from src.models.campaign import Campaign
        
        query = Campaign.query.filter_by(organization_id=organization_id)
        
        if status:
            query = query.filter_by(status=status)
        
        campaigns = query.order_by(Campaign.created_at.desc())\
                        .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'campaigns': [campaign.to_dict() for campaign in campaigns.items],
            'total': campaigns.total,
            'pages': campaigns.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@organizations_bp.route('/<organization_id>/verify', methods=['POST'])
@jwt_required()
def verify_organization(organization_id):
    try:
        # This would typically integrate with IRS API
        # For now, we'll simulate the verification process
        
        organization = Organization.query.get(organization_id)
        
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        # Simulate IRS verification
        # In production, this would call CharityAPI.org or similar service
        verification_data = {
            'ein_verified': True,
            'tax_exempt_status': '501(c)(3)',
            'deductibility_status': 'Deductible',
            'verification_source': 'IRS_API_SIMULATION'
        }
        
        organization.verification_status = 'verified'
        organization.verification_date = db.func.now()
        organization.tax_exempt_status = verification_data['tax_exempt_status']
        organization.deductibility_status = verification_data['deductibility_status']
        organization.set_irs_data(verification_data)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Organization verified successfully',
            'organization': organization.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

