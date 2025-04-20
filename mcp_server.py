#!/usr/bin/env python3
"""
MCP server for Azure DevOps PR Analysis.
This module handles the MCP server functionality to integrate with Claude Desktop.
"""

import sys
import os
import traceback
from typing import Any, Dict
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Import our modules
from azure_api import get_client
from file_utils import get_file_manager

class AzurePRAnalysisMCP:
    """MCP server for Azure DevOps PR Analysis."""
    
    def __init__(self):
        """Initialize the MCP server."""
        # Load environment variables
        load_dotenv()
        
        # Create MCP server
        self.mcp = FastMCP("azure_devops_pr_analysis")
        
        # Initialize dependencies
        self.azure_client = get_client()
        self.file_manager = get_file_manager()
        
        # Register MCP tools
        self._register_tools()
    
    def _register_tools(self):
        """Register MCP tools for Azure DevOps PR analysis."""
        
        @self.mcp.tool()
        async def fetch_azure_pr(organization: str, project: str, repository: str, pr_id: int) -> Dict[str, Any]:
            """Fetch changes from an Azure DevOps pull request."""
            print(f"Tool called: fetch_azure_pr for PR #{pr_id}", file=sys.stderr)
            return self.azure_client.fetch_pr_changes(organization, project, repository, pr_id)
        
        @self.mcp.tool()
        async def get_file_content(organization: str, project: str, repository: str, file_path: str, commit_id: str) -> str:
            """Get content of a specific file at a given commit."""
            print(f"Tool called: get_file_content for {file_path}", file=sys.stderr)
            return self.azure_client.fetch_file_content(organization, project, repository, file_path, commit_id)
        
        @self.mcp.tool()
        async def get_file_diff(organization: str, project: str, repository: str, pr_id: int, iteration_id: int, file_path: str) -> Dict[str, Any]:
            """Get diff for a specific file in a PR."""
            print(f"Tool called: get_file_diff for {file_path}", file=sys.stderr)
            return self.azure_client.fetch_file_diff(organization, project, repository, pr_id, iteration_id, file_path)
        
        @self.mcp.tool()
        async def save_analysis_to_file(title: str, content: str) -> str:
            """Save PR analysis to a local text file."""
            print(f"Tool called: save_analysis_to_file for '{title}'", file=sys.stderr)
            return self.file_manager.save_analysis(title, content)
    
    def run(self):
        """Start the MCP server."""
        try:
            print("Running MCP Server for Azure DevOps PR Analysis...", file=sys.stderr)
            self.mcp.run(transport="stdio")
        except Exception as e:
            print(f"Error running MCP server: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)

# Factory function for Claude Desktop MCP integration
def create_server():
    """Factory function to create the MCP server instance."""
    try:
        print("Creating Azure DevOps PR Analysis MCP server...", file=sys.stderr)
        return AzurePRAnalysisMCP().mcp
    except Exception as e:
        print(f"Error creating MCP server: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise

# Run the server if executed directly
if __name__ == "__main__":
    try:
        print("==== Starting Azure DevOps PR Analysis MCP Server ====", file=sys.stderr)
        print(f"Python version: {sys.version}", file=sys.stderr)
        print(f"Current working directory: {os.getcwd()}", file=sys.stderr)
        print(f"Script path: {__file__}", file=sys.stderr)
        
        server = AzurePRAnalysisMCP()
        server.run()
    except Exception as e:
        print(f"Fatal error: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
