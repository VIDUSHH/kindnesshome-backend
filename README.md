# KindnessHome Backend API

A Flask-based REST API for the KindnessHome donation platform, providing user authentication, OAuth integration, and organization management.

## Features

- 🔐 **Google OAuth Authentication**
- 👤 **User Management & JWT Tokens**
- 🏢 **Organization Directory**
- 🔒 **Secure API Endpoints**
- 📊 **SQLite Database (Production-ready)**

## Quick Deploy

### Deploy to Railway (Recommended)

1. **Fork this repository**
2. **Go to [Railway](https://railway.app/)**
3. **Click "Deploy from GitHub repo"**
4. **Select this repository**
5. **Add environment variables** (see below)
6. **Deploy!**

### Deploy to Render

1. **Fork this repository**
2. **Go to [Render](https://render.com/)**
3. **Click "New Web Service"**
4. **Connect your GitHub repository**
5. **Set build command:** `pip install -r requirements.txt`
6. **Set start command:** `gunicorn src.main:app`
7. **Add environment variables**

### Deploy to Vercel

1. **Fork this repository**
2. **Go to [Vercel](https://vercel.com/)**
3. **Import your GitHub repository**
4. **Configure as Python project**
5. **Add environment variables**

## Environment Variables

Create a `.env` file or add these to your deployment platform:

```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://your-backend-url.com/api/oauth/google/callback
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
```

## Google OAuth Setup

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Create a new project or select existing**
3. **Enable Google+ API**
4. **Create OAuth 2.0 credentials**
5. **Add your backend URL to authorized redirect URIs:**
   - `https://your-backend-url.com/api/oauth/google/callback`

## API Endpoints

### Authentication
- `GET /api/oauth/google/login` - Initiate Google OAuth
- `GET /api/oauth/google/callback` - Handle OAuth callback

### Organizations
- `GET /api/organizations` - List verified organizations
- `GET /api/health` - Health check

### Testing
- `GET /` - API status
- `GET /api/oauth/test` - OAuth configuration test

## Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd kindnesshome-backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create .env file**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

4. **Run the application**
   ```bash
   python src/main.py
   ```

5. **Test the API**
   ```bash
   curl http://localhost:5000/api/health
   ```

## Project Structure

```
kindnesshome-backend/
├── src/
│   ├── main.py              # Main Flask application
│   ├── routes/              # API route handlers
│   └── models/              # Database models
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── README.md               # This file
└── runtime.txt             # Python version (for some platforms)
```

## Frontend Integration

This backend is designed to work with the KindnessHome React frontend. After deployment:

1. **Update frontend OAuth configuration**
2. **Update CORS settings** if needed
3. **Test complete OAuth flow**

## Support

For issues or questions about deployment, please check the platform-specific documentation:
- [Railway Docs](https://docs.railway.app/)
- [Render Docs](https://render.com/docs)
- [Vercel Docs](https://vercel.com/docs)

## License

MIT License - see LICENSE file for details.

