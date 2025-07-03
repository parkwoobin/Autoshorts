#!/usr/bin/env python3
"""
Storyboard Generation Prototype - Main Runner
This script manages the FastAPI server and the interactive client using a command-line interface.
"""

import subprocess
import time
import sys
import os
import argparse
from pathlib import Path

# --- Helper Functions ---

def run_command(command, **kwargs):
    """Runs a command in a subprocess, handling common exceptions."""
    try:
        return subprocess.Popen(command, text=True, **kwargs)
    except FileNotFoundError:
        print(f"❌ Error: Command not found. Is '{command[0]}' installed and in your PATH?")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return None

# --- Core Actions ---

def start_server():
    """Starts the FastAPI server using Uvicorn and returns the process."""
    print("🚀 Starting FastAPI server (http://localhost:8000)...")
    command = [sys.executable, "-m", "uvicorn", "client:app", "--host", "0.0.0.0", "--port", "8000"]
    
    process = run_command(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not process:
        return None

    # Wait a moment and check if the server started successfully
    time.sleep(3)
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        print("❌ Failed to start server. Error:")
        print(stderr or stdout)
        return None
        
    print("✅ Server started successfully.")
    return process

def start_client():
    """Starts the interactive test client."""
    print("🎮 Starting interactive client...")
    if not Path("test_client.py").exists():
        print("❌ 'test_client.py' not found.")
        return
        
    command = [sys.executable, "test_client.py"]
    # For the client, we run it directly and wait for it to complete
    try:
        subprocess.run(command, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Client interrupted by user.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Client exited with an error: {e}")


def check_requirements():
    """Checks for the presence of required files."""
    missing_files = []
    if not Path("client.py").exists():
        missing_files.append("client.py")
    if not Path("test_client.py").exists():
        missing_files.append("test_client.py")
    if not Path("requirements.txt").exists():
        missing_files.append("requirements.txt")

    if missing_files:
        print("❌ The following required files are missing:")
        for file in missing_files:
            print(f"  - {file}")
        return False

    return True

def install_dependencies():
    """Installs dependencies from requirements.txt."""
    print("📦 Checking and installing dependencies...")
    if not Path("requirements.txt").exists():
        print("⚠️ 'requirements.txt' not found. Skipping installation.")
        return

    command = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    try:
        # We wait for this command to finish
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("✅ Dependencies are up to date.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages:\n{e.stderr}")

# --- Main Execution Logic ---

def main():
    """Parses command-line arguments and executes the corresponding command."""
    # Set the working directory to the script's directory
    os.chdir(Path(__file__).parent.resolve())

    parser = argparse.ArgumentParser(
        description="Storyboard Generation Prototype Runner",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Server Command ---
    subparsers.add_parser("server", help="Start the FastAPI server only.")

    # --- Client Command ---
    subparsers.add_parser("client", help="Start the interactive test client only.")

    # --- Run Command ---
    subparsers.add_parser("run", help="Start both the server and the client for development.")

    # --- Install Command ---
    subparsers.add_parser("install", help="Install or update dependencies from requirements.txt.")

    args = parser.parse_args()

    # Check for required files, but allow 'install' to run anyway
    if args.command != 'install' and not check_requirements():
        print("❌ Cannot proceed until required files are present.")
        return

    try:
        if args.command == "server":
            server_process = start_server()
            if server_process:
                print("\n✅ Server is running. Press Ctrl+C to stop.")
                server_process.wait()
        
        elif args.command == "client":
            start_client()
            
        elif args.command == "run":
            server_process = start_server()
            if server_process:
                try:
                    print("\n🚀 Starting client in 3 seconds...")
                    time.sleep(3)
                    start_client()
                finally:
                    print("\n🛑 Stopping server...")
                    server_process.terminate()
                    
        elif args.command == "install":
            install_dependencies()

    except KeyboardInterrupt:
        print("\n\n🛑 Program interrupted by user. Exiting.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
