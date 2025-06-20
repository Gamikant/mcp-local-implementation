# MCP Local Implementation - System Design

## High-Level Design (HLD)

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Local Implementation                     │
├─────────────────────────────────────────────────────────────────┤
│  User Interface Layer                                          │
│  ┌─────────────────┐                                          │
│  │ Interactive CLI │ ← User Commands                          │
│  └─────────────────┘                                          │
│           │                                                    │
│  ┌─────────────────┐                                          │
│  │   MCPChatbot    │ ← Main Orchestrator                     │
│  │   (main.py)     │                                          │
│  └─────────────────┘                                          │
│           │                                                    │
│  ┌─────────────────┐    ┌─────────────────┐                  │
│  │  Ollama Client  │    │    MCP Host     │                  │
│  │ (ollama_client) │    │  (mcp_host.py)  │                  │
│  └─────────────────┘    └─────────────────┘                  │
│           │                       │                           │
│  ┌─────────────────┐    ┌─────────────────┐                  │
│  │ Ollama Server   │    │  MCP Servers    │                  │
│  │ (llama3.2)      │    │   (3 servers)   │                  │
│  └─────────────────┘    └─────────────────┘                  │
│                                   │                           │
│                          ┌─────────────────┐                  │
│                          │ External APIs   │                  │
│                          │ (arXiv, Files)  │                  │
│                          └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```


### Architecture Components

#### 1. **User Interface Layer**

- **Interactive CLI**: Command-line interface for user interaction
- **Built-in Commands**: tools, debug, clear, quit
- **Natural Language Processing**: Converts user queries to tool calls


#### 2. **Application Layer**

- **MCPChatbot**: Main orchestrator managing conversation flow
- **Conversation Management**: Maintains chat history and context
- **Tool Call Detection**: Identifies when to use MCP tools vs. normal chat


#### 3. **Integration Layer**

- **Ollama Client**: Interface to local LLM (llama3.2)
- **MCP Host**: Manages multiple MCP servers and tool routing
- **Protocol Handler**: JSON-RPC 2.0 communication management


#### 4. **Service Layer**

- **Research Server**: arXiv paper search and information extraction
- **File Server**: Local file system operations
- **Calculator Server**: Mathematical computations


#### 5. **External Dependencies**

- **Ollama Runtime**: Local LLM execution environment
- **arXiv API**: Academic paper repository
- **Local File System**: File storage and retrieval


### Data Flow

```
User Input → MCPChatbot → System Prompt → Ollama → Tool Call Detection
     ↓
Tool Execution → MCP Server → External API/Local Resource → Response
     ↓
Result Processing → Natural Language Response → User Output
```


## Low-Level Design (LLD)

### Class Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      MCPChatbot                                │
├─────────────────────────────────────────────────────────────────┤
│ - ollama: OllamaClient                                         │
│ - mcp_host: MCPHost                                            │
│ - conversation_history: List[Dict]                             │
├─────────────────────────────────────────────────────────────────┤
│ + initialize() → bool                                          │
│ + chat(user_input: str) → str                                  │
│ + _handle_tool_call(tool_call: dict) → str                     │
│ + _create_system_prompt() → str                                │
│ + run_interactive() → None                                     │
│ + cleanup() → None                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OllamaClient                              │
├─────────────────────────────────────────────────────────────────┤
│ - base_url: str                                                │
│ - model: str                                                   │
│ - session: requests.Session                                    │
├─────────────────────────────────────────────────────────────────┤
│ + generate(prompt: str, system_prompt: str) → str              │
│ + chat(messages: List[Dict]) → str                             │
│ + is_available() → bool                                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        MCPHost                                 │
├─────────────────────────────────────────────────────────────────┤
│ - config_path: str                                             │
│ - servers: Dict[str, MCPServer]                                │
│ - config: Dict                                                 │
├─────────────────────────────────────────────────────────────────┤
│ + start_all_servers() → None                                   │
│ + call_tool(server: str, tool: str, args: Dict) → Dict         │
│ + get_available_tools() → Dict[str, List[Dict]]                │
│ + stop_all_servers() → None                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ manages
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCPServer                                 │
├─────────────────────────────────────────────────────────────────┤
│ - name: str                                                    │
│ - command: str                                                 │
│ - args: List[str]                                              │
│ - process: subprocess.Popen                                    │
│ - available_tools: List[Dict]                                  │
│ - initialized: bool                                            │
├─────────────────────────────────────────────────────────────────┤
│ + start() → None                                               │
│ + _initialize() → None                                         │
│ + _get_tools() → None                                          │
│ + call_tool(tool_name: str, arguments: Dict) → Dict            │
│ + _send_request(request: Dict) → Dict                          │
│ + _send_notification(notification: Dict) → None               │
│ + stop() → None                                                │
└─────────────────────────────────────────────────────────────────┘
```


