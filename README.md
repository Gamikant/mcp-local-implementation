# MCP Local Implementation

A complete local implementation of the Model Context Protocol (MCP) with Ollama as the LLM backend, featuring research paper search, file operations, and mathematical calculations.

## 🚀 Quick Start

### Prerequisites

- **Python 3.10.11**
- **Ollama** ([Download here](https://ollama.ai))
- **8GB+ RAM** (16GB recommended)


### Installation

1. **Clone and setup**:
```bash
git clone https://github.com/yourusername/mcp_local_implementation.git
cd mcp_local_implementation
python3.10 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Install Ollama model**:
```bash
ollama pull llama3.2
ollama serve  # Keep running in background
```

3. **Run the chatbot**:
```bash
python chatbot/main.py
```


## 🎯 Usage

### Commands

- `tools` - Show available tools
- `debug` - Show server status
- `clear` - Clear conversation history
- `quit` - Exit


### Examples

```bash
# Research papers
You: search for papers on machine learning

# File operations  
You: list files in the current directory
You: read the requirements.txt file

# Math calculations
You: multiply 25 by 4.5
You: calculate square root of 144
```


## 📁 Project Structure

```
mcp_local_implementation/
├── chatbot/
│   ├── main.py              # Main application
│   ├── mcp_host.py          # MCP server management
│   └── ollama_client.py     # Ollama integration
├── mcp_servers/
│   ├── research_server.py   # ArXiv paper search
│   ├── file_server.py       # File operations
│   └── calculator_server.py # Math calculations
├── config/
│   └── mcp_config.json      # Configuration
├── requirements.txt
└── README.md
```


## 🔧 Troubleshooting

### Ollama not available

```bash
# Check if running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```


### ArXiv connection errors

This is normal due to rate limiting. The system includes automatic retry logic.

### Permission errors

```bash
chmod 755 data/ papers/ logs/
```


## ⚙️ Configuration

Edit `config/mcp_config.json` to change models or add servers:

```json
{
  "ollama": {
    "model": "llama3.2",
    "base_url": "http://localhost:11434"
  }
}
```


## 🌟 Features

- **Research Server**: Search academic papers from arXiv
- **File Server**: Read, write, list, delete files
- **Calculator Server**: Mathematical operations
- **Local LLM**: Uses Ollama with llama3.2
- **MCP Protocol**: Full JSON-RPC 2.0 compliance
- **Async Architecture**: Efficient multi-server handling

