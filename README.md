# Azure DevOps PR Reviewer

A modular API for Azure DevOps pull request analysis with enhanced comparison between source and target branches.

## Overview

This tool provides a more accurate PR review process by directly comparing files between source and destination branches rather than relying solely on the PR's diff information, which can sometimes be inconsistent.

## Features

- Enhanced PR review with direct branch comparison
- Handles branches with special names (like those containing slashes)
- Reliable file content retrieval with fallback mechanisms
- Detailed diff analysis with line-level change tracking
- Modular architecture for easier maintenance and extension

## Structure

The codebase has been refactored into a modular package structure:

```
azure_api/
├── __init__.py          # Package exports
├── auth_utils.py        # Authentication utilities
├── branch_utils.py      # Branch operations
├── client.py            # Main client interface
├── diff_utils.py        # Diff generation and analysis
├── file_utils.py        # File operations
├── http_utils.py        # HTTP request handling
└── pr_reviewer.py       # PR review operations
```

Each module focuses on a specific set of related functionality, with clear separation of concerns.

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create an `.env` file with your Azure DevOps Personal Access Token:
   ```
   AZURE_PAT=your_personal_access_token
   OUTPUT_DIR=path_to_save_analysis_results
   ```

## Usage

### As a standalone tool

```bash
python test_modular_api.py --org "YourOrg" --project "YourProject" --repo "YourRepo" --pr 123 --action enhanced_review
```

### As an MCP server

```bash
python azure_pr_mcp.py
```

## API Examples

### Enhanced PR Review

For the most thorough PR review, the `perform_enhanced_pr_review` method offers comprehensive comparison:

```python
from azure_api import get_client

client = get_client()
pr_info = client.perform_enhanced_pr_review("OrganizationName", "ProjectName", "RepositoryName", pr_id=123)
```

This will:
1. Fetch PR metadata
2. Extract source and target branch information
3. Get the latest commits from both branches
4. Retrieve all changed files
5. Compare file contents directly between branches
6. Generate detailed diffs

### Using individual components

The modular structure allows direct use of specific components:

```python
from azure_api.branch_utils import BranchManager
from azure_api.file_utils import FileManager
from azure_api.diff_utils import DiffManager

# Work with branches
branch_manager = BranchManager("OrganizationName", "ProjectName", "RepositoryName")
commit_id = branch_manager.get_latest_commit("feature/my-branch")

# Work with files
file_manager = FileManager("OrganizationName", "ProjectName", "RepositoryName")
content = file_manager.fetch_content("/path/to/file.cs", commit_id)

# Compare files
diff_manager = DiffManager("OrganizationName", "ProjectName", "RepositoryName")
comparison = diff_manager.compare_files("feature/my-branch", "main", "/path/to/file.cs")
```

## Troubleshooting

If you encounter 404 errors when fetching file content, make sure:

1. The file path is correct (case-sensitive)
2. The branch name or commit ID is valid
3. Your PAT has sufficient permissions

The tool has built-in fallback mechanisms that attempt different API approaches when the standard approach fails.

## License

MIT
