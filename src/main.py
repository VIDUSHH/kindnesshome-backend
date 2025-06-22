import os
from flask import Flask, jsonify, redirect, session, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token
import requests
import logging

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'kindnesshome-secret-key-2025')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'kindnesshome-jwt-secret-2025')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kindnesshome.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app)
    
    # OAuth Configuration
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', "222142306503-nin1nh3q36f4sak91b5doseko86jorjr.apps.googleusercontent.com")
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', "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")
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', "https://kindnesshome-backend.onrender.com/api/oauth/google/callback")
    
    # User model
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(120), unique=True, nullable=False)
        first_name = db.Column(db.String(50))
        last_name = db.Column(db.String(50))
        google_id = db.Column(db.String(100))
        profile_picture_url = db.Column(db.String(200))
        is_email_verified = db.Column(db.Boolean, default=False)
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
        
        def to_dict(self):
            return {
                'id': self.id,
                'email': self.email,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'profile_picture_url': self.profile_picture_url,
                'is_email_verified': self.is_email_verified
            }
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # OAuth Routes
    @app.route('/api/oauth/google/login')
    def google_login():
        """Initiate Google OAuth login"""
        try:
            google_auth_url = "https://accounts.google.com/o/oauth2/auth"
            params = {
                'client_id': GOOGLE_CLIENT_ID,
                'redirect_uri': GOOGLE_REDIRECT_URI,
                'scope': 'openid email profile',
                'response_type': 'code',
                'access_type': 'offline',
                'prompt': 'consent'
            }
            
            auth_url = f"{google_auth_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
            return redirect(auth_url)
            
        except Exception as e:
            logging.error(f"Error initiating Google login: {str(e)}")
            return jsonify({'error': 'Failed to initiate Google login'}), 500

    @app.route('/api/oauth/google/callback')
    def google_callback():
        """Handle Google OAuth callback"""
        try:
            code = request.args.get('code')
            if not code:
                return jsonify({'error': 'Authorization code not provided'}), 400
            
            # Exchange code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': GOOGLE_REDIRECT_URI
            }
            
            token_response = requests.post(token_url, data=token_data)
            token_json = token_response.json()
            
            if 'access_token' not in token_json:
                return jsonify({'error': 'Failed to get access token', 'details': token_json}), 400
            
            # Get user info from Google
            user_info_url = f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={token_json['access_token']}"
            user_response = requests.get(user_info_url)
            user_info = user_response.json()
            
            if 'email' not in user_info:
                return jsonify({'error': 'Failed to get user email from Google'}), 400
            
            # Extract user data
            email = user_info.get('email')
            name = user_info.get('name', '')
            google_id = user_info.get('id')
            profile_picture = user_info.get('picture')
            
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
            
            # Return success response with redirect to frontend
            return f"""
            <html>
            <head><title>Login Successful - KindnessHome</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2>🎉 Login Successful!</h2>
                <p>Welcome <strong>{user.first_name}</strong>! You have successfully logged in with Google.</p>
                <p>Redirecting to KindnessHome...</p>
                <script>
                    // Store tokens in localStorage and redirect
                    localStorage.setItem('access_token', '{access_token}');
                    localStorage.setItem('refresh_token', '{refresh_token}');
                    localStorage.setItem('user', JSON.stringify({user.to_dict()}));
                    setTimeout(() => {{
                        window.location.href = 'https://atqnnjst.manus.space';
                    }}, 2000);
                </script>
            </body>
            </html>
            """
            
        except Exception as e:
            logging.error(f"Error in Google callback: {str(e)}")
            return f"""
            <html>
            <head><title>Login Error - KindnessHome</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2>❌ Login Failed</h2>
                <p>Sorry, there was an error during Google login.</p>
                <p>Error: {str(e)}</p>
                <a href="https://atqnnjst.manus.space">Return to KindnessHome</a>
            </body>
            </html>
            """
    
    # Simple routes for deployment testing
    @app.route('/')
    def home():
        return jsonify({
            "message": "KindnessHome API is running!",
            "status": "success",
            "version": "1.0.0",
            "oauth_ready": True
        })
    
    @app.route('/api/organizations')
    def organizations():
        return jsonify({
            "organizations": [
                {
                    "id": 1,
                    "name": "American Red Cross",
                    "ein": "53-0196605",
                    "category": "Emergency Relief",
                    "rating": 4.8,
                    "location": "Washington, DC",
                    "verified": True
                },
                {
                    "id": 2,
                    "name": "Feeding America",
                    "ein": "36-3673599", 
                    "category": "Hunger Relief",
                    "rating": 4.7,
                    "location": "Chicago, IL",
                    "verified": True
                }
            ],
            "total": 2,
            "status": "success"
        })
    
    @app.route('/api/health')
    def health():
        return jsonify({"status": "healthy", "service": "KindnessHome API"})
    
    @app.route('/api/oauth/test')
    def oauth_test():
        return jsonify({
            "message": "OAuth endpoints ready",
            "google_configured": True,
            "google_client_id": GOOGLE_CLIENT_ID[:20] + "...",
            "redirect_uris": {
                "google": GOOGLE_REDIRECT_URI
            }
        })
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)

