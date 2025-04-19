#!/bin/bash

#Token
TOKEN="YOUR_TOKEN_HERE"

#Step 1: Run SPL query on Splunk (MCP ID 4) and extract top 3 source IPs
splunk_output=$(curl -s -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 4,
    "type": "tool",
    "name": "splunk_spl_search",
    "arguments": {
      "spl_query": "index=threats | top limit=3 src_ip"
    }
  }' | jq -r '.result')

echo -e "\nTop SPL Output:\n$splunk_output"

#Step 2: Extract IPs from the output (assumes JSON lines)
top_ips=$(echo "$splunk_output" | jq -r '.results[]?.src_ip' 2>/dev/null | head -n 3)

echo -e "\nExtracted IPs:\n$top_ips"

#Step 3: Check VT for each IP (MCP ID 3) and accumulate results
vt_reports=""
for ip in $top_ips; do
  vt_result=$(curl -s -X POST http://localhost:8000/infere-mcp \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"mcp_id\": 3,
      \"type\": \"tool\",
      \"name\": \"check_vt\",
      \"arguments\": { \"ip\": \"$ip\" }
    }" | jq -r '.result')
  vt_reports+="IP: $ip\n$vt_result\n\n"
done

echo -e "\nVT Reports:\n$vt_reports"

#Step 4: Send summary prompt to Ollama (MCP ID 2)
summary=$(curl -s -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"mcp_id\": 2,
    \"type\": \"tool\",
    \"name\": \"prompt_ollama\",
    \"arguments\": {
      \"model\": \"mistral\",
      \"prompt\": \"Based on the following VirusTotal reports, summarize the most critical threat indicators and possible actions:\\n$vt_reports\"
    }
  }" | jq -r '.result')

echo -e "\nOllama Final Summary:\n$summary"
