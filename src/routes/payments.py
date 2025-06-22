import os
import stripe
import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.database import db
from src.models.donation import Donation, PaymentMethod
from src.models.user import User
from src.models.organization import Organization
import uuid
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/create-payment-intent', methods=['POST'])
@jwt_required()
def create_payment_intent():
    """Create a Stripe payment intent for donation"""
    try:
        data = request.get_json()
        amount = data.get('amount')  # Amount in cents
        organization_id = data.get('organization_id')
        currency = data.get('currency', 'usd')
        
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        organization = Organization.query.get(organization_id)
        
        if not user or not organization:
            return jsonify({'error': 'User or organization not found'}), 404
        
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            metadata={
                'user_id': user_id,
                'organization_id': organization_id,
                'user_email': user.email,
                'organization_name': organization.name
            }
        )
        
        return jsonify({
            'client_secret': intent.client_secret,
            'payment_intent_id': intent.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payments_bp.route('/confirm-donation', methods=['POST'])
@jwt_required()
def confirm_donation():
    """Confirm donation after successful payment"""
    try:
        data = request.get_json()
        payment_intent_id = data.get('payment_intent_id')
        organization_id = data.get('organization_id')
        amount = data.get('amount')
        dedication = data.get('dedication', '')
        anonymous = data.get('anonymous', False)
        
        user_id = get_jwt_identity()
        
        # Verify payment intent with Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status != 'succeeded':
            return jsonify({'error': 'Payment not completed'}), 400
        
        # Create donation record
        donation = Donation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            organization_id=organization_id,
            amount=amount / 100,  # Convert from cents to dollars
            currency='USD',
            payment_method='stripe',
            payment_status='completed',
            stripe_payment_intent_id=payment_intent_id,
            dedication=dedication,
            anonymous=anonymous,
            created_at=datetime.utcnow()
        )
        
        db.session.add(donation)
        db.session.commit()
        
        # Send tax receipt email
        send_tax_receipt(donation)
        
        return jsonify({
            'success': True,
            'donation_id': donation.id,
            'message': 'Donation completed successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payments_bp.route('/create-paypal-order', methods=['POST'])
@jwt_required()
def create_paypal_order():
    """Create PayPal order for donation"""
    try:
        data = request.get_json()
        amount = data.get('amount')  # Amount in dollars
        organization_id = data.get('organization_id')
        
        user_id = get_jwt_identity()
        organization = Organization.query.get(organization_id)
        
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        # Get PayPal access token
        access_token = get_paypal_access_token()
        
        # Create PayPal order
        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": str(amount)
                },
                "description": f"Donation to {organization.name}"
            }],
            "application_context": {
                "return_url": "http://localhost:3000/donation-success",
                "cancel_url": "http://localhost:3000/donation-cancel"
            }
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        paypal_api_url = "https://api.sandbox.paypal.com/v2/checkout/orders"
        if os.getenv('PAYPAL_MODE') == 'live':
            paypal_api_url = "https://api.paypal.com/v2/checkout/orders"
        
        response = requests.post(paypal_api_url, json=order_data, headers=headers)
        
        if response.status_code == 201:
            order = response.json()
            return jsonify({
                'order_id': order['id'],
                'approval_url': next(link['href'] for link in order['links'] if link['rel'] == 'approve')
            })
        else:
            return jsonify({'error': 'Failed to create PayPal order'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payments_bp.route('/capture-paypal-order', methods=['POST'])
@jwt_required()
def capture_paypal_order():
    """Capture PayPal order and create donation record"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        organization_id = data.get('organization_id')
        dedication = data.get('dedication', '')
        anonymous = data.get('anonymous', False)
        
        user_id = get_jwt_identity()
        
        # Get PayPal access token
        access_token = get_paypal_access_token()
        
        # Capture PayPal order
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        paypal_api_url = f"https://api.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"
        if os.getenv('PAYPAL_MODE') == 'live':
            paypal_api_url = f"https://api.paypal.com/v2/checkout/orders/{order_id}/capture"
        
        response = requests.post(paypal_api_url, headers=headers)
        
        if response.status_code == 201:
            capture_data = response.json()
            amount = float(capture_data['purchase_units'][0]['payments']['captures'][0]['amount']['value'])
            
            # Create donation record
            donation = Donation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                organization_id=organization_id,
                amount=amount,
                currency='USD',
                payment_method='paypal',
                payment_status='completed',
                paypal_order_id=order_id,
                dedication=dedication,
                anonymous=anonymous,
                created_at=datetime.utcnow()
            )
            
            db.session.add(donation)
            db.session.commit()
            
            # Send tax receipt email
            send_tax_receipt(donation)
            
            return jsonify({
                'success': True,
                'donation_id': donation.id,
                'message': 'Donation completed successfully'
            })
        else:
            return jsonify({'error': 'Failed to capture PayPal order'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payments_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        # Update donation status if needed
        print(f"Payment succeeded: {payment_intent['id']}")
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        # Handle failed payment
        print(f"Payment failed: {payment_intent['id']}")
    
    return jsonify({'status': 'success'})

@payments_bp.route('/save-payment-method', methods=['POST'])
@jwt_required()
def save_payment_method():
    """Save payment method for future use"""
    try:
        data = request.get_json()
        payment_method_id = data.get('payment_method_id')
        card_last4 = data.get('card_last4')
        card_brand = data.get('card_brand')
        exp_month = data.get('exp_month')
        exp_year = data.get('exp_year')
        
        user_id = get_jwt_identity()
        
        # Create payment method record
        payment_method = PaymentMethod(
            id=str(uuid.uuid4()),
            user_id=user_id,
            stripe_payment_method_id=payment_method_id,
            type='card',
            card_last4=card_last4,
            card_brand=card_brand,
            expiry_month=exp_month,
            expiry_year=exp_year,
            is_default=False,
            created_at=datetime.utcnow()
        )
        
        db.session.add(payment_method)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'payment_method_id': payment_method.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_paypal_access_token():
    """Get PayPal access token"""
    client_id = os.getenv('PAYPAL_CLIENT_ID')
    client_secret = os.getenv('PAYPAL_CLIENT_SECRET')
    
    auth_url = "https://api.sandbox.paypal.com/v1/oauth2/token"
    if os.getenv('PAYPAL_MODE') == 'live':
        auth_url = "https://api.paypal.com/v1/oauth2/token"
    
    headers = {
        'Accept': 'application/json',
        'Accept-Language': 'en_US',
    }
    
    data = 'grant_type=client_credentials'
    
    response = requests.post(
        auth_url,
        headers=headers,
        data=data,
        auth=(client_id, client_secret)
    )
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception('Failed to get PayPal access token')

def send_tax_receipt(donation):
    """Send tax receipt email to donor"""
    try:
        user = User.query.get(donation.user_id)
        organization = Organization.query.get(donation.organization_id)
        
        if not user or not organization:
            return
        
        # Create email content
        subject = f"Tax Receipt for Your Donation to {organization.name}"
        
        html_content = f"""
        <html>
        <body>
            <h2>Tax Receipt</h2>
            <p>Dear {user.first_name} {user.last_name},</p>
            
            <p>Thank you for your generous donation to {organization.name}.</p>
            
            <h3>Donation Details:</h3>
            <ul>
                <li><strong>Donation ID:</strong> {donation.id}</li>
                <li><strong>Amount:</strong> ${donation.amount:.2f}</li>
                <li><strong>Date:</strong> {donation.created_at.strftime('%B %d, %Y')}</li>
                <li><strong>Organization:</strong> {organization.name}</li>
                <li><strong>EIN:</strong> {organization.ein}</li>
                <li><strong>Payment Method:</strong> {donation.payment_method.title()}</li>
            </ul>
            
            <p>This donation is tax-deductible to the extent allowed by law. Please consult your tax advisor for specific guidance.</p>
            
            <p>Thank you for supporting {organization.name} and making a difference in the community.</p>
            
            <p>Best regards,<br>
            The DonateHub Team</p>
        </body>
        </html>
        """
        
        # Send email (placeholder - would need actual SMTP configuration)
        print(f"Tax receipt sent to {user.email} for donation {donation.id}")
        
    except Exception as e:
        print(f"Failed to send tax receipt: {str(e)}")

