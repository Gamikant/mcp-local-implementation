<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

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


## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/name`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/name`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built for local AI enthusiasts** 🤖

<div style="text-align: center">⁂</div>

[^1]: calculator_server.py

[^2]: file_server.py

[^3]: research_server.py

[^4]: main.py

[^5]: mcp_host.py

[^6]: ollama_client.py

[^7]: requirements.txt

[^8]: mcp_config.json

[^9]: https://github.com/punkpeye/awesome-mcp-servers

[^10]: https://www.youtube.com/watch?v=StgbwIQH-C4

[^11]: https://github.com/patruff/ollama-mcp-bridge/blob/main/README.md

[^12]: https://www.reddit.com/r/ollama/comments/1kiw05t/built_a_simple_way_to_oneclick_install_and/

[^13]: https://dev.to/auyeungdavid_2847435260/step-by-step-guide-just-minutes-build-an-mcp-server-and-client-interacting-with-ollama-in-c-906

[^14]: https://www.youtube.com/watch?v=aiH79Q-LGjY

[^15]: https://github.com/QuantGeekDev/mcp-framework/issues/91

[^16]: https://blog.stackademic.com/build-simple-local-mcp-server-5434d19572a4?gi=8346020ff770

[^17]: https://ubos.tech/mcp/mcp-ollama-server/

[^18]: https://ubos.tech/mcp/mcp-server-basic-example-2/

