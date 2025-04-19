#!/bin/bash

#Token
TOKEN="YOUR_TOKEN_HERE"

#Step 1: Create MCP
curl -X POST http://localhost:8000/create-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "prompt-ollama",
    "description": "Use Ollama API to generate a response using provided prompt and model.",
    "imports": ["import requests", "import json"],
    "globals": {
      "OLLAMA_HOST": "localhost or YOUR_OLLAMA_IP",
      "OLLAMA_PORT": "11434"
    }
  }'

#Step 2: Create Tool
curl -X POST http://localhost:8000/create-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "prompt_ollama",
    "snippet": "    response = requests.post(f\"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/chat\", json={\"model\": model, \"messages\": [{\"role\": \"user\", \"content\": prompt}]})\n    lines = response.text.strip().splitlines()\n    output = []\n    for line in lines:\n        try:\n            obj = json.loads(line)\n            if \"message\" in obj and \"content\" in obj[\"message\"]:\n                output.append(obj[\"message\"][\"content\"])\n        except Exception:\n            continue\n    return \"\".join(output) if output else \"No response returned.\"",
    "is_async": false,
    "params": {
      "model": {"type": "str"},
      "prompt": {"type": "str"}
    }
  }'


#Step 3: Link Tool to MCP
curl -X POST http://localhost:8000/link-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_id": 2, "mcp_id": 2}'

#Step 4: Install `requests` (if not already installed)
curl -X POST http://localhost:8000/install-library \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "requests"}'

#Step 5: Run MCP
curl -X POST http://localhost:8000/run-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mcp_id": 2}'

#Step 6: Inference Call
curl -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 2,
    "type": "tool",
    "name": "prompt_ollama",
    "arguments": {
      "model": "mistral",
      "prompt": "summarize the latest OWASP API Top 10"
    }
  }'
