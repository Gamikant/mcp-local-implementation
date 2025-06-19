import asyncio
import json
import subprocess
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class MCPServer:
    """Represents an MCP Server instance"""
    
    def __init__(self, name: str, command: str, args: List[str], description: str = ""):
        self.name = name
        self.command = command
        self.args = args
        self.description = description
        self.process: Optional[subprocess.Popen] = None
        self.available_tools: List[Dict] = []
        self.initialized = False
    
    async def start(self):
        """Start the MCP server process"""
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
            logger.info(f"Started MCP server: {self.name}")
            
            # Wait a moment for the server to start
            await asyncio.sleep(0.5)
            
            # Initialize the server
            await self._initialize()
            
        except Exception as e:
            logger.error(f"Failed to start MCP server {self.name}: {e}")
            raise
    
    async def _initialize(self):
        """Initialize the MCP server"""
        try:
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "mcp-local-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            response = await self._send_request(init_request)
            if response and "result" in response:
                self.initialized = True
                logger.info(f"Initialized MCP server: {self.name}")
                
                # Send initialized notification
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                await self._send_notification(initialized_notification)
                
                # Get available tools
                await self._get_tools()
            else:
                logger.error(f"Failed to initialize {self.name}: {response}")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server {self.name}: {e}")
    
    async def _get_tools(self):
        """Get available tools from the MCP server"""
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
        """Send a JSON-RPC request to the MCP server"""
        if not self.process or self.process.poll() is not None:
            logger.error(f"MCP server {self.name} is not running")
            return None
        
        try:
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
            
            # Wait for response
            await asyncio.sleep(0.1)
            
            # Read response
            response_str = self.process.stdout.readline()
            if response_str.strip():
                return json.loads(response_str.strip())
            else:
                logger.warning(f"Empty response from {self.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error communicating with MCP server {self.name}: {e}")
            return None
    
    async def _send_notification(self, notification: Dict):
        """Send a JSON-RPC notification to the MCP server"""
        if not self.process or self.process.poll() is not None:
            return
        
        try:
            notification_str = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_str)
            self.process.stdin.flush()
        except Exception as e:
            logger.error(f"Error sending notification to {self.name}: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
        """Call a tool on the MCP server"""
        if not self.initialized:
            logger.error(f"Server {self.name} not initialized")
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
        """Stop the MCP server process"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            logger.info(f"Stopped MCP server: {self.name}")

class MCPHost:
    """MCP Host that manages multiple MCP servers"""
    
    def __init__(self, config_path: str = "config/mcp_config.json"):
        self.config_path = config_path
        self.servers: Dict[str, MCPServer] = {}
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
                server = MCPServer(
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
