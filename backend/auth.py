import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from typing import Optional
import json
from urllib.parse import urlparse, urlunparse

class GoogleAuth:
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        # Get configured backend port
        backend_port = os.getenv('BACKEND_PORT', '8000')
        
        # Get redirect URI from env or default
        default_redirect = f'http://localhost:{backend_port}/auth/google/callback'
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', default_redirect)
        
        # Auto-adjust port in redirect_uri if BACKEND_PORT is set and differs from the URI
        if os.getenv('BACKEND_PORT'):
            try:
                parsed = urlparse(self.redirect_uri)
                if parsed.port and str(parsed.port) != backend_port:
                    # Replace port in netloc
                    new_netloc = parsed.netloc.replace(f":{parsed.port}", f":{backend_port}")
                    self.redirect_uri = urlunparse(parsed._replace(netloc=new_netloc))
            except Exception:
                pass # Keep original if parsing fails

        self.scopes = ['https://www.googleapis.com/auth/contacts.readonly']
        self.credentials: Optional[Credentials] = None
        
        if not self.client_id or not self.client_secret:
            raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")

    def get_auth_url(self) -> str:
        """Generate Google OAuth authorization URL"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return authorization_url

    def exchange_code(self, code: str) -> Credentials:
        """Exchange authorization code for credentials"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        flow.fetch_token(code=code)
        return flow.credentials

    def store_credentials(self, credentials: Credentials):
        """Store credentials in memory (for demo purposes)"""
        self.credentials = credentials

    def get_credentials(self) -> Optional[Credentials]:
        """Get stored credentials"""
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            self.credentials.refresh(Request())
        return self.credentials

    def has_credentials(self) -> bool:
        """Check if valid credentials are available"""
        return self.credentials is not None and self.credentials.valid
