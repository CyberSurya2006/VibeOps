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
    Connects to the local running VibeOps FastAPI dev server.
    """
    url = "http://localhost:8000/api/chat"
    headers = {
        "Content-Type": "application/json",
        "X-Gemini-API-Key": api_key
    }
    payload = {"message": query}
    
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    if response.status_code == 200:
        return response.json().get("reply", "No response content.")
    else:
        detail = response.json().get("detail", "Unknown error")
        raise RuntimeError(f"Backend error: {detail}")

def query_locally(query: str, api_key: str) -> str:
    """
    Fallback: imports the agents locally if the FastAPI server is offline.
    """
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from backend.agents import run_multi_agent_system
    return run_multi_agent_system(api_key, query)

def main():
    parser = argparse.ArgumentParser(
        description="VibeOps CLI: Terminal agent skill for automating builds, tests, and security audits."
    )
    parser.add_argument(
        "query",
        type=str,
        nargs="?",
        help="The natural language question (e.g. 'run tests', 'stage modifications', 'scan keys')."
    )
    parser.add_argument(
        "--api-key",
        "-k",
        type=str,
        help="Your Gemini API Key. Can also be set via the GEMINI_API_KEY environment variable."
    )
    
    args = parser.parse_args()
    
    if not args.query:
        print("VibeOps Developer Operations CLI")
        print("-" * 35)
        try:
            query = input("Ask VibeOps Agent > ").strip()
            if not query:
                print("Exiting: No query specified.")
                return
        except (KeyboardInterrupt, EOFError):
            print("\nExited.")
            return
    else:
        query = args.query
        
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: Gemini API Key not specified.")
        print("Please set the GEMINI_API_KEY environment variable, pass it via --api-key (-k),")
        print("or save it in a .env file in this directory.")
        return
        
    print(f"\nRouting query to dev-ops agents: '{query}'")
    print("Hold on while the agents audit your project...\n")
    
    # Attempt to query backend first
    try:
        reply = query_via_backend(query, api_key)
        print("=== RESPONSE (via VibeOps Server) ===")
        print(reply)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # Fallback to local agent modules
        try:
            reply = query_locally(query, api_key)
            print("=== RESPONSE (via Standalone Local Agents) ===")
            print(reply)
        except ImportError as e:
            print("Error: FastAPI server is offline, and local agent modules could not be loaded.")
            print(f"Details: {str(e)}")
            print("Please run start-vibeops.bat to start the system.")
        except Exception as e:
            print(f"Error during execution: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