### Individual Server Designs

#### Research Server

```
┌─────────────────────────────────────────────────────────────────┐
│                   ResearchServer                               │
├─────────────────────────────────────────────────────────────────┤
│ - initialized: bool                                            │
│ - tools: List[Dict] = [search_papers, extract_info]            │
├─────────────────────────────────────────────────────────────────┤
│ + search_papers(topic: str, max_results: int) → str            │
│ + extract_info(paper_id: str) → str                            │
│ + handle_message(message: Dict) → Dict                         │
│ + main() → None                                                │
└─────────────────────────────────────────────────────────────────┘
```


#### File Server

```
┌─────────────────────────────────────────────────────────────────┐
│                     FileServer                                │
├─────────────────────────────────────────────────────────────────┤
│ - initialized: bool                                            │
│ - tools: List[Dict] = [list_files, read_file, write_file,      │
│                       delete_file]                             │
├─────────────────────────────────────────────────────────────────┤
│ + list_files(directory: str) → List[str]                       │
│ + read_file(filename: str, directory: str) → str               │
│ + write_file(filename: str, content: str, directory: str) → str │
│ + delete_file(filename: str, directory: str) → str             │
│ + handle_message(message: Dict) → Dict                         │
│ + main() → None                                                │
└─────────────────────────────────────────────────────────────────┘
```


#### Calculator Server

```
┌─────────────────────────────────────────────────────────────────┐
│                  CalculatorServer                              │
├─────────────────────────────────────────────────────────────────┤
│ - initialized: bool                                            │
│ - tools: List[Dict] = [add, subtract, multiply, divide,        │
│                       power, square_root]                      │
├─────────────────────────────────────────────────────────────────┤
│ + add(a: float, b: float) → float                              │
│ + subtract(a: float, b: float) → float                         │
│ + multiply(a: float, b: float) → float                         │
│ + divide(a: float, b: float) → float                           │
│ + power(base: float, exponent: float) → float                  │
│ + square_root(number: float) → float                           │
│ + handle_message(message: Dict) → Dict                         │
│ + main() → None                                                │
└─────────────────────────────────────────────────────────────────┘
```


### Communication Protocol

#### JSON-RPC 2.0 Message Flow

```
1. Initialization Sequence:
   Client → Server: {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {...}}
   Server → Client: {"jsonrpc": "2.0", "id": 1, "result": {...}}
   Client → Server: {"jsonrpc": "2.0", "method": "notifications/initialized"}

2. Tool Discovery:
   Client → Server: {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
   Server → Client: {"jsonrpc": "2.0", "id": 2, "result": {"tools": [...]}}

3. Tool Execution:
   Client → Server: {"jsonrpc": "2.0", "id": 3, "method": "tools/call", 
                    "params": {"name": "tool_name", "arguments": {...}}}
   Server → Client: {"jsonrpc": "2.0", "id": 3, "result": {"content": [...]}}
```


### Data Models

#### Tool Schema

```python
{
    "name": str,
    "description": str,
    "inputSchema": {
        "type": "object",
        "properties": Dict[str, Any],
        "required": List[str]
    }
}
```


#### Tool Call Schema

```python
{
    "action": "use_tool",
    "server": str,
    "tool": str,
    "arguments": Dict[str, Any]
}
```


#### Configuration Schema

```python
{
    "ollama": {
        "base_url": str,
        "model": str,
        "timeout": int
    },
    "mcp_servers": Dict[str, {
        "command": str,
        "args": List[str],
        "description": str
    }],
    "logging": {
        "level": str,
        "file": str
    }
}
```


### Error Handling Strategy

#### Error Types and Handling

```python
1. Connection Errors:
   - Ollama unavailable → Graceful shutdown with user message
   - MCP server crash → Log error, continue with remaining servers
   - arXiv API timeout → Retry with exponential backoff

2. Protocol Errors:
   - Invalid JSON-RPC → Return parse error response
   - Unknown method → Return method not found error
   - Tool execution error → Return execution error with details

3. Application Errors:
   - File not found → Return descriptive error message
   - Division by zero → Return mathematical error
   - Permission denied → Return access error
```


### Performance Considerations

#### Optimization Strategies

```
1. Asynchronous Operations:
   - MCP server communication uses asyncio
   - Non-blocking I/O for file operations
   - Concurrent tool execution where possible

2. Resource Management:
   - Process lifecycle management for MCP servers
   - Memory-efficient conversation history (last 10 messages)
   - Lazy loading of large datasets

3. Caching:
   - Tool discovery results cached per server
   - Configuration loaded once at startup
   - Session reuse for HTTP connections
```

