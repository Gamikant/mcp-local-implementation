import asyncio
import json
import subprocess
import logging
import os
import aiohttp
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dotenv import load_dotenv
import ssl
import certifi

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class BaseMCPServer:
    """Base class for MCP servers"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.available_tools: List[Dict] = []
        self.initialized = False
    
    async def start(self):
        """Start the MCP server"""
        raise NotImplementedError
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
        """Call a tool on the MCP server"""
        raise NotImplementedError
    
    def stop(self):
        """Stop the MCP server"""
        raise NotImplementedError

class LocalMCPServer(BaseMCPServer):
    """Local MCP Server (subprocess-based)"""
    
    def __init__(self, name: str, command: str, args: List[str], description: str = ""):
        super().__init__(name, description)
        self.command = command
        self.args = args
        self.process: Optional[subprocess.Popen] = None
    
    async def start(self):
        """Start the local MCP server process"""
        try:
            cmd = [self.command] + self.args
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            logger.info(f"Started local MCP server: {self.name}")
            
            await asyncio.sleep(0.5)
            await self._initialize()
            
        except Exception as e:
            logger.error(f"Failed to start local MCP server {self.name}: {e}")
            raise
    
    async def _initialize(self):
        """Initialize the local MCP server"""
        try:
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "mcp-local-client", "version": "1.0.0"}
                }
            }
            
            response = await self._send_request(init_request)
            if response and "result" in response:
                self.initialized = True
                logger.info(f"Initialized local MCP server: {self.name}")
                
                # Send initialized notification
                await self._send_notification({"jsonrpc": "2.0", "method": "notifications/initialized"})
                
                # Get available tools
                await self._get_tools()
            else:
                logger.error(f"Failed to initialize {self.name}: {response}")
                
        except Exception as e:
            logger.error(f"Failed to initialize local MCP server {self.name}: {e}")
    
    async def _get_tools(self):
        """Get available tools from the local MCP server"""
        try:
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            response = await self._send_request(tools_request)
            if response and "result" in response:
                self.available_tools = response["result"].get("tools", [])
                logger.info(f"Got {len(self.available_tools)} tools from {self.name}: {[tool.get('name') for tool in self.available_tools]}")
            else:
                logger.warning(f"No tools result from {self.name}, response: {response}")
                
        except Exception as e:
            logger.error(f"Failed to get tools from {self.name}: {e}")
    
    async def _send_request(self, request: Dict) -> Optional[Dict]:
        """Send a JSON-RPC request to the local MCP server"""
        if not self.process or self.process.poll() is not None:
            logger.error(f"Local MCP server {self.name} is not running")
            return None
        
        try:
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
            
            await asyncio.sleep(0.1)
            
            response_str = self.process.stdout.readline()
            if response_str.strip():
                return json.loads(response_str.strip())
            else:
                logger.warning(f"Empty response from {self.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error communicating with local MCP server {self.name}: {e}")
            return None
    
    async def _send_notification(self, notification: Dict):
        """Send a JSON-RPC notification to the local MCP server"""
        if not self.process or self.process.poll() is not None:
            return
        
        try:
            notification_str = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_str)
            self.process.stdin.flush()
        except Exception as e:
            logger.error(f"Error sending notification to {self.name}: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
        """Call a tool on the local MCP server"""
        if not self.initialized:
            logger.error(f"Local server {self.name} not initialized")
            return None
            
        try:
            tool_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            logger.info(f"Sending tool request to {self.name}: {tool_request}")
            response = await self._send_request(tool_request)
            logger.info(f"Tool response from {self.name}: {response}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {self.name}: {e}")
            return None
    
    def stop(self):
        """Stop the local MCP server process"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            logger.info(f"Stopped local MCP server: {self.name}")

