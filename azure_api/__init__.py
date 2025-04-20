"""
Azure DevOps API package for PR analysis.
This package provides interfaces for Azure DevOps API interactions with enhanced PR review capabilities.
"""

from .client import AzureDevOpsClient, get_client
from .pr_reviewer import PRReviewer
from .branch_utils import BranchManager
from .file_utils import FileManager
from .diff_utils import DiffManager
