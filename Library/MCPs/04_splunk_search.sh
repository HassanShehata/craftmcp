#!/bin/bash

#Token
TOKEN="YOUR_TOKEN_HERE"

#Step 1: Create MCP
curl -X POST http://localhost:8000/create-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "splunk-spl-search",
    "description": "Execute SPL query against Splunk API and return results.",
    "imports": ["import requests"],
    "globals": {
      "SPLUNK_HOST": "splunk.company.com",
      "SPLUNK_PORT": "8089",
      "SPLUNK_TOKEN": "your_splunk_token"
    }
  }'

#Step 2: Create Tool
curl -X POST http://localhost:8000/create-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "splunk_spl_search",
    "snippet": "    url = f\"https://{SPLUNK_HOST}:{SPLUNK_PORT}/services/search/jobs/export\"\n    headers = {\n        \"Authorization\": f\"Bearer {SPLUNK_TOKEN}\",\n        \"Content-Type\": \"application/x-www-form-urlencoded\"\n    }\n    data = {\"search\": f\"search {spl_query}\", \"output_mode\": \"json\"}\n    resp = requests.post(url, headers=headers, data=data, verify=False)\n    return resp.text",
    "is_async": false,
    "params": {
      "spl_query": { "type": "str" }
    }
  }'

#Step 3: Link Tool to MCP
curl -X POST http://localhost:8000/link-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_id": 4, "mcp_id": 4}'

#Step 4: Install Required Libraries
curl -X POST http://localhost:8000/install-library \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "requests"}'

#Step 5: Run MCP
curl -X POST http://localhost:8000/run-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mcp_id": 4}'

#Step 6: Inference Call
curl -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 4,
    "type": "tool",
    "name": "splunk_spl_search",
    "arguments": {
      "spl_query": "index=_internal | stats count by sourcetype"
    }
  }'