class RemoteMCPServer(BaseMCPServer):
    """Remote MCP Server (HTTP-based)"""
    
    def __init__(self, name: str, url: str, headers: Dict[str, str] = None, description: str = ""):
        super().__init__(name, description)
        self.url = url.rstrip('/')
        self.headers = headers or {}
        self.session: Optional[aiohttp.ClientSession] = None
        
        # In the RemoteMCPServer.__init__ method, update the header expansion:
        for key, value in self.headers.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                token_value = os.getenv(env_var, value)
                if token_value and token_value != value:
                    self.headers[key] = token_value
            elif isinstance(value, str) and "${" in value:
                # Handle template strings like "token ${GITHUB_TOKEN}"
                import re
                def replace_env_var(match):
                    env_var = match.group(1)
                    return os.getenv(env_var, match.group(0))
                
                self.headers[key] = re.sub(r'\$\{([^}]+)\}', replace_env_var, value)


    

    async def start(self):
        """Start the remote MCP server connection"""
        try:
            # Create proper SSL context with certifi certificates
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
            logger.info(f"Started remote MCP server: {self.name}")
            
            await self._initialize()
            
        except Exception as e:
            logger.error(f"Failed to start remote MCP server {self.name}: {e}")
            raise
    
    async def _initialize(self):
        """Initialize the remote MCP server"""
        try:
            # For GitHub MCP server, we'll assume it's initialized
            # In a real implementation, you'd send proper initialization requests
            self.initialized = True
            logger.info(f"Initialized remote MCP server: {self.name}")
            
            # Get available tools
            await self._get_tools()
            
        except Exception as e:
            logger.error(f"Failed to initialize remote MCP server {self.name}: {e}")
    
    async def _get_tools(self):
        """Get available tools from the remote MCP server"""
        try:
            # For GitHub MCP server, define known tools
            # In a real implementation, you'd query the server for available tools
            if "github" in self.name.lower():
                self.available_tools = [
                    {
                        "name": "get_repository",
                        "description": "Get repository information",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "owner": {"type": "string", "description": "Repository owner"},
                                "repo": {"type": "string", "description": "Repository name"}
                            },
                            "required": ["owner", "repo"]
                        }
                    },
                    {
                        "name": "list_files",
                        "description": "List files in repository",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "owner": {"type": "string", "description": "Repository owner"},
                                "repo": {"type": "string", "description": "Repository name"},
                                "path": {"type": "string", "description": "Path in repository", "default": ""}
                            },
                            "required": ["owner", "repo"]
                        }
                    },
                    {
                        "name": "get_file_content",
                        "description": "Get file content from repository",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "owner": {"type": "string", "description": "Repository owner"},
                                "repo": {"type": "string", "description": "Repository name"},
                                "path": {"type": "string", "description": "File path"}
                            },
                            "required": ["owner", "repo", "path"]
                        }
                    }
                ]
            
            logger.info(f"Got {len(self.available_tools)} tools from {self.name}: {[tool.get('name') for tool in self.available_tools]}")
            
        except Exception as e:
            logger.error(f"Failed to get tools from {self.name}: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
        """Call a tool on the remote MCP server"""
        if not self.initialized or not self.session:
            logger.error(f"Remote server {self.name} not initialized")
            return None
        
        try:
            # For GitHub MCP server, implement specific tool calls
            if "github" in self.name.lower():
                return await self._call_github_tool(tool_name, arguments)
            else:
                # Generic remote tool call
                return await self._call_generic_tool(tool_name, arguments)
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {self.name}: {e}")
            return None
    
    async def _call_github_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
        """Call GitHub-specific tools"""
        try:
            if tool_name == "get_repository":
                owner = arguments.get("owner")
                repo = arguments.get("repo")
                
                async with self.session.get(f"https://api.github.com/repos/{owner}/{repo}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "result": {
                                "content": [{
                                    "type": "text",
                                    "text": json.dumps(data, indent=2)
                                }]
                            }
                        }
                    else:
                        return {
                            "error": {
                                "code": response.status,
                                "message": f"GitHub API error: {response.status}"
                            }
                        }
            
            elif tool_name == "list_files":
                owner = arguments.get("owner")
                repo = arguments.get("repo")
                path = arguments.get("path", "")
                
                url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list):
                            files = [item["name"] for item in data]
                        else:
                            files = [data["name"]]
                        
                        return {
                            "result": {
                                "content": [{
                                    "type": "text",
                                    "text": json.dumps(files, indent=2)
                                }]
                            }
                        }
                    else:
                        return {
                            "error": {
                                "code": response.status,
                                "message": f"GitHub API error: {response.status}"
                            }
                        }
            
            elif tool_name == "get_file_content":
                owner = arguments.get("owner")
                repo = arguments.get("repo")
                path = arguments.get("path")
                
                url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("type") == "file":
                            import base64
                            content = base64.b64decode(data["content"]).decode('utf-8')
                            return {
                                "result": {
                                    "content": [{
                                        "type": "text",
                                        "text": content
                                    }]
                                }
                            }
                        else:
                            return {
                                "error": {
                                    "code": -1,
                                    "message": "Path is not a file"
                                }
                            }
                    else:
                        return {
                            "error": {
                                "code": response.status,
                                "message": f"GitHub API error: {response.status}"
                            }
                        }
            
            return {
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }
            
        except Exception as e:
            return {
                "error": {
                    "code": -32603,
                    "message": f"Tool execution error: {str(e)}"
                }
            }
    
    async def _call_generic_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
        """Call generic remote tools"""
        try:
            # Generic implementation for other remote MCP servers
            payload = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            async with self.session.post(f"{self.url}/tools/call", json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "error": {
                            "code": response.status,
                            "message": f"Remote server error: {response.status}"
                        }
                    }
                    
        except Exception as e:
            return {
                "error": {
                    "code": -32603,
                    "message": f"Tool execution error: {str(e)}"
                }
            }
    
    def stop(self):
        """Stop the remote MCP server connection"""
        if self.session:
            asyncio.create_task(self.session.close())
            logger.info(f"Stopped remote MCP server: {self.name}")

class EnhancedMCPHost:
    """Enhanced MCP Host that manages both local and remote MCP servers"""
    
    def __init__(self, config_path: str = "config/mcp_config.json"):
        self.config_path = config_path
        self.servers: Dict[str, BaseMCPServer] = {}
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    async def start_all_servers(self):
        """Start all configured MCP servers"""
        mcp_servers_config = self.config.get("mcp_servers", {})
        
        for name, server_config in mcp_servers_config.items():
            try:
                server_type = server_config.get("type", "local")
                
                if server_type == "remote":
                    # Create remote server
                    server = RemoteMCPServer(
                        name=name,
                        url=server_config["url"],
                        headers=server_config.get("headers", {}),
                        description=server_config.get("description", "")
                    )
                else:
                    # Create local server
                    server = LocalMCPServer(
                        name=name,
                        command=server_config["command"],
                        args=server_config["args"],
                        description=server_config.get("description", "")
                    )
                
                await server.start()
                self.servers[name] = server
                
            except Exception as e:
                logger.error(f"Failed to start server {name}: {e}")
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
        """Call a tool on a specific MCP server"""
        if server_name not in self.servers:
            logger.error(f"Server {server_name} not found")
            return None
        
        return await self.servers[server_name].call_tool(tool_name, arguments)
    
    def get_available_tools(self) -> Dict[str, List[Dict]]:
        """Get all available tools from all servers"""
        tools = {}
        for name, server in self.servers.items():
            tools[name] = server.available_tools
        return tools
    
    def stop_all_servers(self):
        """Stop all MCP servers"""
        for server in self.servers.values():
            server.stop()
        self.servers.clear()
