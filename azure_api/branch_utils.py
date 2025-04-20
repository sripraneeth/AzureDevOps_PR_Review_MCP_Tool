"""
Branch utilities for Azure DevOps API.
"""

import sys
import traceback
from typing import Dict, Any, List, Optional
from urllib.parse import quote

from .http_utils import HTTPUtils
from .auth_utils import AuthUtils

class BranchManager:
    """Manages operations related to branches in Azure DevOps."""
    
    def __init__(self, organization: str, project: str, repository: str):
        """
        Initialize with repository information.
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            repository: Azure DevOps repository name
        """
        self.organization = organization
        self.project = project
        self.repository = repository
        self.base_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repository}"
    
    def get_branch_name_from_ref(self, ref_name: str) -> str:
        """
        Extract branch name from a ref name (e.g., 'refs/heads/main' -> 'main').
        
        Args:
            ref_name: The reference name (e.g., 'refs/heads/main')
            
        Returns:
            The branch name
        """
        if ref_name.startswith('refs/heads/'):
            return ref_name[len('refs/heads/'):]
        return ref_name
    
    def get_latest_commit(self, branch: str) -> str:
        """
        Get the latest commit ID from a branch.
        
        Args:
            branch: The branch name
            
        Returns:
            The commit ID or branch name if commit ID cannot be determined
        """
        try:
            # Normalize branch name for API request
            # If it's already a full ref path like refs/heads/main, use it as is
            # Otherwise, assume it's a branch name and prefix with heads/
            filter_ref = branch
            if not branch.startswith('refs/'):
                filter_ref = f"heads/{branch}"
                
            # Handle special characters in branch name
            encoded_filter = quote(filter_ref)
                
            # Get branch info to get the latest commit
            branch_url = f"{self.base_url}/refs?filter={encoded_filter}&api-version=6.0"
            print(f"Making API request to get branch info: {branch_url}", file=sys.stderr)
            
            try:
                data = HTTPUtils.get_json(branch_url)
                
                if data.get('count', 0) > 0:
                    # Get the commit ID
                    commit_id = data['value'][0]['objectId']
                    print(f"Found latest commit for branch '{branch}': {commit_id}", file=sys.stderr)
                    return commit_id
                else:
                    print(f"Branch '{branch}' not found using filter='{filter_ref}'. Trying alternative approach...", file=sys.stderr)
            except Exception as e:
                print(f"Error getting branch info: {str(e)}", file=sys.stderr)
                # Continue to try alternative methods
                
            # Alternative approach: try to get branch directly by name
            try:
                # Use the Git API to get branch information
                branch_direct_url = f"{self.base_url}/stats/branches?name={quote(branch)}&api-version=6.0"
                print(f"Trying direct branch request: {branch_direct_url}", file=sys.stderr)
                
                branch_data = HTTPUtils.get_json(branch_direct_url)
                
                if branch_data and len(branch_data) > 0:
                    commit_id = branch_data[0].get('commit', {}).get('commitId', '')
                    if commit_id:
                        print(f"Found latest commit for branch '{branch}' using direct method: {commit_id}", file=sys.stderr)
                        return commit_id
            except Exception as inner_e:
                print(f"Alternative branch lookup failed: {str(inner_e)}", file=sys.stderr)
            
            # If branch name contains slashes (like releases/branch), it might be the actual branch name
            # In this case, we'll return it as is - for use in versionDescriptor.version
            if '/' in branch:
                print(f"Using branch name '{branch}' as version descriptor", file=sys.stderr)
                return branch
                
            return ""
        except Exception as e:
            print(f"Error getting latest commit for branch '{branch}': {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            # If branch name contains slashes (like releases/branch), return as is as a fallback
            if '/' in branch:
                print(f"Using branch name '{branch}' as version descriptor (fallback)", file=sys.stderr)
                return branch
            return ""
            
    def get_files(self, branch: str, path: str = None) -> List[Dict[str, Any]]:
        """
        Get all files in a branch, optionally filtered by path.
        
        Args:
            branch: The branch name
            path: Optional path to filter files
            
        Returns:
            List of file information dictionaries
        """
        print(f"Getting files from branch '{branch}' in {self.organization}/{self.project}/{self.repository}", file=sys.stderr)
        
        try:
            # Get the latest commit for the branch
            commit_id = self.get_latest_commit(branch)
            if not commit_id:
                print(f"Could not get commit ID for branch '{branch}', using branch name directly", file=sys.stderr)
                commit_id = branch  # Fallback to using branch name
            
            # Azure DevOps API to get items in a repository
            items_url = f"{self.base_url}/items"
            
            # Determine if we're using a commit ID or branch name
            version_type = "commit"
            if '/' in commit_id and not commit_id.startswith('refs/'):
                # This looks like a branch name with slashes (e.g., 'releases/branch')
                version_type = "branch"
                print(f"Using version type 'branch' for '{commit_id}'", file=sys.stderr)
            
            # URL encode the version
            encoded_version = quote(commit_id)
            
            params = {
                "versionDescriptor.version": encoded_version,
                "versionDescriptor.versionType": version_type,
                "recursionLevel": "Full",
                "api-version": "6.0"
            }
            
            if path:
                # Ensure path starts with /
                if not path.startswith('/'):
                    path = '/' + path
                params["path"] = path
            
            print(f"Requesting items with URL: {items_url} and params: {params}", file=sys.stderr)
            
            try:
                response = HTTPUtils.make_request(items_url, params=params)
                data = response.json()
            except requests.exceptions.HTTPError as err:
                if err.response.status_code == 404:
                    print("Got 404, trying alternative approach", file=sys.stderr)
                    # Try different API endpoint
                    alt_url = f"https://dev.azure.com/{self.organization}/{self.project}/_git/{self.repository}/items"
                    print(f"Trying alternative URL: {alt_url}", file=sys.stderr)
                    response = HTTPUtils.make_request(alt_url, params=params)
                    data = response.json()
                else:
                    raise
            
            # Extract file information
            files = []
            if 'value' in data:
                # Standard response format
                for item in data.get('value', []):
                    if item.get('isFolder', False):
                        continue
                        
                    file_info = {
                        'path': item.get('path', ''),
                        'contentId': item.get('objectId', ''),
                        'size': item.get('size', 0)
                    }
                    files.append(file_info)
            elif isinstance(data, list):
                # Alternative response format
                for item in data:
                    if item.get('isFolder', False):
                        continue
                        
                    file_info = {
                        'path': item.get('path', ''),
                        'contentId': item.get('objectId', ''),
                        'size': item.get('size', 0)
                    }
                    files.append(file_info)
            
            print(f"Found {len(files)} files in branch '{branch}'", file=sys.stderr)
            return files
            
        except Exception as e:
            print(f"Error getting branch files: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return []
