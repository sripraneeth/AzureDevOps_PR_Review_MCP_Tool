#!/usr/bin/env python3
"""
Utility functions for file operations.
"""

import os
import sys
import datetime
import traceback
from pathlib import Path
from typing import Optional

class FileManager:
    """Manages file operations for PR analysis."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize with the output directory for file operations."""
        self.output_dir = output_dir or os.getenv('OUTPUT_DIR', 'pr_analysis_results')
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """Ensure the output directory exists."""
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                print(f"Created output directory: {self.output_dir}", file=sys.stderr)
            else:
                print(f"Using existing output directory: {self.output_dir}", file=sys.stderr)
        except Exception as e:
            print(f"Error ensuring output directory: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
    
    def save_analysis(self, title: str, content: str) -> str:
        """Save PR analysis to a file and return the filepath."""
        # Sanitize the title to create a valid filename
        safe_title = "".join([c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in title])
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        print(f"Saving analysis to file: {filepath}", file=sys.stderr)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            success_msg = f"Analysis saved successfully to {filepath}"
            print(success_msg, file=sys.stderr)
            return success_msg
        except Exception as e:
            error_msg = f"Error saving analysis to file: {str(e)}"
            print(error_msg, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return error_msg
    
    def get_output_dir(self) -> str:
        """Get the current output directory path."""
        return self.output_dir
    
    def set_output_dir(self, output_dir: str) -> None:
        """Set a new output directory and ensure it exists."""
        self.output_dir = output_dir
        self._ensure_output_dir()

# Singleton instance for easy importing
def get_file_manager():
    """Get or create the FileManager singleton instance."""
    if not hasattr(get_file_manager, 'instance'):
        get_file_manager.instance = FileManager()
    return get_file_manager.instance
