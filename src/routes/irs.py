from flask import Blueprint, request, jsonify
from src.services.mock_irs_service import MockIRSDataService
from src.models.organization import Organization
from src.models.database import db
from datetime import datetime
import logging

irs_bp = Blueprint('irs', __name__, url_prefix='/api/irs')

@irs_bp.route('/verify-ein', methods=['POST'])
def verify_ein():
    """Verify an organization's EIN with IRS data"""
    try:
        data = request.get_json()
        ein = data.get('ein')
        
        if not ein:
            return jsonify({'error': 'EIN is required'}), 400
        
        irs_service = MockIRSDataService()
        
        # Validate EIN format
        if not irs_service.validate_ein_format(ein):
            return jsonify({
                'valid': False,
                'error': 'Invalid EIN format'
            }), 400
        
        # Use mock verification
        result = irs_service.verify_organization(ein)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error verifying EIN: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@irs_bp.route('/categories', methods=['GET'])
def get_ntee_categories():
    """Get all NTEE categories with organization counts"""
    try:
        irs_service = MockIRSDataService()
        categories = irs_service.get_mock_categories()
        
        return jsonify({
            'categories': categories,
            'total_organizations': sum(cat['organization_count'] for cat in categories)
        })
        
    except Exception as e:
        logging.error(f"Error getting NTEE categories: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@irs_bp.route('/organization-status/<ein>', methods=['GET'])
def get_organization_status(ein):
    """Get detailed organization status from IRS data"""
    try:
        irs_service = MockIRSDataService()
        
        # Validate EIN format
        if not irs_service.validate_ein_format(ein):
            return jsonify({'error': 'Invalid EIN format'}), 400
        
        result = irs_service.verify_organization(ein)
        
        if not result.get('valid'):
            return jsonify({'error': 'Organization not found'}), 404
        
        org_data = result['organization']
        category = irs_service.get_ntee_category(org_data.get('ntee_code'))
        
        status_info = {
            'ein': org_data['ein'],
            'name': org_data['name'],
            'tax_exempt_status': org_data['tax_exempt_status'],
            'is_verified': org_data['is_verified'],
            'verification_date': datetime.now().isoformat(),
            'ntee_code': org_data.get('ntee_code'),
            'category': category,
            'location': {
                'city': org_data.get('city'),
                'state': org_data.get('state'),
                'zip_code': org_data.get('zip_code')
            },
            'eligible_for_donations': org_data['tax_exempt_status'] == '501(c)(3)',
            'last_updated': datetime.now().isoformat()
        }
        
        return jsonify(status_info)
        
    except Exception as e:
        logging.error(f"Error getting organization status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

