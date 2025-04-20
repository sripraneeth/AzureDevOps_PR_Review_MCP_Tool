#!/usr/bin/env python3
"""
MCP server for Azure DevOps PR Analysis with enhanced file comparison.
This version uses a modular API structure for better maintainability.
"""

import sys
import os
import traceback
from typing import Any, Dict, List
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Import our modular API package
from azure_api import get_client
from file_utils import get_file_manager

# Global variables
_mcp = None

def create_server():
    """
    Factory function that MCP calls to create the server.
    Returns a valid MCP server object.
    """
    global _mcp
    
    print("Starting Azure DevOps PR Analysis MCP Server with enhanced comparison", file=sys.stderr)
    print(f"Python version: {sys.version}", file=sys.stderr)
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Get Azure API client
        client = get_client()
        
        # Get file manager for saving analysis results
        file_manager = get_file_manager()
        
        # Create MCP server
        _mcp = FastMCP("azure_devops_pr_analysis")
        
        # Register MCP tools
        @_mcp.tool()
        async def fetch_azure_pr(organization: str, project: str, repository: str, pr_id: int) -> Dict[str, Any]:
            """Fetch changes from an Azure DevOps pull request."""
            print(f"Tool called: fetch_azure_pr for PR #{pr_id}", file=sys.stderr)
            return client.fetch_pr_changes(organization, project, repository, pr_id)
        
        @_mcp.tool()
        async def get_file_content(organization: str, project: str, repository: str, file_path: str, commit_id: str) -> str:
            """Get content of a specific file at a given commit."""
            print(f"Tool called: get_file_content for {file_path}", file=sys.stderr)
            return client.fetch_file_content(organization, project, repository, file_path, commit_id)
        
        @_mcp.tool()
        async def get_file_diff(organization: str, project: str, repository: str, pr_id: int, iteration_id: int, file_path: str) -> Dict[str, Any]:
            """Get diff for a specific file in a PR."""
            print(f"Tool called: get_file_diff for {file_path}", file=sys.stderr)
            return client.fetch_file_diff(organization, project, repository, pr_id, iteration_id, file_path)
        
        @_mcp.tool()
        async def compare_branch_files(organization: str, project: str, repository: str, 
                                      source_branch: str, target_branch: str, file_path: str) -> Dict[str, Any]:
            """Compare a file between source and target branches."""
            print(f"Tool called: compare_branch_files for {file_path}", file=sys.stderr)
            return client.compare_branch_files(organization, project, repository, source_branch, target_branch, file_path)
        
        @_mcp.tool()
        async def perform_enhanced_pr_review(organization: str, project: str, repository: str, pr_id: int) -> Dict[str, Any]:
            """Perform an enhanced PR review with direct branch comparison."""
            print(f"Tool called: perform_enhanced_pr_review for PR #{pr_id}", file=sys.stderr)
            result = client.perform_enhanced_pr_review(organization, project, repository, pr_id)
            
            # Automatically save the PR review to a file
            try:
                output_dir = os.getenv('OUTPUT_DIR', 'pr_analysis_results')
                # Use the PRReviewer directly to save the review
                from azure_api.pr_reviewer import PRReviewer
                pr_reviewer = PRReviewer(organization, project, repository)
                save_result = pr_reviewer.save_pr_review(pr_id, result, output_dir)
                print(f"Auto-save result: {save_result}", file=sys.stderr)
                
                # Add save result to the PR info
                result['save_result'] = save_result
            except Exception as e:
                print(f"Error auto-saving PR review: {str(e)}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                result['save_error'] = str(e)
            
            return result
        
        @_mcp.tool()
        async def get_branch_files(organization: str, project: str, repository: str, branch: str, path: str = None) -> List[Dict[str, Any]]:
            """Get all files in a branch, optionally filtered by path."""
            print(f"Tool called: get_branch_files for branch {branch}", file=sys.stderr)
            return client.get_branch_files(organization, project, repository, branch, path)
        
        @_mcp.tool()
        async def save_analysis_to_file(title: str, content: str) -> str:
            """Save PR analysis to a local text file."""
            print(f"Tool called: save_analysis_to_file for '{title}'", file=sys.stderr)
            output_dir = os.getenv('OUTPUT_DIR', 'pr_analysis_results')
            return file_manager.save_analysis(output_dir, title, content)
        
        print("Successfully registered all tools", file=sys.stderr)
        return _mcp
    
    except Exception as e:
        print(f"Error creating MCP server: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise

# If run directly, test the create_server function
if __name__ == "__main__":
    try:
        server = create_server()
        print("Server created successfully, running...", file=sys.stderr)
        server.run(transport="stdio")
    except Exception as e:
        print(f"Error running server: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
