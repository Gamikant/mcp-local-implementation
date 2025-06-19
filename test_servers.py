#!/usr/bin/env python3
import subprocess
import json
import time

def test_server(server_path, server_name):
    print(f"\n=== Testing {server_name} ===")
    
    try:
        process = subprocess.Popen(
            ['python3', server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        
        # Initialize
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        process.stdin.write(json.dumps(init_msg) + "\n")
        process.stdin.flush()
        
        time.sleep(0.5)
        init_response = process.stdout.readline()
        print(f"Initialize: {init_response.strip()}")
        
        # Send initialized notification
        init_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        process.stdin.write(json.dumps(init_notification) + "\n")
        process.stdin.flush()
        
        # List tools
        tools_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        process.stdin.write(json.dumps(tools_msg) + "\n")
        process.stdin.flush()
        
        time.sleep(0.5)
        tools_response = process.stdout.readline()
        print(f"Tools: {tools_response.strip()}")
        
        process.terminate()
        process.wait(timeout=5)
        
    except Exception as e:
        print(f"Error testing {server_name}: {e}")
        if 'process' in locals():
            process.kill()

if __name__ == "__main__":
    test_server("mcp_servers/research_server.py", "Research Server")
    test_server("mcp_servers/file_server.py", "File Server") 
    test_server("mcp_servers/calculator_server.py", "Calculator Server")
