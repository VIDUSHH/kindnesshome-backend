from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.database import db
from src.models.user import User
from src.models.donation import Donation, PaymentMethod

users_bp = Blueprint('users', __name__)

@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'phone', 'date_of_birth', 'profile_image_url']
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        
        # Handle address update
        if 'address' in data:
            user.set_address(data['address'])
        
        # Handle preferences update
        if 'preferences' in data:
            user.set_preferences(data['preferences'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/donations', methods=['GET'])
@jwt_required()
def get_user_donations():
    try:
        current_user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        donations = Donation.query.filter_by(user_id=current_user_id)\
                                 .order_by(Donation.created_at.desc())\
                                 .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'donations': [donation.to_dict() for donation in donations.items],
            'total': donations.total,
            'pages': donations.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/payment-methods', methods=['GET'])
@jwt_required()
def get_payment_methods():
    try:
        current_user_id = get_jwt_identity()
        
        payment_methods = PaymentMethod.query.filter_by(
            user_id=current_user_id, 
            is_active=True
        ).order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc()).all()
        
        return jsonify({
            'payment_methods': [pm.to_dict() for pm in payment_methods]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/payment-methods', methods=['POST'])
@jwt_required()
def add_payment_method():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['type', 'provider', 'provider_payment_method_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # If this is set as default, unset other default payment methods
        if data.get('is_default', False):
            PaymentMethod.query.filter_by(user_id=current_user_id, is_default=True)\
                              .update({'is_default': False})
        
        payment_method = PaymentMethod(
            user_id=current_user_id,
            type=data['type'],
            provider=data['provider'],
            provider_payment_method_id=data['provider_payment_method_id'],
            last_four=data.get('last_four'),
            brand=data.get('brand'),
            expiry_month=data.get('expiry_month'),
            expiry_year=data.get('expiry_year'),
            is_default=data.get('is_default', False)
        )
        
        if 'metadata' in data:
            payment_method.set_metadata(data['metadata'])
        
        db.session.add(payment_method)
        db.session.commit()
        
        return jsonify({
            'message': 'Payment method added successfully',
            'payment_method': payment_method.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/payment-methods/<payment_method_id>', methods=['DELETE'])
@jwt_required()
def delete_payment_method(payment_method_id):
    try:
        current_user_id = get_jwt_identity()
        
        payment_method = PaymentMethod.query.filter_by(
            id=payment_method_id,
            user_id=current_user_id
        ).first()
        
        if not payment_method:
            return jsonify({'error': 'Payment method not found'}), 404
        
        payment_method.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Payment method deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/tax-receipts', methods=['GET'])
@jwt_required()
def get_tax_receipts():
    try:
        current_user_id = get_jwt_identity()
        year = request.args.get('year', type=int)
        
        query = Donation.query.filter_by(user_id=current_user_id, payment_status='completed')
        
        if year:
            from datetime import datetime
            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31, 23, 59, 59)
            query = query.filter(Donation.created_at.between(start_date, end_date))
        
        donations = query.order_by(Donation.created_at.desc()).all()
        
        total_donated = sum(float(donation.amount) for donation in donations)
        
        return jsonify({
            'donations': [donation.to_dict() for donation in donations],
            'total_donated': total_donated,
            'year': year,
            'count': len(donations)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

