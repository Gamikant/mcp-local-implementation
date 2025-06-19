#!/usr/bin/env python3
import sys
import json
import os
from pathlib import Path
from typing import List, Dict, Any

# Use current working directory as default
DEFAULT_DIR = "."

class FileServer:
    def __init__(self):
        self.initialized = False
        self.tools = [
            {
                "name": "list_files",
                "description": "List files in a directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Directory to list", "default": DEFAULT_DIR}
                    }
                }
            },
            {
                "name": "read_file",
                "description": "Read contents of a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Name of the file to read"},
                        "directory": {"type": "string", "description": "Directory containing the file", "default": DEFAULT_DIR}
                    },
                    "required": ["filename"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Name of the file to write"},
                        "content": {"type": "string", "description": "Content to write"},
                        "directory": {"type": "string", "description": "Directory to write to", "default": DEFAULT_DIR}
                    },
                    "required": ["filename", "content"]
                }
            },
            {
                "name": "delete_file",
                "description": "Delete a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Name of the file to delete"},
                        "directory": {"type": "string", "description": "Directory containing the file", "default": DEFAULT_DIR}
                    },
                    "required": ["filename"]
                }
            }
        ]
    
    def list_files(self, directory: str = DEFAULT_DIR) -> List[str]:
        """List files in directory"""
        try:
            if directory.startswith("~"):
                directory = os.path.expanduser(directory)
            
            path = Path(directory)
            if not path.exists():
                return [f"Directory {directory} does not exist"]
            
            if not path.is_dir():
                return [f"{directory} is not a directory"]
            
            files = []
            for item in path.iterdir():
                if item.is_file():
                    files.append(str(item.name))
                elif item.is_dir():
                    files.append(f"{item.name}/")
            
            if not files:
                return [f"Directory {directory} is empty"]
            
            return sorted(files)
        except Exception as e:
            return [f"Error listing files: {str(e)}"]
    
    def read_file(self, filename: str, directory: str = DEFAULT_DIR) -> str:
        """Read file contents"""
        try:
            file_path = Path(directory) / filename
            if not file_path.exists():
                return f"File {filename} not found in {directory}"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def write_file(self, filename: str, content: str, directory: str = DEFAULT_DIR) -> str:
        """Write content to file"""
        try:
            dir_path = Path(directory)
            dir_path.mkdir(parents=True, exist_ok=True)
            
            file_path = dir_path / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"Successfully wrote to {filename}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    def delete_file(self, filename: str, directory: str = DEFAULT_DIR) -> str:
        """Delete a file"""
        try:
            file_path = Path(directory) / filename
            if not file_path.exists():
                return f"File {filename} not found in {directory}"
            
            file_path.unlink()
            return f"Successfully deleted {filename}"
        except Exception as e:
            return f"Error deleting file: {str(e)}"
    
    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC message"""
        method = message.get("method")
        
        # Handle notifications
        if "id" not in message:
            if method == "notifications/initialized":
                self.initialized = True
            return None
        
        # Handle requests
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "file-server", "version": "1.0.0"}
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {"tools": self.tools}
            }
        
        elif method == "tools/call":
            params = message.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            try:
                if tool_name == "list_files":
                    result = self.list_files(**arguments)
                elif tool_name == "read_file":
                    result = self.read_file(**arguments)
                elif tool_name == "write_file":
                    result = self.write_file(**arguments)
                elif tool_name == "delete_file":
                    result = self.delete_file(**arguments)
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                    }
                
                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {
                        "content": [{"type": "text", "text": str(result)}]
                    }
                }
                
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {"code": -32603, "message": f"Tool execution error: {str(e)}"}
                }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            }

def main():
    try:
        server = FileServer()
        
        for line in sys.stdin:
            try:
                message = json.loads(line.strip())
                response = server.handle_message(message)
                
                if response is not None:
                    print(json.dumps(response))
                    sys.stdout.flush()
                    
            except json.JSONDecodeError:
                continue
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
                
    except Exception as e:
        print(f"Fatal error in file server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
