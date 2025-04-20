"""
Authentication utilities for Azure DevOps API.
"""

import sys
import os
import base64
import traceback

class AuthUtils:
    """Authentication utilities for Azure DevOps API."""
    
    @staticmethod
    def get_pat():
        """Get the Personal Access Token from environment variables."""
        pat = os.getenv('AZURE_PAT')
        if not pat:
            raise ValueError("Azure DevOps PAT is required. Set AZURE_PAT environment variable.")
        return pat
        
    @staticmethod
    def get_auth_header(pat=None):
        """Create the authentication header for Azure DevOps API."""
        try:
            # Use provided PAT or get from environment
            _pat = pat or AuthUtils.get_pat()
            
            # Basic authentication with empty username
            # This is the standard format: "Basic base64(:'PAT')"
            pat_with_colon = f":{_pat}"
            encoded_pat = base64.b64encode(pat_with_colon.encode('utf-8')).decode('utf-8')
            auth_header = {'Authorization': f'Basic {encoded_pat}'}
            return auth_header
        except Exception as e:
            print(f"Error creating authentication header: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            # Fall back to using PAT directly
            return {'Authorization': f'Basic {_pat}'}
