"""
Azure DevOps API client.
This module provides the main client interface for Azure DevOps API operations.
"""

import sys
import os
import traceback
from typing import Optional, Dict, Any

from .pr_reviewer import PRReviewer
from .branch_utils import BranchManager
from .file_utils import FileManager
from .diff_utils import DiffManager
from .auth_utils import AuthUtils

class AzureDevOpsClient:
    """Client for interacting with Azure DevOps API with enhanced PR review capabilities."""
    
    def __init__(self, pat=None):
        """
        Initialize the Azure DevOps client with a PAT.
        
        Args:
            pat: Personal Access Token (optional, will use AZURE_PAT env var if not provided)
        """
        self.pat = pat or os.getenv('AZURE_PAT')
        if not self.pat:
            raise ValueError("Azure DevOps PAT is required. Set AZURE_PAT environment variable or pass it directly.")
        
        # Store PAT in auth utils for use by other components
        AuthUtils.get_pat = lambda: self.pat
        
        print(f"Azure DevOps client initialized with PAT length: {len(self.pat)}", file=sys.stderr)
        
        # Initialize component managers on demand to save resources
        self._pr_reviewers = {}
        self._branch_managers = {}
        self._file_managers = {}
        self._diff_managers = {}
    
    def _get_pr_reviewer(self, organization: str, project: str, repository: str) -> PRReviewer:
        """Get a PR reviewer for the specified repository."""
        key = f"{organization}/{project}/{repository}"
        if key not in self._pr_reviewers:
            self._pr_reviewers[key] = PRReviewer(organization, project, repository)
        return self._pr_reviewers[key]
    
    def _get_branch_manager(self, organization: str, project: str, repository: str) -> BranchManager:
        """Get a branch manager for the specified repository."""
        key = f"{organization}/{project}/{repository}"
        if key not in self._branch_managers:
            self._branch_managers[key] = BranchManager(organization, project, repository)
        return self._branch_managers[key]
    
    def _get_file_manager(self, organization: str, project: str, repository: str) -> FileManager:
        """Get a file manager for the specified repository."""
        key = f"{organization}/{project}/{repository}"
        if key not in self._file_managers:
            self._file_managers[key] = FileManager(organization, project, repository)
        return self._file_managers[key]
    
    def _get_diff_manager(self, organization: str, project: str, repository: str) -> DiffManager:
        """Get a diff manager for the specified repository."""
        key = f"{organization}/{project}/{repository}"
        if key not in self._diff_managers:
            self._diff_managers[key] = DiffManager(organization, project, repository)
        return self._diff_managers[key]
    
    # PR operations
    def fetch_pr_changes(self, organization: str, project: str, repository: str, pr_id: int) -> Dict[str, Any]:
        """
        Fetch changes from an Azure DevOps pull request.
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pr_id: Pull Request ID
            
        Returns:
            PR information with changes
        """
        pr_reviewer = self._get_pr_reviewer(organization, project, repository)
        return pr_reviewer.fetch_pr_changes(pr_id)
    
    def perform_enhanced_pr_review(self, organization: str, project: str, repository: str, pr_id: int) -> Dict[str, Any]:
        """
        Perform an enhanced PR review by directly comparing files between source and target branches.
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pr_id: Pull Request ID
            
        Returns:
            Enhanced PR review information
        """
        pr_reviewer = self._get_pr_reviewer(organization, project, repository)
        return pr_reviewer.perform_enhanced_pr_review(pr_id)
    
    def save_pr_review(self, organization: str, project: str, repository: str, pr_id: int, pr_info: Dict[str, Any], output_dir: str = None) -> str:
        """
        Save PR review to a file.
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pr_id: Pull Request ID
            pr_info: PR review information
            output_dir: Output directory (optional)
            
        Returns:
            Success or error message
        """
        pr_reviewer = self._get_pr_reviewer(organization, project, repository)
        return pr_reviewer.save_pr_review(pr_id, pr_info, output_dir)
    
    # Branch operations
    def get_branch_name_from_ref(self, organization: str, project: str, repository: str, ref_name: str) -> str:
        """
        Extract branch name from a ref name.
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            ref_name: Reference name
            
        Returns:
            Branch name
        """
        branch_manager = self._get_branch_manager(organization, project, repository)
        return branch_manager.get_branch_name_from_ref(ref_name)
    
    def get_latest_commit(self, organization: str, project: str, repository: str, branch: str) -> str:
        """
        Get the latest commit ID for a branch.
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            branch: Branch name
            
        Returns:
            Commit ID
        """
        branch_manager = self._get_branch_manager(organization, project, repository)
        return branch_manager.get_latest_commit(branch)
    
    def get_branch_files(self, organization: str, project: str, repository: str, branch: str, path: str = None) -> Dict[str, Any]:
        """
        Get all files in a branch.
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            branch: Branch name
            path: Optional path filter
            
        Returns:
            List of files
        """
        branch_manager = self._get_branch_manager(organization, project, repository)
        return branch_manager.get_files(branch, path)
    
    # File operations
    def fetch_file_content(self, organization: str, project: str, repository: str, file_path: str, commit_id: str) -> str:
        """
        Fetch content of a file.
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            file_path: Path to the file
            commit_id: Commit ID or branch name
            
        Returns:
            File content
        """
        file_manager = self._get_file_manager(organization, project, repository)
        return file_manager.fetch_content(file_path, commit_id)
    
    # Diff operations
    def fetch_file_diff(self, organization: str, project: str, repository: str, pr_id: int, iteration_id: int, file_path: str) -> Dict[str, Any]:
        """
        Fetch diff for a file.
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pr_id: Pull Request ID
            iteration_id: Iteration ID
            file_path: Path to the file
            
        Returns:
            Diff information
        """
        diff_manager = self._get_diff_manager(organization, project, repository)
        return diff_manager.fetch_file_diff(pr_id, iteration_id, file_path)
    
    def compare_branch_files(self, organization: str, project: str, repository: str, source_branch: str, target_branch: str, file_path: str) -> Dict[str, Any]:
        """
        Compare a file between branches.
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            source_branch: Source branch name
            target_branch: Target branch name
            file_path: Path to the file
            
        Returns:
            Comparison result
        """
        diff_manager = self._get_diff_manager(organization, project, repository)
        return diff_manager.compare_files(source_branch, target_branch, file_path)

# Singleton instance for easy importing
_client_instance = None

def get_client():
    """Get or create the AzureDevOpsClient singleton instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = AzureDevOpsClient()
    return _client_instance
