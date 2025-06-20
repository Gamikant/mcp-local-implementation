import asyncio
import json
import logging
from pathlib import Path
from ollama_client import OllamaClient
from mcp_host import EnhancedMCPHost

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mcp_local.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MCPChatbot:
    """Main chatbot class that integrates Ollama with MCP servers"""
    
    def __init__(self):
        self.ollama = OllamaClient()
        self.mcp_host = EnhancedMCPHost()
        self.conversation_history = []
    
    async def initialize(self):
        """Initialize the chatbot and MCP servers"""
        logger.info("Initializing MCP Chatbot...")
        
        # Check if Ollama is available
        if not self.ollama.is_available():
            logger.error("Ollama is not available. Please ensure it's running with: ollama run llama3.2")
            return False
        
        # Start MCP servers
        await self.mcp_host.start_all_servers()
        
        # Wait a moment for servers to fully initialize
        await asyncio.sleep(1)
        
        logger.info("MCP Chatbot initialized successfully!")
        return True
    
    async def _handle_tool_call(self, tool_call: dict) -> str:
        """Handle tool call from LLM response"""
        try:
            server = tool_call.get("server", "").lower()
            tool = tool_call.get("tool")
            arguments = tool_call.get("arguments", {})
            
            logger.info(f"Calling tool {tool} on server {server} with args: {arguments}")
            
            result = await self.mcp_host.call_tool(server, tool, arguments)
            logger.info(f"Raw tool result: {result}")
            
            if result and "result" in result:
                # Extract the actual content from MCP response
                content = result["result"]
                if isinstance(content, dict) and "content" in content:
                    # Handle MCP content format
                    if isinstance(content["content"], list) and len(content["content"]) > 0:
                        text_content = content["content"][0].get("text", str(content))
                        return f"Tool executed successfully. Result: {text_content}"
                    else:
                        return f"Tool executed successfully. Result: {content}"
                else:
                    return f"Tool executed successfully. Result: {json.dumps(content, indent=2)}"
            elif result and "error" in result:
                error_msg = result["error"].get("message", "Unknown error")
                logger.error(f"Tool call error: {error_msg}")
                return f"Tool call failed with error: {error_msg}"
            else:
                logger.warning(f"Unexpected tool result format: {result}")
                return f"Tool call completed but returned unexpected result: {result}"
                
        except Exception as e:
            logger.error(f"Error handling tool call: {e}")
            return f"Error executing tool: {e}"

    def _create_system_prompt(self) -> str:
        """Create system prompt with available tools"""
        tools = self.mcp_host.get_available_tools()
        
        if not any(tools.values()):
            return """You are an AI assistant. The MCP servers are connected but no tools are currently available. 
    Please respond normally to user queries without attempting to use tools."""
        
        prompt = """You are an AI assistant with access to various tools through MCP servers.

    Available tools:
    """
        
        for server_name, server_tools in tools.items():
            if server_tools:
                prompt += f"\n{server_name.upper()} SERVER:\n"
                for tool in server_tools:
                    prompt += f"- {tool.get('name', 'unknown')}: {tool.get('description', 'No description')}\n"
        
        prompt += """
        CRITICAL RULES:
        - ALWAYS use "use_tool" as the action value
        - Use EXACT server names: research, file, calculator, github
        - Use EXACT tool names as listed above
        - For research papers, use parameter "topic"
        - For math operations, use parameters like "a", "b", "base", "exponent", etc.
        - For file operations, use "directory", "filename", "content" as needed
        - For GitHub operations, use "owner" and "repo" parameters (NOT "repository")
        - NEVER provide explanatory text with the JSON - ONLY return the JSON object

        Examples:
        - For "list files": {"action": "use_tool", "server": "file", "tool": "list_files", "arguments": {}}
        - For "multiply 3 and 4": {"action": "use_tool", "server": "calculator", "tool": "multiply", "arguments": {"a": 3, "b": 4}}
        - For "search papers on AI": {"action": "use_tool", "server": "research", "tool": "search_papers", "arguments": {"topic": "AI"}}
        - For "list files in my repo": {"action": "use_tool", "server": "github", "tool": "list_files", "arguments": {"owner": "Gamikant", "repo": "mcp-local-implementation"}}

        Otherwise, respond normally to the user's query.
        """

        return prompt

    
    async def chat(self, user_input: str) -> str:
        """Process user input and generate response"""
        try:
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Create messages for Ollama
            messages = [
                {"role": "system", "content": self._create_system_prompt()}
            ] + self.conversation_history[-10:]  # Keep last 10 messages
            
            # Get response from Ollama
            response = self.ollama.chat(messages)
            
            # Check if response contains a tool call
            try:
                if response.strip().startswith('{') and '"action": "use_tool"' in response:
                    tool_call = json.loads(response.strip())
                    tool_result = await self._handle_tool_call(tool_call)
                    
                    # Get final response from Ollama with tool result
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": f"Tool result: {tool_result}. Please provide a natural language response to the user based on this result."})
                    
                    final_response = self.ollama.chat(messages)
                    self.conversation_history.append({"role": "assistant", "content": final_response})
                    return final_response
                else:
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
                    
            except json.JSONDecodeError:
                # Not a tool call, return response as is
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
                
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"Sorry, I encountered an error: {e}"
    
    async def run_interactive(self):
        """Run interactive chat loop"""
        print("🤖 MCP Chatbot is ready! Type 'quit' to exit.")
        print("Available commands:")
        print("- 'tools' - Show available tools")
        print("- 'debug' - Show debug information")
        print("- 'clear' - Clear conversation history")
        print()
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    break
                elif user_input.lower() == 'tools':
                    tools = self.mcp_host.get_available_tools()
                    print("\n📋 Available Tools:")
                    for server_name, server_tools in tools.items():
                        print(f"\n{server_name.upper()}:")
                        if server_tools:
                            for tool in server_tools:
                                print(f"  - {tool.get('name', 'unknown')}: {tool.get('description', 'No description')}")
                        else:
                            print("  - No tools available")
                    print()
                    continue
                elif user_input.lower() == 'debug':
                    print(f"\n🔍 Debug Info:")
                    print(f"Available servers: {list(self.mcp_host.servers.keys())}")
                    for name, server in self.mcp_host.servers.items():
                        status = "initialized" if server.initialized else "not initialized"
                        print(f"Server '{name}': {status}, {len(server.available_tools)} tools")
                    print()
                    continue
                elif user_input.lower() == 'clear':
                    self.conversation_history.clear()
                    print("🧹 Conversation history cleared!")
                    continue
                elif not user_input:
                    continue
                
                response = await self.chat(user_input)
                print(f"Bot: {response}\n")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in interactive loop: {e}")
                print(f"Error: {e}\n")
    
    async def cleanup(self):
        """Cleanup resources"""
        self.mcp_host.stop_all_servers()
        logger.info("Chatbot cleanup completed")

async def main():
    """Main function"""
    chatbot = MCPChatbot()
    
    try:
        # Initialize
        if not await chatbot.initialize():
            return
        
        # Run interactive chat
        await chatbot.run_interactive()
        
    finally:
        await chatbot.cleanup()

if __name__ == "__main__":
    # Ensure required directories exist
    Path("logs").mkdir(exist_ok=True)
    Path("papers").mkdir(exist_ok=True)    
    asyncio.run(main())
