import os
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, request, jsonify, redirect, url_for, session
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from src.models.user import User
from src.models.database import db
import logging

oauth_bp = Blueprint('oauth', __name__, url_prefix='/api/oauth')

# Initialize OAuth
oauth = OAuth()

def init_oauth(app):
    """Initialize OAuth with Flask app"""
    oauth.init_app(app)
    
    # Google OAuth
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    
    # Facebook OAuth
    oauth.register(
        name='facebook',
        client_id=os.getenv('FACEBOOK_CLIENT_ID'),
        client_secret=os.getenv('FACEBOOK_CLIENT_SECRET'),
        access_token_url='https://graph.facebook.com/oauth/access_token',
        authorize_url='https://www.facebook.com/dialog/oauth',
        api_base_url='https://graph.facebook.com/',
        client_kwargs={'scope': 'email'},
    )

@oauth_bp.route('/google/login')
def google_login():
    """Initiate Google OAuth login"""
    try:
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI') or url_for('oauth.google_callback', _external=True)
        return oauth.google.authorize_redirect(redirect_uri)
    except Exception as e:
        logging.error(f"Error initiating Google login: {str(e)}")
        return jsonify({'error': 'Failed to initiate Google login'}), 500

@oauth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            return jsonify({'error': 'Failed to get user information from Google'}), 400
        
        # Extract user data
        email = user_info.get('email')
        name = user_info.get('name')
        google_id = user_info.get('sub')
        profile_picture = user_info.get('picture')
        
        if not email:
            return jsonify({'error': 'Email not provided by Google'}), 400
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Update existing user with Google info
            user.google_id = google_id
            user.profile_picture_url = profile_picture
            if not user.first_name and name:
                names = name.split(' ', 1)
                user.first_name = names[0]
                user.last_name = names[1] if len(names) > 1 else ''
        else:
            # Create new user
            names = name.split(' ', 1) if name else ['', '']
            user = User(
                email=email,
                first_name=names[0],
                last_name=names[1] if len(names) > 1 else '',
                google_id=google_id,
                profile_picture_url=profile_picture,
                is_email_verified=True  # Google emails are pre-verified
            )
            db.session.add(user)
        
        db.session.commit()
        
        # Create JWT tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # Return success response (in production, redirect to frontend)
        return jsonify({
            'message': 'Google login successful',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        })
        
    except Exception as e:
        logging.error(f"Error in Google callback: {str(e)}")
        return jsonify({'error': 'Google login failed'}), 500

@oauth_bp.route('/facebook/login')
def facebook_login():
    """Initiate Facebook OAuth login"""
    try:
        redirect_uri = os.getenv('FACEBOOK_REDIRECT_URI') or url_for('oauth.facebook_callback', _external=True)
        return oauth.facebook.authorize_redirect(redirect_uri)
    except Exception as e:
        logging.error(f"Error initiating Facebook login: {str(e)}")
        return jsonify({'error': 'Failed to initiate Facebook login'}), 500

@oauth_bp.route('/facebook/callback')
def facebook_callback():
    """Handle Facebook OAuth callback"""
    try:
        token = oauth.facebook.authorize_access_token()
        
        # Get user info from Facebook Graph API
        resp = oauth.facebook.get('me?fields=id,name,email,picture')
        user_info = resp.json()
        
        # Extract user data
        email = user_info.get('email')
        name = user_info.get('name')
        facebook_id = user_info.get('id')
        profile_picture = user_info.get('picture', {}).get('data', {}).get('url')
        
        if not email:
            return jsonify({'error': 'Email not provided by Facebook'}), 400
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Update existing user with Facebook info
            user.facebook_id = facebook_id
            user.profile_picture_url = profile_picture
            if not user.first_name and name:
                names = name.split(' ', 1)
                user.first_name = names[0]
                user.last_name = names[1] if len(names) > 1 else ''
        else:
            # Create new user
            names = name.split(' ', 1) if name else ['', '']
            user = User(
                email=email,
                first_name=names[0],
                last_name=names[1] if len(names) > 1 else '',
                facebook_id=facebook_id,
                profile_picture_url=profile_picture,
                is_email_verified=True  # Facebook emails are pre-verified
            )
            db.session.add(user)
        
        db.session.commit()
        
        # Create JWT tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # Return success response (in production, redirect to frontend)
        return jsonify({
            'message': 'Facebook login successful',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        })
        
    except Exception as e:
        logging.error(f"Error in Facebook callback: {str(e)}")
        return jsonify({'error': 'Facebook login failed'}), 500

@oauth_bp.route('/link-account', methods=['POST'])
@jwt_required()
def link_social_account():
    """Link a social account to existing user account"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        provider = data.get('provider')  # 'google' or 'facebook'
        
        if provider == 'google':
            redirect_uri = url_for('oauth.google_link_callback', _external=True)
            return oauth.google.authorize_redirect(redirect_uri)
        elif provider == 'facebook':
            redirect_uri = url_for('oauth.facebook_link_callback', _external=True)
            return oauth.facebook.authorize_redirect(redirect_uri)
        else:
            return jsonify({'error': 'Invalid provider'}), 400
            
    except Exception as e:
        logging.error(f"Error linking social account: {str(e)}")
        return jsonify({'error': 'Failed to link social account'}), 500

@oauth_bp.route('/unlink-account', methods=['POST'])
@jwt_required()
def unlink_social_account():
    """Unlink a social account from user account"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        provider = data.get('provider')  # 'google' or 'facebook'
        
        if provider == 'google':
            user.google_id = None
        elif provider == 'facebook':
            user.facebook_id = None
        else:
            return jsonify({'error': 'Invalid provider'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': f'{provider.title()} account unlinked successfully',
            'user': user.to_dict()
        })
        
    except Exception as e:
        logging.error(f"Error unlinking social account: {str(e)}")
        return jsonify({'error': 'Failed to unlink social account'}), 500

@oauth_bp.route('/status')
@jwt_required()
def oauth_status():
    """Get OAuth connection status for current user"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'google_connected': bool(user.google_id),
            'facebook_connected': bool(user.facebook_id),
            'profile_picture_url': user.profile_picture_url
        })
        
    except Exception as e:
        logging.error(f"Error getting OAuth status: {str(e)}")
        return jsonify({'error': 'Failed to get OAuth status'}), 500

