#!/usr/bin/env python3
import sys
import json
import os
from typing import List, Dict, Any

# Add error handling for arxiv import
try:
    import arxiv
    ARXIV_AVAILABLE = True
except ImportError as e:
    ARXIV_AVAILABLE = False
    print(f"Warning: arxiv not available: {e}", file=sys.stderr)

# Ensure papers directory exists
PAPER_DIR = "papers"
os.makedirs(PAPER_DIR, exist_ok=True)

class ResearchServer:
    def __init__(self):
        self.initialized = False
        self.tools = [
            {
                "name": "search_papers",
                "description": "Search for papers on arXiv based on a topic",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "The topic to search for"},
                        "max_results": {"type": "integer", "description": "Maximum number of results", "default": 5}
                    },
                    "required": ["topic"]
                }
            },
            {
                "name": "extract_info",
                "description": "Get information about a specific paper by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "paper_id": {"type": "string", "description": "The ID of the paper"}
                    },
                    "required": ["paper_id"]
                }
            }
        ]
    
    def search_papers(self, topic: str, max_results: int = 5) -> str:
        """Search for papers on arXiv"""
        if not ARXIV_AVAILABLE:
            return "Error: arxiv library not available. Please install with: pip install arxiv"

        import time
        import random
        
        max_retries = 3
        base_delay = 3  # arXiv requires 3 second delays
        
        for attempt in range(max_retries):
            try:
                # Add delay to respect arXiv rate limits
                if attempt > 0:
                    delay = base_delay + random.uniform(1, 3)  # Add jitter
                    time.sleep(delay)
                
                client = arxiv.Client()
                search = arxiv.Search(
                    query=topic,
                    max_results=max_results,
                    sort_by=arxiv.SortCriterion.Relevance
                )
                
                papers = client.results(search)
                
                # Create directory for this topic
                path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
                os.makedirs(path, exist_ok=True)
                file_path = os.path.join(path, "papers_info.json")
                
                # Load existing papers info
                try:
                    with open(file_path, "r") as f:
                        papers_info = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    papers_info = {}
                
                # Process papers
                paper_ids = []
                for paper in papers:
                    paper_id = paper.get_short_id()
                    paper_ids.append(paper_id)
                    
                    paper_info = {
                        'title': paper.title,
                        'authors': [author.name for author in paper.authors],
                        'summary': paper.summary[:500] + "..." if len(paper.summary) > 500 else paper.summary,
                        'pdf_url': paper.pdf_url,
                        'published': str(paper.published.date())
                    }
                    
                    papers_info[paper_id] = paper_info
                
                # Save papers info
                with open(file_path, "w") as f:
                    json.dump(papers_info, f, indent=2)
                
                return f"Found {len(paper_ids)} papers: {', '.join(paper_ids)}"
                
            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    return f"Error searching papers after {max_retries} attempts: {str(e)}"
                else:
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying...", file=sys.stderr)
                    continue

    
    def extract_info(self, paper_id: str) -> str:
        """Get information about a specific paper"""
        try:
            for item in os.listdir(PAPER_DIR):
                item_path = os.path.join(PAPER_DIR, item)
                if os.path.isdir(item_path):
                    file_path = os.path.join(item_path, "papers_info.json")
                    if os.path.isfile(file_path):
                        try:
                            with open(file_path, "r") as f:
                                papers_info = json.load(f)
                            if paper_id in papers_info:
                                return json.dumps(papers_info[paper_id], indent=2)
                        except (FileNotFoundError, json.JSONDecodeError):
                            continue
            
            return f"No information found for paper {paper_id}"
            
        except Exception as e:
            return f"Error extracting info: {str(e)}"
    
    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC message (request or notification)"""
        method = message.get("method")
        
        # Handle notifications (no response needed)
        if "id" not in message:
            if method == "notifications/initialized":
                self.initialized = True
            return None  # No response for notifications
        
        # Handle requests (response needed)
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "research-server",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "tools": self.tools
                }
            }
        
        elif method == "tools/call":
            params = message.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            try:
                if tool_name == "search_papers":
                    result = self.search_papers(**arguments)
                elif tool_name == "extract_info":
                    result = self.extract_info(**arguments)
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }
                
                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": str(result)
                            }
                        ]
                    }
                }
                
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {
                        "code": -32603,
                        "message": f"Tool execution error: {str(e)}"
                    }
                }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Unknown method: {method}"
                }
            }

def main():
    try:
        server = ResearchServer()
        
        for line in sys.stdin:
            try:
                message = json.loads(line.strip())
                response = server.handle_message(message)
                
                # Only send response if it's not None (i.e., not a notification)
                if response is not None:
                    print(json.dumps(response))
                    sys.stdout.flush()
                    
            except json.JSONDecodeError:
                continue
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
                
    except Exception as e:
        print(f"Fatal error in research server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
