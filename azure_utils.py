"""
Utility functions for working with Azure DevOps
"""

import re
from typing import Dict

def parse_azure_devops_url(url: str) -> Dict[str, str]:
    """
    Parse an Azure DevOps pull request URL to extract organization, project, repository, and PR ID.
    
    Args:
        url: The Azure DevOps pull request URL
        
    Returns:
        A dictionary containing organization, project, repository, and PR ID
        
    Raises:
        ValueError: If the URL is not a valid Azure DevOps pull request URL
    """
    # Match pattern for Azure DevOps PR URLs
    # https://dev.azure.com/{organization}/{project}/_git/{repository}/pullrequest/{pr_id}
    pattern = r"https://dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)/pullrequest/(\d+)"
    match = re.match(pattern, url)
    
    if not match:
        raise ValueError(
            "Invalid Azure DevOps PR URL. Expected format: "
            "https://dev.azure.com/{organization}/{project}/_git/{repository}/pullrequest/{pr_id}"
        )
    
    organization, project, repository, pr_id = match.groups()
    
    return {
        "organization": organization,
        "project": project,
        "repository": repository,
        "pr_id": int(pr_id)
    }

def is_valid_azure_pat(pat: str) -> bool:
    """
    Validate if a string is likely to be an Azure DevOps Personal Access Token.
    
    Args:
        pat: The string to validate
        
    Returns:
        True if the string matches the expected PAT format, False otherwise
    """
    # Azure DevOps PATs are typically long strings
    if len(pat) < 30:
        return False
    
    # They usually contain only alphanumeric characters, possibly with some symbols
    if not re.match(r'^[A-Za-z0-9\+/=]+$', pat):
        return False
    
    return True
