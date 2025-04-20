"""
File utilities for Azure DevOps API.
"""

import sys
import os
import datetime
import traceback
import requests
import re
import json
from urllib.parse import quote, urlencode
from typing import Dict, Any, Optional, List, Tuple

from .http_utils import HTTPUtils

class FileManager:
    """Manages file operations for Azure DevOps."""
    
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
        self.web_url = f"https://dev.azure.com/{organization}/{project}/_git/{repository}"
        
        # Cache for project and repository IDs
        self._project_id = None
        self._repository_id = None
    
    def fetch_content(self, file_path: str, commit_or_branch: str) -> str:
        """
        Fetch content of a specific file at a given commit or branch using various fallback approaches.
        
        Args:
            file_path: Path to the file
            commit_or_branch: Commit ID or branch name
            
        Returns:
            File content as text
        """
        print(f"Fetching content for file: {file_path} at commit/branch: {commit_or_branch}", file=sys.stderr)
        
        try:
            # Make sure file path is consistent by removing leading slash if present
            if file_path.startswith('/'):
                file_path = file_path[1:]
                
            # Try all available methods to fetch the file content
            content = None
            errors = []
            
            # Method 1: Try using the standard git API
            try:
                content = self._fetch_via_api(file_path, commit_or_branch)
                if not content.startswith("Error:"):
                    return content
                errors.append(f"API method failed: {content}")
                print(f"API method failed: {content}", file=sys.stderr)
            except Exception as e:
                errors.append(f"API method exception: {str(e)}")
                print(f"API method exception: {str(e)}", file=sys.stderr)
            
            # Method 2: Try using the API with project and repository GUIDs
            try:
                content = self._fetch_via_api_with_guids(file_path, commit_or_branch)
                if not content.startswith("Error:"):
                    return content
                errors.append(f"API with GUIDs method failed: {content}")
                print(f"API with GUIDs method failed: {content}", file=sys.stderr)
            except Exception as e:
                errors.append(f"API with GUIDs exception: {str(e)}")
                print(f"API with GUIDs exception: {str(e)}", file=sys.stderr)
            
            # Method 3: Try using a REST client approach directly
            try:
                content = self._fetch_via_rest_client(file_path, commit_or_branch)
                if not content.startswith("Error:"):
                    return content
                errors.append(f"REST client method failed: {content}")
                print(f"REST client method failed: {content}", file=sys.stderr)
            except Exception as e:
                errors.append(f"REST client exception: {str(e)}")
                print(f"REST client exception: {str(e)}", file=sys.stderr)
            
            # Method 4: Try using the itemContent endpoint
            try:
                content = self._fetch_via_item_content(file_path, commit_or_branch)
                if not content.startswith("Error:"):
                    return content
                errors.append(f"Item content method failed: {content}")
                print(f"Item content method failed: {content}", file=sys.stderr)
            except Exception as e:
                errors.append(f"Item content exception: {str(e)}")
                print(f"Item content exception: {str(e)}", file=sys.stderr)
            
            # Method 5: Try using the web URL with raw=true
            try:
                content = self._fetch_via_web_raw(file_path, commit_or_branch)
                if not content.startswith("Error:"):
                    return content
                errors.append(f"Web raw method failed: {content}")
                print(f"Web raw method failed: {content}", file=sys.stderr)
            except Exception as e:
                errors.append(f"Web raw exception: {str(e)}")
                print(f"Web raw exception: {str(e)}", file=sys.stderr)
            
            # Method 6: Try direct web scraping
            try:
                content = self._fetch_via_web_scraping(file_path, commit_or_branch)
                if not content.startswith("Error:"):
                    return content
                errors.append(f"Web scraping method failed: {content}")
                print(f"Web scraping method failed: {content}", file=sys.stderr)
            except Exception as e:
                errors.append(f"Web scraping exception: {str(e)}")
                print(f"Web scraping exception: {str(e)}", file=sys.stderr)
            
            # If we got here, all methods failed
            error_summary = "\n".join(errors)
            return f"Error: Could not retrieve file content through any available method. Details:\n{error_summary}"
                    
        except Exception as e:
            error_msg = f"Error fetching file content: {str(e)}"
            print(error_msg, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return f"Error: {error_msg}"
    
    def _fetch_via_api(self, file_path: str, commit_or_branch: str) -> str:
        """Fetch file content using the standard git API."""
        # First attempt - standard API path
        content_url = f"{self.base_url}/items"
        params = {
            "path": f"/{file_path}",
            "versionDescriptor.version": commit_or_branch,
            "api-version": "6.0"
        }
        
        try:
            print(f"Attempting to fetch file via standard API", file=sys.stderr)
            response = HTTPUtils.make_request(content_url, params=params)
            return response.text
        except Exception as err:
            # Second attempt - try with branch format if it looks like a branch
            if '/' in commit_or_branch or commit_or_branch.startswith('GB'):
                # Extract the branch name if it starts with GB (GitBranch prefix)
                branch_name = commit_or_branch
                if branch_name.startswith('GB'):
                    branch_name = branch_name[2:]  # Remove GB prefix
                
                # URL encode the branch name
                encoded_version = quote(branch_name)
                params = {
                    "path": f"/{file_path}",
                    "versionDescriptor.version": encoded_version,
                    "versionDescriptor.versionType": "branch",
                    "api-version": "6.0"
                }
                
                try:
                    print(f"Attempting with branch format: {branch_name}", file=sys.stderr)
                    response = HTTPUtils.make_request(content_url, params=params)
                    return response.text
                except Exception as inner_err:
                    print(f"Branch format attempt failed: {str(inner_err)}", file=sys.stderr)
            
            return f"Error: {str(err)}"
    
    def _get_project_id(self) -> str:
        """Get the project GUID."""
        if self._project_id:
            return self._project_id
            
        try:
            # Get project information using the Azure DevOps API
            url = f"https://dev.azure.com/{self.organization}/_apis/projects/{self.project}?api-version=6.0"
            print(f"Fetching project ID from: {url}", file=sys.stderr)
            
            response = HTTPUtils.make_request(url)
            data = response.json()
            
            if 'id' in data:
                self._project_id = data['id']
                print(f"Project ID for '{self.project}': {self._project_id}", file=sys.stderr)
                return self._project_id
            else:
                print(f"Project ID not found in response: {data}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"Error getting project ID: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return None
    
    def _get_repository_id(self) -> str:
        """Get the repository GUID."""
        if self._repository_id:
            return self._repository_id
            
        try:
            # Get repository information using the Azure DevOps API
            url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/git/repositories/{self.repository}?api-version=6.0"
            print(f"Fetching repository ID from: {url}", file=sys.stderr)
            
            response = HTTPUtils.make_request(url)
            data = response.json()
            
            if 'id' in data:
                self._repository_id = data['id']
                print(f"Repository ID for '{self.repository}': {self._repository_id}", file=sys.stderr)
                return self._repository_id
            else:
                print(f"Repository ID not found in response: {data}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"Error getting repository ID: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return None
    
    def _fetch_via_api_with_guids(self, file_path: str, commit_or_branch: str) -> str:
        """Fetch file content using the API with project and repository GUIDs."""
        # Get project and repository IDs
        project_id = self._get_project_id()
        repo_id = self._get_repository_id()
        
        if not project_id or not repo_id:
            return "Error: Could not determine project or repository ID"
        
        # Determine version type (commit or branch)
        version_type = "0"  # 0 = branch, 1 = commit, 2 = tag
        version = commit_or_branch
        
        # Check if it's a SHA-1 commit ID (40 hex characters)
        import re
        if re.match(r'^[0-9a-f]{40}$', commit_or_branch, re.IGNORECASE):
            version_type = "1"
        # If it starts with GB, it's a branch reference
        elif commit_or_branch.startswith('GB'):
            version = commit_or_branch[2:]  # Remove GB prefix
        
        # Build the URL with GUIDs
        url = f"https://dev.azure.com/{self.organization}/{project_id}/_apis/git/repositories/{repo_id}/Items"
        
        params = {
            "path": f"/{file_path}",
            "recursionLevel": "0",
            "includeContentMetadata": "true",
            "versionDescriptor.version": version,
            "versionDescriptor.versionOptions": "0",
            "versionDescriptor.versionType": version_type,
            "includeContent": "true",
            "resolveLfs": "true",
            "api-version": "6.0"
        }
        
        try:
            print(f"Attempting to fetch file via API with GUIDs: {url}", file=sys.stderr)
            response = HTTPUtils.make_request(url, params=params)
            return response.text
        except Exception as err:
            print(f"API with GUIDs attempt failed: {str(err)}", file=sys.stderr)
            return f"Error: {str(err)}"
    
    def _fetch_via_rest_client(self, file_path: str, commit_or_branch: str) -> str:
        """
        Fetch file content using a direct REST client approach.
        This bypasses some of the helper methods and gives more control over the request.
        """
        try:
            # Get project and repository IDs if not already cached
            project_id = self._get_project_id() or self.project
            repo_id = self._get_repository_id() or self.repository
            
            # Determine version type
            version_type = "branch"  # Default to branch
            version = commit_or_branch
            
            # Check if it's a SHA-1 commit ID
            if re.match(r'^[0-9a-f]{40}$', commit_or_branch, re.IGNORECASE):
                version_type = "commit"
            # If it starts with GB, it's a branch reference
            elif commit_or_branch.startswith('GB'):
                version = commit_or_branch[2:]  # Remove GB prefix
            
            # Build URL
            url = f"https://dev.azure.com/{self.organization}/{project_id}/_apis/git/repositories/{repo_id}/items"
            params = {
                "path": f"/{file_path}",
                "versionDescriptor.version": version,
                "versionDescriptor.versionType": version_type,
                "api-version": "6.0"
            }
            
            print(f"Attempting to fetch file via REST client: {url} with params: {params}", file=sys.stderr)
            
            # Direct request with detailed headers
            headers = HTTPUtils.get_auth_header()
            headers['Accept'] = 'text/plain'
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            print(f"Response Content-Type: {content_type}", file=sys.stderr)
            
            # Check if we got HTML instead of raw content
            if 'text/html' in content_type or response.text.startswith('<!DOCTYPE html>') or '<html' in response.text:
                return f"Error: Received HTML response instead of raw file content"
                
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _fetch_via_item_content(self, file_path: str, commit_or_branch: str) -> str:
        """
        Fetch file content using the itemContent endpoint which is specifically for raw content.
        """
        try:
            # Get project and repository IDs if not already cached
            project_id = self._get_project_id() or self.project
            repo_id = self._get_repository_id() or self.repository
            
            # Determine version type
            version_type = "branch"  # Default to branch
            version = commit_or_branch
            
            # Check if it's a SHA-1 commit ID
            if re.match(r'^[0-9a-f]{40}$', commit_or_branch, re.IGNORECASE):
                version_type = "commit"
            # If it starts with GB, it's a branch reference
            elif commit_or_branch.startswith('GB'):
                version = commit_or_branch[2:]  # Remove GB prefix
            
            # Build URL - using itemContent specific endpoint
            url = f"https://dev.azure.com/{self.organization}/{project_id}/_apis/git/repositories/{repo_id}/items/{file_path}?version={version}&versionType={version_type}&api-version=6.0&$format=text"
            
            print(f"Attempting to fetch file via itemContent endpoint: {url}", file=sys.stderr)
            
            # Direct request with detailed headers
            headers = HTTPUtils.get_auth_header()
            headers['Accept'] = 'text/plain'
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Check if we got HTML instead of raw content
            if response.text.startswith('<!DOCTYPE html>') or '<html' in response.text:
                return f"Error: Received HTML response instead of raw file content"
                
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _fetch_via_web_raw(self, file_path: str, commit_or_branch: str) -> str:
        """Fetch file content using the web URL with raw=true parameter."""
        try:
            # Prepare branch name
            branch_name = commit_or_branch
            if branch_name.startswith('GB'):
                branch_name = branch_name[2:]  # Remove GB prefix
            
            # Check if it's a commit ID and handle appropriately
            if re.match(r'^[0-9a-f]{40}$', commit_or_branch, re.IGNORECASE):
                # For commit IDs, use a different format
                params = {
                    "version": commit_or_branch,
                    "path": f"/{file_path}",
                    "raw": "true"
                }
            else:
                # For branches, use GB prefix
                params = {
                    "version": f"GB{branch_name}" if not branch_name.startswith('GB') else branch_name,
                    "path": f"/{file_path}",
                    "raw": "true"
                }
            
            url = f"{self.web_url}?{urlencode(params)}"
            
            print(f"Attempting to fetch file via web URL with raw=true: {url}", file=sys.stderr)
            
            headers = HTTPUtils.get_auth_header()
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Check if we got HTML instead of raw content
            if response.text.startswith('<!DOCTYPE html>') or '<html' in response.text:
                # Don't return an error immediately, but try to extract code from HTML
                try:
                    # Try to find the file content inside the HTML
                    code = self._extract_code_from_html(response.text)
                    if code:
                        return code
                except Exception as ex:
                    print(f"Failed to extract code from HTML: {str(ex)}", file=sys.stderr)
                
                return f"Error: Received HTML response instead of raw file content"
                
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _extract_code_from_html(self, html_content: str) -> str:
        """
        Extract code content from HTML response.
        This is a fallback when we receive HTML instead of raw content.
        """
        print("Attempting to extract code from HTML response", file=sys.stderr)
        
        # Look for JSON data in the page
        # Most modern Azure DevOps pages include the file content in a JSON object
        try:
            matches = re.findall(r'<script type="application/json" id="(dataProviders|initial-data)">(.*?)</script>', html_content, re.DOTALL)
            
            for match in matches:
                try:
                    json_data = json.loads(match[1])
                    
                    # Look for content in data providers
                    if 'data' in json_data and isinstance(json_data['data'], dict):
                        for key, value in json_data['data'].items():
                            if 'content' in value:
                                print(f"Found content in {key}", file=sys.stderr)
                                return value['content']
                    
                    # Alternative structure
                    if 'codeContent' in json_data:
                        return json_data['codeContent']
                        
                    # Look for content in file structure
                    if 'file' in json_data and 'content' in json_data['file']:
                        return json_data['file']['content']
                        
                except Exception as e:
                    print(f"Error parsing JSON data: {str(e)}", file=sys.stderr)
                    continue
        
        except Exception as e:
            print(f"Error extracting JSON data: {str(e)}", file=sys.stderr)
        
        # Fallback to regex approach
        try:
            # Look for content in code viewers
            code_viewers = re.findall(r'<div class="code-viewer">(.*?)</div>', html_content, re.DOTALL)
            if code_viewers:
                # Extract content from the first code viewer
                code_content = re.sub(r'<[^>]+>', '', code_viewers[0])
                # Unescape HTML entities
                code_content = code_content.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                return code_content.strip()
                
            # Look for pre tags
            pre_tags = re.findall(r'<pre[^>]*>(.*?)</pre>', html_content, re.DOTALL)
            if pre_tags:
                # Extract content from the first pre tag
                code_content = re.sub(r'<[^>]+>', '', pre_tags[0])
                # Unescape HTML entities
                code_content = code_content.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                return code_content.strip()
        
        except Exception as e:
            print(f"Error extracting code with regex: {str(e)}", file=sys.stderr)
            
        return ""
    
    def _fetch_via_web_scraping(self, file_path: str, commit_or_branch: str) -> str:
        """
        Fetch file content by simulating a web browser and extracting content.
        This is a last resort when API methods fail.
        """
        try:
            # Prepare branch name
            branch_name = commit_or_branch
            if branch_name.startswith('GB'):
                branch_name = branch_name[2:]  # Remove GB prefix
            
            # Construct the URL
            params = {
                "version": f"GB{branch_name}" if not branch_name.startswith('GB') else branch_name,
                "path": f"/{file_path}"
            }
            url = f"{self.web_url}?{urlencode(params)}"
            
            print(f"Attempting to fetch file via web scraping: {url}", file=sys.stderr)
            
            headers = HTTPUtils.get_auth_header()
            # Add user agent to mimic browser
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Extract code from HTML
            code = self._extract_code_from_html(response.text)
            if code:
                return code
                
            return f"Error: Could not extract file content from web page"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def fetch_direct_url(self, file_path: str, branch_name: str) -> str:
        """
        Return the direct URL to view the file in the web UI.
        
        Args:
            file_path: Path to the file
            branch_name: Branch name
            
        Returns:
            URL to view the file in the web UI
        """
        # Ensure branch format
        if not branch_name.startswith('GB'):
            branch_name = f"GB{branch_name}"
        
        # Construct the URL
        params = {
            "version": branch_name,
            "path": f"/{file_path}"
        }
        return f"{self.web_url}?{urlencode(params)}"
    
    def compare_files_locally(self, source_content: str, target_content: str, source_name: str = "source", target_name: str = "target") -> Tuple[str, Dict]:
        """
        Compare two file contents and generate a unified diff.
        
        Args:
            source_content: Content of the source file
            target_content: Content of the target file
            source_name: Name to use for the source file in the diff
            target_name: Name to use for the target file in the diff
            
        Returns:
            Tuple of (unified diff, dict with line changes)
        """
        import difflib
        
        source_lines = source_content.splitlines()
        target_lines = target_content.splitlines()
        
        diff = list(difflib.unified_diff(
            target_lines, source_lines,
            fromfile=target_name,
            tofile=source_name,
            lineterm=''
        ))
        
        # Parse line changes
        added_lines = []
        removed_lines = []
        current_line_number = 0
        
        for line in diff:
            if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                # Parse the line numbers from the @@ line
                if line.startswith('@@'):
                    # Format is @@ -a,b +c,d @@
                    parts = line.split()
                    if len(parts) >= 3:
                        current_line_number = int(parts[2].split(',')[0][1:])
                continue
                
            if line.startswith('+'):
                added_lines.append((current_line_number, line[1:]))
                current_line_number += 1
            elif line.startswith('-'):
                removed_lines.append((current_line_number, line[1:]))
                # Don't increment line number for removed lines
            else:
                current_line_number += 1
        
        line_changes = {
            "added": added_lines,
            "removed": removed_lines
        }
        
        return '\n'.join(diff), line_changes
    
    def save_analysis(self, output_dir: str, title: str, content: str) -> str:
        """
        Save PR analysis to a file and return the filepath.
        
        Args:
            output_dir: Directory to save the file
            title: Title for the analysis file
            content: Content to write to the file
            
        Returns:
            Success or error message
        """
        # Ensure output directory exists
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                print(f"Created output directory: {output_dir}", file=sys.stderr)
            except Exception as e:
                print(f"Error creating output directory: {str(e)}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return f"Error: {str(e)}"
        
        # Sanitize the title to create a valid filename
        safe_title = "".join([c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in title])
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.md"
        filepath = os.path.join(output_dir, filename)
        
        print(f"Saving analysis to file: {filepath}", file=sys.stderr)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            success_msg = f"Analysis saved successfully to {filepath}"
            print(success_msg, file=sys.stderr)
            return success_msg
        except Exception as e:
            error_msg = f"Error saving analysis to file: {str(e)}"
            print(error_msg, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return error_msg
