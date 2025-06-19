# MCP Local Implementation

A local implementation of Model Context Protocol (MCP) with Ollama as the LLM backend.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Ensure Ollama is installed and running: `ollama run llama3.2`
3. Run the chatbot: `python chatbot/main.py`

## Features

- Research paper search via arXiv
- File operations
- Calculator functions
- Local MCP server/client architecture

## Usage

- Type 'tools' to see available tools
- Type 'debug' to see server status
- Type 'clear' to clear conversation history
- Type 'quit' to exit
