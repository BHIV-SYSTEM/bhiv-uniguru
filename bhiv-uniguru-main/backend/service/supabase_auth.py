"""
Supabase authentication service for UniGuru.
Handles both Google OAuth and email/password authentication.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Any, Optional

try:
    from supabase import create_client, Client
except ImportError:  # pragma: no cover - exercised only in slim/no-auth runtimes
    create_client = None
    Client = Any  # type: ignore[misc, assignment]

try:
    from passlib.context import CryptContext
except ImportError:  # pragma: no cover - exercised only in slim/no-auth runtimes
    CryptContext = None  # type: ignore[assignment]

logger = logging.getLogger("uniguru.service.supabase_auth")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") if CryptContext else None


class SupabaseAuthService:
    """Manages user authentication with Supabase."""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
        self.enabled = bool(create_client and self.supabase_url and self.supabase_key)
        
        if self.enabled:
            try:
                self.client: Client = create_client(self.supabase_url, self.supabase_key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.enabled = False
                self.client = None
        else:
            self.client = None
            if create_client is None:
                logger.warning("Supabase package unavailable; Supabase authentication disabled")
            else:
                logger.warning("Supabase not configured (missing SUPABASE_URL or SUPABASE_ANON_KEY)")
    
    def signup_with_email(self, email: str, password: str, name: str) -> Dict[str, Any]:
        """Sign up a new user with email and password."""
        if not self.enabled:
            raise Exception("Supabase authentication is not configured")
        
        try:
            # Sign up user in Supabase Auth
            auth_response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "name": name
                    }
                }
            })
            
            if not auth_response.user:
                raise Exception("Failed to create user account")
            
            user = auth_response.user
            session = auth_response.session
            
            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": name
                },
                "token": session.access_token if session else None,
                "requires_email_verification": session is None,
                "message": "Account created successfully"
            }
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Signup failed: {error_msg}")
            
            # Parse common Supabase errors
            lower = error_msg.lower()
            if "rate limit" in lower or "email rate limit exceeded" in lower:
                raise Exception(
                    "Too many signup attempts. Supabase email rate limit exceeded. "
                    "Please wait a few minutes or use a different email."
                )
            if "already registered" in lower or "already exists" in lower:
                raise Exception("This email is already registered. Please login instead.")
            elif "invalid email" in lower:
                raise Exception("Please enter a valid email address")
            elif "password" in lower and "short" in lower:
                raise Exception("Password must be at least 6 characters")
            else:
                raise Exception(f"Signup failed: {error_msg}")
    
    def login_with_email(self, email: str, password: str) -> Dict[str, Any]:
        """Login user with email and password."""
        if not self.enabled:
            raise Exception("Supabase authentication is not configured")
        
        try:
            auth_response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not auth_response.user or not auth_response.session:
                raise Exception("Invalid email or password")
            
            user = auth_response.user
            session = auth_response.session
            
            # Get user metadata
            name = user.user_metadata.get("name", email.split("@")[0])
            
            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": name
                },
                "token": session.access_token
            }
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Login failed: {error_msg}")
            
            lower = error_msg.lower()
            if "email not confirmed" in lower:
                raise Exception("Email not confirmed. Please verify your email from the Supabase confirmation mail, then login.")
            if "invalid" in lower or "credentials" in lower:
                raise Exception("Invalid email or password")
            else:
                raise Exception(f"Login failed: {error_msg}")
    
    def verify_google_token(self, google_token: str) -> Dict[str, Any]:
        """Verify Google OAuth token and create/login user."""
        if not self.enabled:
            raise Exception("Supabase authentication is not configured")
        
        try:
            # Sign in with Google OAuth token
            auth_response = self.client.auth.sign_in_with_id_token({
                "provider": "google",
                "token": google_token
            })
            
            if not auth_response.user or not auth_response.session:
                raise Exception("Google authentication failed")
            
            user = auth_response.user
            session = auth_response.session
            
            # Extract name from user metadata
            name = user.user_metadata.get("full_name") or user.user_metadata.get("name") or user.email.split("@")[0]
            
            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": name
                },
                "token": session.access_token
            }
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Google OAuth failed: {error_msg}")
            raise Exception(f"Google authentication failed: {error_msg}")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a session token and return user info."""
        if not self.enabled:
            return None
        
        try:
            # Get user from token
            user_response = self.client.auth.get_user(token)
            
            if not user_response.user:
                return None
            
            user = user_response.user
            name = user.user_metadata.get("name") or user.user_metadata.get("full_name") or user.email.split("@")[0]
            
            return {
                "id": user.id,
                "email": user.email,
                "name": name
            }
        
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return None
    
    def logout(self, token: str) -> bool:
        """Logout user by invalidating token."""
        if not self.enabled:
            return True
        
        try:
            self.client.auth.sign_out()
            return True
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False


# Global instance
supabase_auth = SupabaseAuthService()
