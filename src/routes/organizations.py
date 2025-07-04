"""
Organization API routes for KindnessHome platform
RESTful endpoints for charitable organization data
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import os

# Import our services (these will be added to the backend)
from ..services.organization_service import OrganizationService

logger = logging.getLogger(__name__)

# Create blueprint for organization routes
organizations_bp = Blueprint('organizations', __name__, url_prefix='/api/organizations')

# Initialize organization service
org_service = OrganizationService()

@organizations_bp.route('/search', methods=['GET'])
def search_organizations():
    """
    Search for organizations by name, location, or category
    
    Query Parameters:
        q (str): Search query for organization name
        state (str): Filter by state code (e.g., 'CA', 'NY')
        city (str): Filter by city name
        category (str): Filter by NTEE category code (A-Z)
        limit (int): Maximum number of results (default 20, max 100)
        
    Returns:
        JSON response with organization list
    """
    try:
        # Get query parameters
        query = request.args.get('q', '').strip()
        state = request.args.get('state', '').strip()
        city = request.args.get('city', '').strip()
        category = request.args.get('category', '').strip()
        limit = min(int(request.args.get('limit', 20)), 100)
        
        # Validate required parameters
        if not query or len(query) < 2:
            return jsonify({
                'error': 'Search query must be at least 2 characters long',
                'data': []
            }), 400
        
        # Search organizations
        organizations = org_service.search_organizations(
            query=query,
            state=state.upper() if state else None,
            city=city,
            category=category.upper() if category else None,
            limit=limit
        )
        
        # Convert to JSON
        org_list = [org.to_dict() for org in organizations]
        
        return jsonify({
            'data': org_list,
            'count': len(org_list),
            'query': query,
            'filters': {
                'state': state.upper() if state else None,
                'city': city if city else None,
                'category': category.upper() if category else None
            }
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error in organization search: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@organizations_bp.route('/<ein>', methods=['GET'])
def get_organization(ein):
    """
    Get organization details by EIN (Tax ID)
    
    Args:
        ein (str): Employer Identification Number
        
    Returns:
        JSON response with organization details
    """
    try:
        # Validate EIN format (basic validation)
        clean_ein = ein.replace('-', '').replace(' ', '')
        if not clean_ein.isdigit() or len(clean_ein) != 9:
            return jsonify({'error': 'Invalid EIN format. Must be 9 digits.'}), 400
        
        # Get organization
        organization = org_service.get_organization_by_ein(clean_ein)
        
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        return jsonify({
            'data': organization.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting organization {ein}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@organizations_bp.route('/verify/<ein>', methods=['GET'])
def verify_organization(ein):
    """
    Verify organization's charitable status and tax-deductible eligibility
    
    Args:
        ein (str): Employer Identification Number
        
    Returns:
        JSON response with verification results
    """
    try:
        # Validate EIN format
        clean_ein = ein.replace('-', '').replace(' ', '')
        if not clean_ein.isdigit() or len(clean_ein) != 9:
            return jsonify({'error': 'Invalid EIN format. Must be 9 digits.'}), 400
        
        # Verify organization
        verification = org_service.verify_organization(clean_ein)
        
        return jsonify(verification)
        
    except Exception as e:
        logger.error(f"Error verifying organization {ein}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@organizations_bp.route('/popular', methods=['GET'])
def get_popular_organizations():
    """
    Get most popular/searched organizations
    
    Query Parameters:
        limit (int): Maximum number of results (default 20, max 50)
        
    Returns:
        JSON response with popular organizations
    """
    try:
        limit = min(int(request.args.get('limit', 20)), 50)
        
        organizations = org_service.get_popular_organizations(limit)
        org_list = [org.to_dict() for org in organizations]
        
        return jsonify({
            'data': org_list,
            'count': len(org_list)
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid limit parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error getting popular organizations: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@organizations_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Get list of available organization categories (NTEE codes)
    
    Returns:
        JSON response with category list
    """
    try:
        categories = org_service.get_categories()
        
        return jsonify({
            'data': categories,
            'count': len(categories)
        })
        
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@organizations_bp.route('/categories/<category_code>', methods=['GET'])
def get_organizations_by_category(category_code):
    """
    Get organizations by NTEE category
    
    Args:
        category_code (str): NTEE major group code (A-Z)
        
    Query Parameters:
        limit (int): Maximum number of results (default 20, max 100)
        
    Returns:
        JSON response with organizations in the category
    """
    try:
        # Validate category code
        if not category_code or len(category_code) != 1 or not category_code.isalpha():
            return jsonify({'error': 'Invalid category code. Must be a single letter A-Z.'}), 400
        
        limit = min(int(request.args.get('limit', 20)), 100)
        
        organizations = org_service.get_organizations_by_category(
            category_code.upper(), 
            limit
        )
        
        org_list = [org.to_dict() for org in organizations]
        
        return jsonify({
            'data': org_list,
            'count': len(org_list),
            'category': category_code.upper()
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error getting organizations by category {category_code}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@organizations_bp.route('/favorites', methods=['GET'])
@jwt_required()
def get_user_favorites():
    """
    Get user's favorite organizations (requires authentication)
    
    Returns:
        JSON response with user's favorite organizations
    """
    try:
        user_id = get_jwt_identity()
        
        # This would require a user favorites table in the database
        # For now, return empty list as placeholder
        # TODO: Implement user favorites functionality
        
        return jsonify({
            'data': [],
            'count': 0,
            'message': 'User favorites feature coming soon'
        })
        
    except Exception as e:
        logger.error(f"Error getting user favorites: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@organizations_bp.route('/favorites/<ein>', methods=['POST'])
@jwt_required()
def add_favorite_organization(ein):
    """
    Add organization to user's favorites (requires authentication)
    
    Args:
        ein (str): Employer Identification Number
        
    Returns:
        JSON response confirming addition
    """
    try:
        user_id = get_jwt_identity()
        
        # Validate EIN format
        clean_ein = ein.replace('-', '').replace(' ', '')
        if not clean_ein.isdigit() or len(clean_ein) != 9:
            return jsonify({'error': 'Invalid EIN format. Must be 9 digits.'}), 400
        
        # Verify organization exists
        organization = org_service.get_organization_by_ein(clean_ein)
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        # TODO: Implement user favorites functionality
        # This would add the organization to user's favorites table
        
        return jsonify({
            'message': 'Organization added to favorites',
            'organization': organization.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error adding favorite organization {ein}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@organizations_bp.route('/favorites/<ein>', methods=['DELETE'])
@jwt_required()
def remove_favorite_organization(ein):
    """
    Remove organization from user's favorites (requires authentication)
    
    Args:
        ein (str): Employer Identification Number
        
    Returns:
        JSON response confirming removal
    """
    try:
        user_id = get_jwt_identity()
        
        # Validate EIN format
        clean_ein = ein.replace('-', '').replace(' ', '')
        if not clean_ein.isdigit() or len(clean_ein) != 9:
            return jsonify({'error': 'Invalid EIN format. Must be 9 digits.'}), 400
        
        # TODO: Implement user favorites functionality
        # This would remove the organization from user's favorites table
        
        return jsonify({
            'message': 'Organization removed from favorites'
        })
        
    except Exception as e:
        logger.error(f"Error removing favorite organization {ein}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@organizations_bp.route('/test', methods=['GET'])
def test_api_connection():
    """
    Test the CharityAPI connection and return status
    
    Returns:
        JSON response with connection test results
    """
    try:
        test_results = org_service.test_api_connection()
        
        return jsonify(test_results)
        
    except Exception as e:
        logger.error(f"Error testing API connection: {str(e)}")
        return jsonify({
            'connected': False,
            'error': str(e)
        }), 500

# Error handlers for the blueprint
@organizations_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@organizations_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@organizations_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

