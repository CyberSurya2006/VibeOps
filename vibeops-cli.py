#!/usr/bin/env python3
import sys
import os
import argparse
import requests
from dotenv import load_dotenv

# Load local environment variables if a .env file exists
load_dotenv()

def query_via_backend(query: str, api_key: str) -> str:
    """
    Attempts to communicate with the local running VibeOps FastAPI server.
    """
    url = "http://localhost:8000/api/chat"
    headers = {
        "Content-Type": "application/json",
        "X-Gemini-API-Key": api_key
    }
    payload = {"message": query}
    
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    if response.status_code == 200:
        return response.json().get("reply", "No response content.")
    else:
        detail = response.json().get("detail", "Unknown error")
        raise RuntimeError(f"Backend error: {detail}")

def query_locally(query: str, api_key: str) -> str:
    """
    Fallback: runs the multi-agent logic locally without a running FastAPI server.
    """
    # Adjust path so we can import from backend
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from backend.agents import run_multi_agent_system
    
    return run_multi_agent_system(api_key, query)

def main():
    parser = argparse.ArgumentParser(
        description="VibeOps CLI: Command-line developer agent skill for workspace & system diagnostics."
    )
    parser.add_argument(
        "query",
        type=str,
        nargs="?",
        help="The natural language question or request to send to the developer agents."
    )
    parser.add_argument(
        "--api-key",
        "-k",
        type=str,
        help="Your Gemini API Key. Can also be set via the GEMINI_API_KEY environment variable."
    )
    
    args = parser.parse_args()
    
    # Prompt if query is empty
    if not args.query:
        print("VibeOps Terminal Skill (CLI)")
        print("-" * 30)
        try:
            query = input("Ask VibeOps Agent > ").strip()
            if not query:
                print("Exiting: No query provided.")
                return
        except (KeyboardInterrupt, EOFError):
            print("\nExited.")
            return
    else:
        query = args.query
        
    # Determine API key
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Check if we have a key in local .env or config files
        print("Error: Gemini API Key not specified.")
        print("Please set the GEMINI_API_KEY environment variable, pass it via --api-key (-k),")
        print("or save it in a .env file in this directory.")
        return
        
    print(f"\nRouting query to VibeOps agents: '{query}'")
    print("Hold on while the agents inspect your workspace...\n")
    
    # Attempt to query backend first
    try:
        reply = query_via_backend(query, api_key)
        print("=== RESPONSE (via VibeOps Server) ===")
        print(reply)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # Fallback to local agent run
        try:
            reply = query_locally(query, api_key)
            print("=== RESPONSE (via Standalone Local Agents) ===")
            print(reply)
        except ImportError as e:
            print("Error: FastAPI server is offline, and local agent modules could not be loaded.")
            print(f"Details: {str(e)}")
            print("Please run uvicorn or start-vibeops.bat to start the system.")
        except Exception as e:
            print(f"Error during execution: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
