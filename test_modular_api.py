#!/usr/bin/env python3
"""
Test script to demonstrate the use of the modular Azure DevOps API.
"""

import sys
import argparse
import json
from dotenv import load_dotenv

# Import our modular API package
from azure_api import get_client
from azure_api.branch_utils import BranchManager
from azure_api.file_utils import FileManager
from azure_api.diff_utils import DiffManager
from azure_api.pr_reviewer import PRReviewer

def main():
    """Main function for testing the modular API."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test the modular Azure DevOps API')
    parser.add_argument('--org', type=str, required=True, help='Azure DevOps organization')
    parser.add_argument('--project', type=str, required=True, help='Azure DevOps project')
    parser.add_argument('--repo', type=str, required=True, help='Azure DevOps repository')
    parser.add_argument('--pr', type=int, help='Pull Request ID for PR operations')
    parser.add_argument('--branch', type=str, help='Branch name for branch operations')
    parser.add_argument('--file', type=str, help='File path for file operations')
    parser.add_argument('--target', type=str, help='Target branch for compare operations')
    parser.add_argument('--commit', type=str, help='Commit ID for file content operations')
    parser.add_argument('--action', type=str, required=True, choices=[
        'pr_changes', 'enhanced_review', 'branch_files', 'file_content', 
        'compare_branches', 'branch_commit'
    ], help='Action to perform')
    parser.add_argument('--output', type=str, help='Output file path for analysis')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get client
    client = get_client()
    
    try:
        # Perform the requested action
        if args.action == 'pr_changes':
            if not args.pr:
                print("Error: PR ID is required for 'pr_changes' action", file=sys.stderr)
                return 1
            
            print(f"Fetching changes for PR #{args.pr} in {args.org}/{args.project}/{args.repo}", file=sys.stderr)
            result = client.fetch_pr_changes(args.org, args.project, args.repo, args.pr)
            
        elif args.action == 'enhanced_review':
            if not args.pr:
                print("Error: PR ID is required for 'enhanced_review' action", file=sys.stderr)
                return 1
            
            print(f"Performing enhanced review for PR #{args.pr} in {args.org}/{args.project}/{args.repo}", file=sys.stderr)
            result = client.perform_enhanced_pr_review(args.org, args.project, args.repo, args.pr)
            
        elif args.action == 'branch_files':
            if not args.branch:
                print("Error: Branch name is required for 'branch_files' action", file=sys.stderr)
                return 1
            
            print(f"Fetching files for branch '{args.branch}' in {args.org}/{args.project}/{args.repo}", file=sys.stderr)
            result = client.get_branch_files(args.org, args.project, args.repo, args.branch, args.file)
            
        elif args.action == 'file_content':
            if not args.file or not (args.commit or args.branch):
                print("Error: File path and commit ID or branch name are required for 'file_content' action", file=sys.stderr)
                return 1
            
            commit_or_branch = args.commit or args.branch
            print(f"Fetching content for file '{args.file}' at '{commit_or_branch}' in {args.org}/{args.project}/{args.repo}", file=sys.stderr)
            result = client.fetch_file_content(args.org, args.project, args.repo, args.file, commit_or_branch)
            
        elif args.action == 'compare_branches':
            if not args.file or not args.branch or not args.target:
                print("Error: File path, source branch, and target branch are required for 'compare_branches' action", file=sys.stderr)
                return 1
            
            print(f"Comparing file '{args.file}' between branches '{args.branch}' and '{args.target}' in {args.org}/{args.project}/{args.repo}", file=sys.stderr)
            result = client.compare_branch_files(args.org, args.project, args.repo, args.branch, args.target, args.file)
            
        elif args.action == 'branch_commit':
            if not args.branch:
                print("Error: Branch name is required for 'branch_commit' action", file=sys.stderr)
                return 1
            
            print(f"Getting latest commit for branch '{args.branch}' in {args.org}/{args.project}/{args.repo}", file=sys.stderr)
            # Create a direct branch manager to test this specific method
            branch_manager = BranchManager(args.org, args.project, args.repo)
            result = branch_manager.get_latest_commit(args.branch)
            
        else:
            print(f"Error: Unknown action '{args.action}'", file=sys.stderr)
            return 1
        
        # Output the result
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        elif isinstance(result, list):
            print(json.dumps(result, indent=2))
        else:
            print(result)
        
        # Save to output file if specified
        if args.output and isinstance(result, dict):
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to {args.output}", file=sys.stderr)
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
