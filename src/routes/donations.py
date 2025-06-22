from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.database import db
from src.models.donation import Donation, MatchingGift
from src.models.organization import Organization
from src.models.user import User
from decimal import Decimal
import uuid

donations_bp = Blueprint('donations', __name__)

@donations_bp.route('', methods=['POST'])
@jwt_required()
def create_donation():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['organization_id', 'amount']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate organization exists
        organization = Organization.query.get(data['organization_id'])
        if not organization or not organization.is_active:
            return jsonify({'error': 'Organization not found'}), 404
        
        # Validate amount
        try:
            amount = Decimal(str(data['amount']))
            if amount <= 0:
                return jsonify({'error': 'Amount must be greater than 0'}), 400
        except:
            return jsonify({'error': 'Invalid amount format'}), 400
        
        # Calculate fees (simplified calculation)
        transaction_fee = amount * Decimal('0.029') + Decimal('0.30')  # 2.9% + $0.30
        platform_fee = amount * Decimal('0.01') if data.get('cover_fees', False) else Decimal('0')  # 1% platform fee
        net_amount = amount - transaction_fee - platform_fee
        
        donation = Donation(
            user_id=current_user_id,
            organization_id=data['organization_id'],
            campaign_id=data.get('campaign_id'),
            amount=amount,
            currency=data.get('currency', 'USD'),
            payment_method=data.get('payment_method', 'stripe'),
            payment_processor_id=str(uuid.uuid4()),  # Would be actual processor ID
            payment_status='pending',
            transaction_fee=transaction_fee,
            platform_fee=platform_fee,
            net_amount=net_amount,
            is_recurring=data.get('is_recurring', False),
            recurring_interval=data.get('recurring_interval'),
            is_anonymous=data.get('is_anonymous', False),
            donor_message=data.get('donor_message'),
            matching_gift_eligible=data.get('matching_gift_eligible', False)
        )
        
        # Handle dedication
        if 'dedication' in data:
            donation.set_dedication(data['dedication'])
        
        # Handle metadata
        if 'metadata' in data:
            donation.set_metadata(data['metadata'])
        
        db.session.add(donation)
        
        # If this is for a campaign, update the raised amount
        if data.get('campaign_id'):
            from src.models.campaign import Campaign
            campaign = Campaign.query.get(data['campaign_id'])
            if campaign:
                campaign.raised_amount = (campaign.raised_amount or 0) + amount
        
        db.session.commit()
        
        # In production, this would integrate with actual payment processors
        # For now, we'll simulate successful payment
        donation.payment_status = 'completed'
        db.session.commit()
        
        return jsonify({
            'message': 'Donation created successfully',
            'donation': donation.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@donations_bp.route('/<donation_id>', methods=['GET'])
@jwt_required()
def get_donation(donation_id):
    try:
        current_user_id = get_jwt_identity()
        
        donation = Donation.query.filter_by(
            id=donation_id,
            user_id=current_user_id
        ).first()
        
        if not donation:
            return jsonify({'error': 'Donation not found'}), 404
        
        return jsonify({
            'donation': donation.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@donations_bp.route('/<donation_id>/cancel', methods=['PUT'])
@jwt_required()
def cancel_recurring_donation(donation_id):
    try:
        current_user_id = get_jwt_identity()
        
        donation = Donation.query.filter_by(
            id=donation_id,
            user_id=current_user_id,
            is_recurring=True
        ).first()
        
        if not donation:
            return jsonify({'error': 'Recurring donation not found'}), 404
        
        if donation.payment_status == 'cancelled':
            return jsonify({'error': 'Donation already cancelled'}), 400
        
        # In production, this would cancel the subscription with the payment processor
        donation.payment_status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            'message': 'Recurring donation cancelled successfully',
            'donation': donation.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@donations_bp.route('/<donation_id>/matching-gift', methods=['POST'])
@jwt_required()
def create_matching_gift(donation_id):
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        donation = Donation.query.filter_by(
            id=donation_id,
            user_id=current_user_id
        ).first()
        
        if not donation:
            return jsonify({'error': 'Donation not found'}), 404
        
        if not donation.matching_gift_eligible:
            return jsonify({'error': 'Donation is not eligible for matching gifts'}), 400
        
        # Validate required fields
        required_fields = ['employer_name', 'employee_email']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Calculate match amount (default 1:1 ratio)
        match_ratio = Decimal(str(data.get('match_ratio', '1.0')))
        match_amount = donation.amount * match_ratio
        
        matching_gift = MatchingGift(
            donation_id=donation_id,
            employer_name=data['employer_name'],
            employer_ein=data.get('employer_ein'),
            employee_email=data['employee_email'],
            match_ratio=match_ratio,
            match_amount=match_amount,
            status='pending'
        )
        
        if 'metadata' in data:
            matching_gift.set_metadata(data['metadata'])
        
        db.session.add(matching_gift)
        
        # Update donation matching status
        donation.matching_gift_status = 'submitted'
        donation.matching_gift_amount = match_amount
        
        db.session.commit()
        
        return jsonify({
            'message': 'Matching gift request created successfully',
            'matching_gift': matching_gift.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@donations_bp.route('/<donation_id>/receipt', methods=['GET'])
@jwt_required()
def get_donation_receipt(donation_id):
    try:
        current_user_id = get_jwt_identity()
        
        donation = Donation.query.filter_by(
            id=donation_id,
            user_id=current_user_id
        ).first()
        
        if not donation:
            return jsonify({'error': 'Donation not found'}), 404
        
        if donation.payment_status != 'completed':
            return jsonify({'error': 'Receipt not available for incomplete donations'}), 400
        
        # Get related data
        user = User.query.get(current_user_id)
        organization = Organization.query.get(donation.organization_id)
        
        receipt_data = {
            'donation': donation.to_dict(),
            'donor': {
                'name': f"{user.first_name} {user.last_name}",
                'email': user.email,
                'address': user.get_address()
            },
            'organization': {
                'name': organization.name,
                'ein': organization.ein,
                'address': organization.get_address(),
                'tax_exempt_status': organization.tax_exempt_status
            },
            'receipt_number': f"RCP-{donation.id[:8].upper()}",
            'tax_deductible': organization.deductibility_status == 'Deductible',
            'generated_at': db.func.now()
        }
        
        # Mark receipt as sent
        if not donation.tax_receipt_sent:
            donation.tax_receipt_sent = True
            db.session.commit()
        
        return jsonify({
            'receipt': receipt_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@donations_bp.route('/bulk', methods=['POST'])
@jwt_required()
def create_bulk_donations():
    try:
        # This would be admin-only in production
        data = request.get_json()
        donations_data = data.get('donations', [])
        
        if not donations_data:
            return jsonify({'error': 'No donations provided'}), 400
        
        created_donations = []
        
        for donation_data in donations_data:
            # Validate required fields for each donation
            required_fields = ['user_id', 'organization_id', 'amount']
            for field in required_fields:
                if not donation_data.get(field):
                    return jsonify({'error': f'{field} is required for all donations'}), 400
            
            amount = Decimal(str(donation_data['amount']))
            transaction_fee = amount * Decimal('0.029') + Decimal('0.30')
            platform_fee = amount * Decimal('0.01') if donation_data.get('cover_fees', False) else Decimal('0')
            net_amount = amount - transaction_fee - platform_fee
            
            donation = Donation(
                user_id=donation_data['user_id'],
                organization_id=donation_data['organization_id'],
                amount=amount,
                currency=donation_data.get('currency', 'USD'),
                payment_method=donation_data.get('payment_method', 'bulk_import'),
                payment_processor_id=str(uuid.uuid4()),
                payment_status='completed',
                transaction_fee=transaction_fee,
                platform_fee=platform_fee,
                net_amount=net_amount,
                is_anonymous=donation_data.get('is_anonymous', False)
            )
            
            db.session.add(donation)
            created_donations.append(donation)
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_donations)} donations created successfully',
            'donations': [donation.to_dict() for donation in created_donations]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

