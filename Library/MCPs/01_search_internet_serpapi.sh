#!/bin/bash

# Replace this token with a valid user token
TOKEN="YOUR_TOKEN_HERE"


# Step 0: Install dependancy
curl -X POST 'http://localhost:8000/install-library' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "google-search-results"}'



# Step 1: Create MCP
curl -X POST http://localhost:8000/create-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SerpAPI_Search_Internet",
    "description": "Search the Internet using SerpAPI as a tool",
    "imports": ["from serpapi import GoogleSearch"],
    "globals": {
      "SERP_API_KEY": "YOUR_SERP_API_KEY_HERE"
    }
  }'


# Step 2: Create Tool
curl -X POST http://localhost:8000/create-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "google_search",
    "snippet": "    search = GoogleSearch({\"q\": query, \"api_key\": SERP_API_KEY})\n    results = search.get_dict()\n    if 'error' in results:\n        return \"API Error: {}\".format(results['error'])\n    organic = results.get('organic_results', [])\n    output = []\n    for r in organic[:max_results]:\n        output.append(\"{}: {}\".format(r['title'], r['link']))\n    return \"\\n\".join(output)",
    "is_async": false,
    "mcp_id": 1,
    "params": {
      "query": {"type": "str"},
      "max_results": {"type": "int", "default": 3}
    }
  }'

# Step 3: Link Tool if not linked on creation
curl -X POST http://localhost:8000/link-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_id": 1, "mcp_id": 1}'

# Step 4: Run MCP
curl -X POST http://localhost:8000/run-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mcp_id": 1}'

# Step 5: Infere via tool
curl -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 1,
    "type": "tool",
    "name": "google_search",
    "arguments": {
      "query": "what is model context protocol",
      "max_results": 3
    }
  }'