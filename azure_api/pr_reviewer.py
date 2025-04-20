"""
PR reviewer for Azure DevOps API.
"""

import sys
import os
import datetime
import traceback
import difflib
from typing import Dict, Any, List, Optional

from .http_utils import HTTPUtils
from .file_utils import FileManager
from .branch_utils import BranchManager
from .diff_utils import DiffManager

class PRReviewer:
    """Manages PR review operations for Azure DevOps."""
    
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
        self.diff_manager = DiffManager(organization, project, repository)
    
    def fetch_pr_changes(self, pr_id: int) -> Dict[str, Any]:
        """
        Fetch changes from an Azure DevOps pull request.
        
        Args:
            pr_id: Pull Request ID
            
        Returns:
            PR information with changes
        """
        print(f"Fetching PR #{pr_id} from {self.organization}/{self.project}/{self.repository}", file=sys.stderr)
        
        try:
            # Get PR metadata
            pr_url = f"{self.base_url}/pullRequests/{pr_id}"
            params = {"api-version": "6.0"}
            
            pr_data = HTTPUtils.get_json(pr_url, params)
            
            # Extract source and target branch information
            source_branch = self.branch_manager.get_branch_name_from_ref(pr_data['sourceRefName'])
            target_branch = self.branch_manager.get_branch_name_from_ref(pr_data['targetRefName'])
            
            # Get latest commits for both branches
            source_commit = self.branch_manager.get_latest_commit(source_branch)
            target_commit = self.branch_manager.get_latest_commit(target_branch)
            
            # Get file changes - Azure DevOps uses 'iterations' API to get changes
            iterations_url = f"{self.base_url}/pullRequests/{pr_id}/iterations"
            params = {"api-version": "6.0"}
            
            iterations_data = HTTPUtils.get_json(iterations_url, params)
            
            # Get the latest iteration
            latest_iteration = None
            if iterations_data['count'] > 0:
                latest_iteration = iterations_data['value'][-1]['id']
                
                # Get changes for the latest iteration
                changes_url = f"{self.base_url}/pullRequests/{pr_id}/iterations/{latest_iteration}/changes"
                params = {"api-version": "6.0"}
                
                changes_data = HTTPUtils.get_json(changes_url, params)
                
                # Process file changes
                changes = []
                for change in changes_data.get('changes', []):
                    if 'item' in change:
                        item = change['item']
                        change_info = {
                            'filename': item.get('path', ''),
                            'status': change.get('changeType', ''),  # add, edit, delete
                            'isFolder': item.get('isFolder', False),
                            'contentId': item.get('contentId', ''),
                            'originalPath': item.get('originalPath', ''),
                            'url': item.get('url', '')
                        }
                        changes.append(change_info)
                
                # Build the PR info object
                pr_info = {
                    'title': pr_data['title'],
                    'description': pr_data['description'],
                    'author': pr_data['createdBy']['displayName'],
                    'author_email': pr_data['createdBy'].get('uniqueName', ''),
                    'created_at': pr_data['creationDate'],
                    'updated_at': pr_data.get('lastMergeSourceCommit', {}).get('commitId', ''),
                    'status': pr_data['status'],
                    'sourceRefName': pr_data['sourceRefName'],
                    'sourceBranch': source_branch,
                    'sourceCommitId': source_commit,
                    'targetRefName': pr_data['targetRefName'],
                    'targetBranch': target_branch,
                    'targetCommitId': target_commit,
                    'total_changes': len(changes),
                    'changes': changes,
                    'organization': self.organization,
                    'project': self.project,
                    'repository': self.repository,
                    'pr_id': pr_id,
                    'latest_iteration': latest_iteration
                }
                
                print(f"Successfully fetched {len(changes)} changes", file=sys.stderr)
                return pr_info
            else:
                print("No iterations found for this PR", file=sys.stderr)
                return {'error': 'No iterations found for this PR'}
            
        except Exception as e:
            print(f"Error fetching PR changes: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return {'error': str(e)}
    
    def perform_enhanced_pr_review(self, pr_id: int) -> Dict[str, Any]:
        """
        Perform an enhanced PR review by directly comparing files between source and target branches.
        
        Args:
            pr_id: Pull Request ID
            
        Returns:
            Enhanced PR review information
        """
        print(f"Performing enhanced PR review for PR #{pr_id}", file=sys.stderr)
        
        try:
            # Get PR metadata first
            pr_info = self.fetch_pr_changes(pr_id)
            
            if 'error' in pr_info:
                return pr_info
            
            # Extract branch information
            source_branch = pr_info['sourceBranch']
            target_branch = pr_info['targetBranch']
            
            print(f"Comparing branches: source='{source_branch}', target='{target_branch}'", file=sys.stderr)
            
            # First, try using the standard PR changes to get a list of changed files
            # This is more efficient than comparing all files in both branches
            pr_changes = pr_info.get('changes', [])
            
            if pr_changes and len(pr_changes) > 0:
                print(f"Using PR-provided list of {len(pr_changes)} changed files", file=sys.stderr)
                enhanced_changes = []
                
                for change in pr_changes:
                    file_path = change['filename']
                    change_type = change['status'].lower()
                    
                    if change.get('isFolder', False):
                        continue  # Skip folders
                    
                    # Process file based on change type
                    change_info = self._process_change(
                        file_path, 
                        change_type, 
                        source_branch, 
                        target_branch
                    )
                    
                    if change_info:
                        enhanced_changes.append(change_info)
            else:
                print("No PR changes provided, falling back to branch comparison", file=sys.stderr)
                # Fallback: Get files from both branches and compare them
                enhanced_changes = self._compare_branches(
                    source_branch, 
                    target_branch
                )
            
            # Add enhanced changes to PR info
            pr_info['enhanced_changes'] = enhanced_changes
            pr_info['enhanced_total_changes'] = len(enhanced_changes)
            
            # Add direct URLs to view files in web UI
            pr_info['source_branch_url'] = f"https://dev.azure.com/{self.organization}/{self.project}/_git/{self.repository}?version=GB{source_branch}"
            pr_info['target_branch_url'] = f"https://dev.azure.com/{self.organization}/{self.project}/_git/{self.repository}?version=GB{target_branch}"
            
            print(f"Enhanced PR review completed with {len(enhanced_changes)} changes identified", file=sys.stderr)
            return pr_info
            
        except Exception as e:
            print(f"Error performing enhanced PR review: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return {'error': str(e)}
    
    def _process_change(self, file_path: str, change_type: str, 
                        source_branch: str, target_branch: str) -> Dict[str, Any]:
        """
        Process a single file change.
        
        Args:
            file_path: Path to the file
            change_type: Type of change (add, edit, delete)
            source_branch: Source branch name
            target_branch: Target branch name
            
        Returns:
            Change information dictionary
        """
        try:
            # Default values
            source_exists = False
            target_exists = False
            source_content = ""
            target_content = ""
            
            # Get source content for add/edit changes
            if change_type in ['add', 'edit']:
                try:
                    source_content = self.file_manager.fetch_content(file_path, source_branch)
                    source_exists = not source_content.startswith("Error:")
                    
                    if not source_exists:
                        print(f"Warning: Could not fetch source content for '{file_path}' from branch '{source_branch}'", file=sys.stderr)
                        print(f"Error message: {source_content}", file=sys.stderr)
                except Exception as e:
                    print(f"Error fetching source content for {file_path}: {str(e)}", file=sys.stderr)
                    source_content = f"Error: {str(e)}"
            
            # Get target content for edit/delete changes
            if change_type in ['edit', 'delete']:
                try:
                    target_content = self.file_manager.fetch_content(file_path, target_branch)
                    target_exists = not target_content.startswith("Error:")
                    
                    if not target_exists:
                        print(f"Warning: Could not fetch target content for '{file_path}' from branch '{target_branch}'", file=sys.stderr)
                        print(f"Error message: {target_content}", file=sys.stderr)
                except Exception as e:
                    print(f"Error fetching target content for {file_path}: {str(e)}", file=sys.stderr)
                    target_content = f"Error: {str(e)}"
            
            # Get direct URLs to view the files in web UI
            source_url = self.file_manager.fetch_direct_url(file_path, source_branch)
            target_url = self.file_manager.fetch_direct_url(file_path, target_branch)
            
            # Generate diff for edited files
            diff_details = None
            if change_type == 'edit' and source_exists and target_exists:
                # Generate diff using file manager's compare method
                diff_text, line_changes = self.file_manager.compare_files_locally(
                    source_content, 
                    target_content,
                    f"{file_path} ({source_branch})",
                    f"{file_path} ({target_branch})"
                )
                
                diff_details = {
                    "diff_unified": diff_text,
                    "line_changes": line_changes,
                    "source_content": source_content,
                    "target_content": target_content,
                    "source_url": source_url,
                    "target_url": target_url
                }
            
            # Build the change info object
            change_info = {
                'filename': file_path,
                'status': change_type,
                'source_exists': source_exists,
                'target_exists': target_exists,
                'source_url': source_url,
                'target_url': target_url
            }
            
            # Add content based on change type
            if change_type == 'add' and source_exists:
                change_info['source_content'] = source_content
            elif change_type == 'delete' and target_exists:
                change_info['target_content'] = target_content
            elif change_type == 'edit' and diff_details:
                change_info['diff_details'] = diff_details
            
            return change_info
            
        except Exception as e:
            print(f"Error processing change for {file_path}: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return None
    
    def _compare_branches(self, source_branch: str, target_branch: str, 
                          file_limit: int = 50) -> List[Dict[str, Any]]:
        """
        Compare all files between two branches.
        
        Args:
            source_branch: Source branch name
            target_branch: Target branch name
            file_limit: Maximum number of files to compare
            
        Returns:
            List of change information dictionaries
        """
        try:
            # Get files from both branches
            source_files = self.branch_manager.get_files(source_branch)
            target_files = self.branch_manager.get_files(target_branch)
            
            # Create dictionaries for easy lookup
            source_file_dict = {f['path']: f for f in source_files}
            target_file_dict = {f['path']: f for f in target_files}
            
            # Find all unique file paths
            all_file_paths = set(source_file_dict.keys()) | set(target_file_dict.keys())
            
            # Limit to a reasonable number of files to avoid timeouts
            if len(all_file_paths) > file_limit:
                print(f"Warning: Limiting comparison to {file_limit} files out of {len(all_file_paths)} total", file=sys.stderr)
                all_file_paths = list(all_file_paths)[:file_limit]
            
            # Compare each file
            enhanced_changes = []
            
            for file_path in all_file_paths:
                source_exists = file_path in source_file_dict
                target_exists = file_path in target_file_dict
                
                if source_exists and target_exists:
                    # File exists in both branches - check if content differs
                    if source_file_dict[file_path].get('contentId', '') != target_file_dict[file_path].get('contentId', ''):
                        # Content is different - process as an edit
                        change_info = self._process_change(
                            file_path, 'edit', source_branch, target_branch
                        )
                        if change_info:
                            enhanced_changes.append(change_info)
                elif source_exists and not target_exists:
                    # File exists only in source - it's an addition
                    change_info = self._process_change(
                        file_path, 'add', source_branch, target_branch
                    )
                    if change_info:
                        enhanced_changes.append(change_info)
                elif target_exists and not source_exists:
                    # File exists only in target - it's a deletion
                    change_info = self._process_change(
                        file_path, 'delete', source_branch, target_branch
                    )
                    if change_info:
                        enhanced_changes.append(change_info)
            
            return enhanced_changes
            
        except Exception as e:
            print(f"Error comparing branches: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return []

    def save_pr_review(self, pr_id: int, pr_info: Dict[str, Any], output_dir: str = None) -> str:
        """
        Save PR review to a file and return the filepath.
        
        Args:
            pr_id: Pull Request ID
            pr_info: PR review information
            output_dir: Directory to save the file (optional)
            
        Returns:
            Success or error message
        """
        # Use default output directory if not specified
        if not output_dir:
            output_dir = os.getenv('OUTPUT_DIR', 'pr_analysis_results')
        
        # Ensure output directory exists
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                print(f"Created output directory: {output_dir}", file=sys.stderr)
            except Exception as e:
                print(f"Error creating output directory: {str(e)}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return f"Error: {str(e)}"
        
        # Generate filename with PR ID
        repo_name = self.repository.replace('/', '_')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"PR_{pr_id}_{repo_name}_{timestamp}.md"
        filepath = os.path.join(output_dir, filename)
        
        # Generate markdown content
        try:
            content = self._generate_pr_review_markdown(pr_info)
            
            # Write to file
            print(f"Saving PR review to file: {filepath}", file=sys.stderr)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                
            success_msg = f"PR review saved successfully to {filepath}"
            print(success_msg, file=sys.stderr)
            return success_msg
        except Exception as e:
            error_msg = f"Error saving PR review to file: {str(e)}"
            print(error_msg, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return error_msg
    
    def _generate_pr_review_markdown(self, pr_info: Dict[str, Any]) -> str:
        """
        Generate markdown content for PR review.
        
        Args:
            pr_info: PR review information
            
        Returns:
            Markdown content
        """
        # Basic PR information
        lines = []
        lines.append(f"# PR Review: {pr_info.get('title', 'No Title')}")
        lines.append("")
        
        # PR metadata
        lines.append("## PR Information")
        lines.append("")
        lines.append(f"- **PR ID:** {pr_info.get('pr_id', 'N/A')}")
        lines.append(f"- **Author:** {pr_info.get('author', 'N/A')}")
        lines.append(f"- **Repository:** {pr_info.get('repository', 'N/A')}")
        lines.append(f"- **Created:** {pr_info.get('created_at', 'N/A')}")
        lines.append(f"- **Status:** {pr_info.get('status', 'N/A')}")
        lines.append(f"- **Source Branch:** [{pr_info.get('sourceBranch', 'N/A')}]({pr_info.get('source_branch_url', '#')})")
        lines.append(f"- **Target Branch:** [{pr_info.get('targetBranch', 'N/A')}]({pr_info.get('target_branch_url', '#')})")
        lines.append("")
        
        # Description
        description = pr_info.get('description', '')
        if description:
            lines.append("## Description")
            lines.append("")
            lines.append(description)
            lines.append("")
        
        # Changes summary
        enhanced_changes = pr_info.get('enhanced_changes', [])
        lines.append("## Changes Summary")
        lines.append("")
        lines.append(f"Total changes: {len(enhanced_changes)}")
        lines.append("")
        
        # Count by change type
        add_count = sum(1 for change in enhanced_changes if change.get('status') == 'add')
        edit_count = sum(1 for change in enhanced_changes if change.get('status') == 'edit')
        delete_count = sum(1 for change in enhanced_changes if change.get('status') == 'delete')
        
        lines.append(f"- Added files: {add_count}")
        lines.append(f"- Modified files: {edit_count}")
        lines.append(f"- Deleted files: {delete_count}")
        lines.append("")
        
        # List of changed files
        lines.append("## Changed Files")
        lines.append("")
        
        # Group by change type for better organization
        if add_count > 0:
            lines.append("### Added Files")
            lines.append("")
            for change in enhanced_changes:
                if change.get('status') == 'add':
                    filename = change.get('filename', 'Unknown file')
                    source_url = change.get('source_url', '#')
                    lines.append(f"- [{filename}]({source_url})")
            lines.append("")
        
        if edit_count > 0:
            lines.append("### Modified Files")
            lines.append("")
            for change in enhanced_changes:
                if change.get('status') == 'edit':
                    filename = change.get('filename', 'Unknown file')
                    source_url = change.get('source_url', '#')
                    lines.append(f"- [{filename}]({source_url})")
            lines.append("")
        
        if delete_count > 0:
            lines.append("### Deleted Files")
            lines.append("")
            for change in enhanced_changes:
                if change.get('status') == 'delete':
                    filename = change.get('filename', 'Unknown file')
                    target_url = change.get('target_url', '#')
                    lines.append(f"- [{filename}]({target_url})")
            lines.append("")
        
        # Detailed changes
        lines.append("## Detailed Changes")
        lines.append("")
        
        for change in enhanced_changes:
            filename = change.get('filename', 'Unknown file')
            status = change.get('status', 'unknown')
            
            lines.append(f"### {filename} ({status})")
            lines.append("")
            
            if status == 'add':
                lines.append(f"- [View in source branch]({change.get('source_url', '#')})")
                lines.append("")
                
                if change.get('source_exists', False) and 'source_content' in change:
                    # Include a preview of the added file
                    source_content = change.get('source_content', '')
                    if len(source_content) > 1000:
                        # Truncate long content
                        preview = source_content[:1000] + "...(truncated)"
                    else:
                        preview = source_content
                    
                    lines.append("```")
                    lines.append(preview)
                    lines.append("```")
                else:
                    lines.append("*Content could not be retrieved*")
                
            elif status == 'delete':
                lines.append(f"- [View in target branch]({change.get('target_url', '#')})")
                lines.append("")
                
                if change.get('target_exists', False) and 'target_content' in change:
                    # Include a preview of the deleted file
                    target_content = change.get('target_content', '')
                    if len(target_content) > 1000:
                        # Truncate long content
                        preview = target_content[:1000] + "...(truncated)"
                    else:
                        preview = target_content
                    
                    lines.append("```")
                    lines.append(preview)
                    lines.append("```")
                else:
                    lines.append("*Content could not be retrieved*")
                
            elif status == 'edit':
                lines.append(f"- [View in source branch]({change.get('source_url', '#')})")
                lines.append(f"- [View in target branch]({change.get('target_url', '#')})")
                lines.append("")
                
                diff_details = change.get('diff_details', {})
                if diff_details and 'diff_unified' in diff_details:
                    # Include the diff
                    diff_text = diff_details['diff_unified']
                    if len(diff_text) > 2000:
                        # Truncate long diffs
                        preview = diff_text[:2000] + "...(truncated)"
                    else:
                        preview = diff_text
                    
                    lines.append("```diff")
                    lines.append(preview)
                    lines.append("```")
                    
                    # Summary of changes
                    line_changes = diff_details.get('line_changes', {})
                    added_lines = line_changes.get('added', [])
                    removed_lines = line_changes.get('removed', [])
                    
                    lines.append("")
                    lines.append(f"- Added lines: {len(added_lines)}")
                    lines.append(f"- Removed lines: {len(removed_lines)}")
                else:
                    lines.append("*Diff information could not be generated*")
            
            lines.append("")
        
        # Generate timestamp
        lines.append("---")
        lines.append("")
        lines.append(f"*Generated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(lines)
