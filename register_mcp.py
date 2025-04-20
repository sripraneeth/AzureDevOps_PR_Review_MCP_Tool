#!/usr/bin/env python3
"""
Script to register the Azure DevOps PR Analysis tool with Claude Desktop.
"""

import os
import sys
import json
import shutil
from pathlib import Path

def find_claude_config_path():
    """Get the Claude config directory based on platform."""
    if sys.platform == "win32":
        path = Path(Path.home(), "AppData", "Roaming", "Claude")
    elif sys.platform == "darwin":
        path = Path(Path.home(), "Library", "Application Support", "Claude")
    elif sys.platform.startswith("linux"):
        path = Path(
            os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"), "Claude"
        )
    else:
        return None

    if path.exists():
        return path
    return None

def setup_environment():
    """Set up the environment configuration."""
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir / ".env"
    env_example_path = script_dir / ".env.example"
    
    env_vars = {}
    
    # Create .env file if it doesn't exist
    if not env_path.exists() and env_example_path.exists():
        shutil.copy(env_example_path, env_path)
        print(f"Created .env file from example template")
    
    # Read existing .env file or create new one
    if env_path.exists():
        print(f"Loading environment variables from {env_path}")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
                    except ValueError:
                        print(f"Warning: Ignoring invalid line in .env file: {line}")
    
    # Prompt for required variables if missing
    if 'AZURE_PAT' not in env_vars or not env_vars['AZURE_PAT'] or env_vars['AZURE_PAT'] == 'your_personal_access_token_here':
        azure_pat = input("Enter your Azure DevOps Personal Access Token (PAT): ")
        env_vars['AZURE_PAT'] = azure_pat
    
    if 'OUTPUT_DIR' not in env_vars or not env_vars['OUTPUT_DIR'] or env_vars['OUTPUT_DIR'] == 'pr_analysis_results':
        default_dir = "pr_analysis_results"
        output_dir = input(f"Enter output directory path (or press Enter for default '{default_dir}'): ")
        env_vars['OUTPUT_DIR'] = output_dir if output_dir else default_dir
    
    # Write updated environment variables back to .env file
    with open(env_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    # Create output directory if it doesn't exist
    output_dir_path = script_dir / env_vars['OUTPUT_DIR']
    if not output_dir_path.exists():
        os.makedirs(output_dir_path)
        print(f"Created output directory: {output_dir_path}")
    
    return env_vars

def register_tool():
    """Register the Azure DevOps PR Analysis tool with Claude Desktop."""
    print("==== Registering Azure DevOps PR Analysis Tool ====")
    
    # Set up environment
    env_vars = setup_environment()
    
    # Get the Claude Desktop config directory
    config_dir = find_claude_config_path()
    if not config_dir:
        print("Error: Claude Desktop config directory not found.")
        print("Please ensure Claude Desktop is installed and has been run at least once.")
        return False
    
    print(f"Found Claude Desktop config directory: {config_dir}")
    
    # Get the config file
    config_file = config_dir / "claude_desktop_config.json"
    if not config_file.exists():
        print("Error: Claude Desktop config file not found.")
        print("Please ensure Claude Desktop has been run at least once.")
        return False
    
    print(f"Found Claude Desktop config file: {config_file}")
    
    # Read the current config
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error reading Claude Desktop config: {str(e)}")
        return False
    
    # Get the script directory
    script_dir = Path(__file__).resolve().parent
    
    # Use the new azure_pr_mcp.py file that uses the modular API structure
    server_name = "Azure DevOps PR Analysis"
    script_path = script_dir / "azure_pr_mcp.py"
    
    # Ensure the path exists
    if not script_path.exists():
        print(f"Error: The MCP server script file does not exist: {script_path}")
        return False
    
    print(f"Using MCP server script: {script_path}")
    
    # Create the MCP server config
    server_config = {
        "command": "python",  # Use python directly
        "args": [
            str(script_path)  # Just run the script directly
        ],
        "env": env_vars
    }
    
    # Update the config
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Add our server
    config["mcpServers"][server_name] = server_config
    
    # Save the config
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Successfully registered {server_name} with Claude Desktop!")
        print("\nYou can now use this tool in Claude Desktop by:")
        print("1. Restart Claude Desktop if it's currently running")
        print("2. Open Claude Desktop and type a prompt like:")
        print('   "Analyze this Azure DevOps PR: https://dev.azure.com/organization/project/_git/repository/pullrequest/123"')
        return True
    except Exception as e:
        print(f"Error writing Claude Desktop config: {str(e)}")
        return False

if __name__ == "__main__":
    success = register_tool()
    if not success:
        sys.exit(1)
