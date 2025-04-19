#!/bin/bash

#Token (use is as env variable on run time or as you wish!)
TOKEN="YOUR_TOKEN_HERE"

#Step 1: Create MCP
curl -X POST http://localhost:8000/create-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "check-vt",
    "description": "Check reputation of a file hash or IP address using VirusTotal API.",
    "imports": ["import requests"],
    "globals": {
      "VT_API_KEY": "YOUR_VT_TOKEN"
    }
  }'

#Step 2: Create Tool
curl -X POST http://localhost:8000/create-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "check_vt",
    "snippet": "    headers = {\"x-apikey\": VT_API_KEY}\n    if hash:\n        url = f\"https://www.virustotal.com/api/v3/files/{hash}\"\n    elif ip:\n        url = f\"https://www.virustotal.com/api/v3/ip_addresses/{ip}\"\n    else:\n        return \"Error: Provide either hash or ip\"\n    res = requests.get(url, headers=headers)\n    data = res.json()\n    score = data.get(\"data\", {}).get(\"attributes\", {}).get(\"last_analysis_stats\", {})\n    return str(score)",
    "is_async": false,
    "params": {
      "hash": { "type": "str", "default": "" },
      "ip": { "type": "str", "default": "" }
    }
  }'

#Step 3: Link Tool to MCP
curl -X POST http://localhost:8000/link-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_id": 3, "mcp_id": 3}'

#Step 4: Run MCP
curl -X POST http://localhost:8000/run-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mcp_id": 3}'

#Step 5: Inference with a hash
curl -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 3,
    "type": "tool",
    "name": "check_vt",
    "arguments": {
      "hash": "44d88612fea8a8f36de82e1278abb02f"
    }
  }'

#Step 6: Inference with an IP
curl -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 3,
    "type": "tool",
    "name": "check_vt",
    "arguments": {
      "ip": "8.8.8.8"
    }
  }'
