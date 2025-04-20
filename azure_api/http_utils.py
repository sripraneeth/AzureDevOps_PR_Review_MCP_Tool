"""
HTTP utilities for Azure DevOps API.
"""

import sys
import traceback
import requests
from urllib.parse import quote
from typing import Dict, Any, Optional

from .auth_utils import AuthUtils

class HTTPUtils:
    """HTTP utilities for making API requests to Azure DevOps."""
    
    @staticmethod
    def get_auth_header():
        """Get authentication header using AuthUtils."""
        return AuthUtils.get_auth_header()
    
    @staticmethod
    def make_request(url: str, method: str = 'GET', params: Dict = None, 
                     headers: Dict = None, retry_count: int = 1) -> requests.Response:
        """
        Make an HTTP request with error handling and retry logic.
        
        Args:
            url: The URL to request
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            headers: HTTP headers
            retry_count: Number of retry attempts
            
        Returns:
            Response object
        """
        if headers is None:
            headers = HTTPUtils.get_auth_header()
            
        print(f"Making {method} request to: {url}", file=sys.stderr)
        if params:
            print(f"With params: {params}", file=sys.stderr)
            
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, params=params)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, params=params)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response
            
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error: {err}", file=sys.stderr)
            # Allow the caller to handle the error
            raise
            
        except Exception as e:
            print(f"Error making request: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise
    
    @staticmethod
    def get_json(url: str, params: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """
        Make a GET request and return the JSON response.
        
        Args:
            url: The URL to request
            params: Query parameters
            headers: HTTP headers
            
        Returns:
            JSON response as dictionary
        """
        try:
            response = HTTPUtils.make_request(url, 'GET', params, headers)
            return response.json()
        except Exception as e:
            print(f"Error getting JSON from {url}: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return {"error": str(e)}
            
    @staticmethod
    def get_text(url: str, params: Dict = None, headers: Dict = None) -> str:
        """
        Make a GET request and return the text response.
        
        Args:
            url: The URL to request
            params: Query parameters
            headers: HTTP headers
            
        Returns:
            Text response
        """
        try:
            response = HTTPUtils.make_request(url, 'GET', params, headers)
            return response.text
        except Exception as e:
            print(f"Error getting text from {url}: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return f"Error: {str(e)}"
            
    @staticmethod
    def encode_path(path: str) -> str:
        """
        Encode a path for use in a URL.
        
        Args:
            path: The path to encode
            
        Returns:
            URL-encoded path
        """
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
            
        return quote(path)
