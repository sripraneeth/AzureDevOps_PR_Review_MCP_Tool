"""
Diff utilities for Azure DevOps API.
"""

import sys
import traceback
import difflib
from typing import Dict, Any, List, Tuple, Optional

from .http_utils import HTTPUtils
from .file_utils import FileManager
from .branch_utils import BranchManager

class DiffManager:
    """Manages diff operations for Azure DevOps."""
    
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
        self.file_manager = FileManager(organization, project, repository)
        self.branch_manager = BranchManager(organization, project, repository)
    
    def fetch_file_diff(self, pr_id: int, iteration_id: int, file_path: str) -> Dict[str, Any]:
        """
        Fetch the diff of a specific file in a PR.
        
        Args:
            pr_id: Pull Request ID
            iteration_id: Iteration ID
            file_path: Path to the file
            
        Returns:
            Diff information as dictionary
        """
        print(f"Fetching diff for file: {file_path} in PR: {pr_id}, iteration: {iteration_id}", file=sys.stderr)
        
        try:
            # Azure DevOps API to get file diff
            diff_url = f"{self.base_url}/pullRequests/{pr_id}/iterations/{iteration_id}/changes"
            params = {
                "path": file_path,
                "api-version": "6.0"
            }
            
            return HTTPUtils.get_json(diff_url, params)
        except Exception as e:
            print(f"Error fetching file diff: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return {"error": str(e)}
    
    def compare_files(self, source_branch: str, target_branch: str, file_path: str) -> Dict[str, Any]:
        """
        Compare a file between source and target branches to get differences.
        
        Args:
            source_branch: Source branch name
            target_branch: Target branch name
            file_path: Path to the file
            
        Returns:
            Comparison result as dictionary
        """
        print(f"Comparing file '{file_path}' between branches '{source_branch}' and '{target_branch}'", file=sys.stderr)
        
        try:
            # Get the latest commits for both branches
            source_commit = self.branch_manager.get_latest_commit(source_branch)
            target_commit = self.branch_manager.get_latest_commit(target_branch)
            
            # If we couldn't get commits, use branch names directly
            if not source_commit:
                source_commit = source_branch
                print(f"Using source branch name directly: {source_branch}", file=sys.stderr)
            
            if not target_commit:
                target_commit = target_branch
                print(f"Using target branch name directly: {target_branch}", file=sys.stderr)
            
            # Get file content from both branches
            source_content = self.file_manager.fetch_content(file_path, source_commit)
            target_content = self.file_manager.fetch_content(file_path, target_commit)
            
            # Check for error responses
            if source_content.startswith("Error:"):
                # File might not exist in source branch
                source_exists = False
                source_content = ""
            else:
                source_exists = True
                
            if target_content.startswith("Error:"):
                # File might not exist in target branch
                target_exists = False
                target_content = ""
            else:
                target_exists = True
            
            # Generate diff using Python's difflib
            source_lines = source_content.splitlines()
            target_lines = target_content.splitlines()
            
            diff = list(difflib.unified_diff(
                target_lines, source_lines,
                fromfile=f'{file_path} (target)',
                tofile=f'{file_path} (source)',
                lineterm=''
            ))
            
            return {
                "source_commit": source_commit,
                "target_commit": target_commit,
                "source_exists": source_exists,
                "target_exists": target_exists,
                "source_content": source_content,
                "target_content": target_content,
                "diff_unified": '\n'.join(diff),
                "line_changes": self.parse_line_changes(diff)
            }
            
        except Exception as e:
            print(f"Error comparing branch files: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return {"error": str(e)}
    
    def parse_line_changes(self, diff_lines: List[str]) -> Dict[str, List[Tuple[int, str]]]:
        """
        Parse line changes from a unified diff.
        
        Args:
            diff_lines: Lines of the unified diff
            
        Returns:
            Dictionary with added and removed lines
        """
        added_lines = []
        removed_lines = []
        current_line_number = 0
        
        for line in diff_lines:
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
        
        return {
            "added": added_lines,
            "removed": removed_lines
        }
