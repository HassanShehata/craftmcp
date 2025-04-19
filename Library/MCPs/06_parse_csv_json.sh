#!/bin/bash

#Token
TOKEN="YOUR_TOKEN_HERE"

#Step 1: Create MCP (ID = 6)
curl -X POST http://localhost:8000/create-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "parse-csv-json",
    "description": "Parse CSV or JSON string content into structured list.",
    "imports": ["import csv", "import json", "from io import StringIO"],
    "globals": {}
  }'

#Step 2: Create Tool (ID = 6)
curl -X POST http://localhost:8000/create-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "parse_file",
    "snippet": "    def flatten_json(y):\n        out = {}\n        def flatten(x, name=\"\"):\n            if type(x) is dict:\n                for a in x:\n                    flatten(x[a], f\"{name}{a}_\")\n            elif type(x) is list:\n                for i, a in enumerate(x):\n                    flatten(a, f\"{name}{i}_\")\n            else:\n                out[name[:-1]] = x\n        flatten(y)\n        return out\n\n    stream = StringIO(file_content)\n\n    if file_type == \"csv\":\n        return list(csv.DictReader(stream))\n    elif file_type == \"json\":\n        data = json.load(stream)\n        if isinstance(data, dict):\n            data = [data]\n        return [flatten_json(x) if flatten else x for x in data]\n    else:\n        return \"Unsupported file_type. Use 'csv' or 'json'.\"",
    "is_async": false,
    "params": {
      "file_content": { "type": "str" },
      "file_type": { "type": "str" },
      "flatten": { "type": "bool", "default": false }
    }
  }'

#Step 3: Link Tool ID 6 to MCP ID 6
curl -X POST http://localhost:8000/link-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_id": 6, "mcp_id": 6}'

#Step 4: Run MCP
curl -X POST http://localhost:8000/run-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mcp_id": 6}'

#Step 5: Inference - Parse CSV string
curl -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 6,
    "type": "tool",
    "name": "parse_file",
    "arguments": {
      "file_type": "csv",
      "file_content": "name,age\\nAlice,30\\nBob,25"
    }
  }'

#Step 6: Inference - Parse JSON string with flatten
curl -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 6,
    "type": "tool",
    "name": "parse_file",
    "arguments": {
      "file_type": "json",
      "file_content": "{\\"user\\":{\\"name\\":\\"alice\\",\\"roles\\":[\\"admin\\",\\"editor\\"]}}",
      "flatten": true
    }
  }'
