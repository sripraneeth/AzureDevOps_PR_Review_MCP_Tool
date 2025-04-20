#!/usr/bin/env python3
"""
Standalone utility to compare a file between two branches in Azure DevOps.
This script uses multiple approaches to fetch file content, including direct GUID-based APIs.
"""

import sys
import os
import argparse
import json
from dotenv import load_dotenv

from azure_api.file_utils import FileManager
from azure_api.auth_utils import AuthUtils

def main():
    """Main function to run the file comparison."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Compare a file between two branches in Azure DevOps')
    parser.add_argument('--org', type=str, required=True, help='Azure DevOps organization name')
    parser.add_argument('--project', type=str, required=True, help='Azure DevOps project name')
    parser.add_argument('--repo', type=str, required=True, help='Azure DevOps repository name')
    parser.add_argument('--file', type=str, required=True, help='Path to the file to compare')
    parser.add_argument('--source', type=str, required=True, help='Source branch name')
    parser.add_argument('--target', type=str, required=True, help='Target branch name')
    parser.add_argument('--output', type=str, help='Output file path (optional)')
    parser.add_argument('--format', type=str, choices=['text', 'json'], default='text', 
                        help='Output format (text or json)')
    
    args = parser.parse_args()
    
    # Load environment variables for PAT
    load_dotenv()
    
    print(f"Comparing file '{args.file}' between branches '{args.source}' and '{args.target}'", file=sys.stderr)
    print(f"Repository: {args.org}/{args.project}/{args.repo}", file=sys.stderr)
    
    try:
        # Create file manager
        file_manager = FileManager(args.org, args.project, args.repo)
        
        # Fetch source content
        print(f"\nFetching source content from '{args.source}'...", file=sys.stderr)
        source_content = file_manager.fetch_content(args.file, args.source)
        
        if source_content.startswith("Error:"):
            print(f"Error fetching source content: {source_content}", file=sys.stderr)
            sys.exit(1)
            
        print(f"Successfully fetched source content ({len(source_content)} characters)", file=sys.stderr)
        
        # Fetch target content
        print(f"\nFetching target content from '{args.target}'...", file=sys.stderr)
        target_content = file_manager.fetch_content(args.file, args.target)
        
        if target_content.startswith("Error:"):
            print(f"Error fetching target content: {target_content}", file=sys.stderr)
            sys.exit(1)
            
        print(f"Successfully fetched target content ({len(target_content)} characters)", file=sys.stderr)
        
        # Compare the files
        print("\nComparing file contents...", file=sys.stderr)
        diff_text, line_changes = file_manager.compare_files_locally(
            source_content, 
            target_content, 
            f"{args.file} ({args.source})", 
            f"{args.file} ({args.target})"
        )
        
        # Print URLs to view the files in the web UI
        source_url = file_manager.fetch_direct_url(args.file, args.source)
        target_url = file_manager.fetch_direct_url(args.file, args.target)
        
        print(f"\nSource file URL: {source_url}", file=sys.stderr)
        print(f"Target file URL: {target_url}", file=sys.stderr)
        
        # Output the result
        if args.format == 'text':
            # Generate a summary
            summary = [
                f"File comparison: {args.file}",
                f"Source branch: {args.source}",
                f"Target branch: {args.target}",
                f"",
                f"Changes summary:",
                f"- Added lines: {len(line_changes['added'])}",
                f"- Removed lines: {len(line_changes['removed'])}",
                f"",
                f"Source URL: {source_url}",
                f"Target URL: {target_url}",
                f"",
                f"Diff:",
                diff_text
            ]
            
            result = "\n".join(summary)
            print(result)
            
            # Save to output file if specified
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"\nDiff saved to {args.output}", file=sys.stderr)
        else:
            # JSON format
            result = {
                "file": args.file,
                "source_branch": args.source,
                "target_branch": args.target,
                "source_url": source_url,
                "target_url": target_url,
                "diff": diff_text,
                "line_changes": {
                    "added": [{"line": line, "text": text} for line, text in line_changes["added"]],
                    "removed": [{"line": line, "text": text} for line, text in line_changes["removed"]]
                },
                "summary": {
                    "added_lines": len(line_changes["added"]),
                    "removed_lines": len(line_changes["removed"])
                }
            }
            
            print(json.dumps(result, indent=2))
            
            # Save to output file if specified
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
                print(f"\nJSON result saved to {args.output}", file=sys.stderr)
        
    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
