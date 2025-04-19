#!/bin/bash

#Token
TOKEN="YOUR_TOKEN_HERE"

#Step 1: Get Cybersecurity News from SerpAPI (MCP ID 1)
cyber_news=$(curl -s -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 1,
    "type": "tool",
    "name": "google_search",
    "arguments": {
      "query": "latest cybersecurity threats 2024",
      "max_results": 3
    }
  }' | jq -r '.result')

echo -e "\n🔍 News Results:\n$cyber_news"

#Step 2: Summarize News with Ollama (MCP ID 2)
ollama_summary=$(curl -s -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"mcp_id\": 2,
    \"type\": \"tool\",
    \"name\": \"prompt_ollama\",
    \"arguments\": {
      \"model\": \"mistral:12b\",
      \"prompt\": \"Summarize the following threat intelligence updates in a formal email report:\\n$cyber_news\"
    }
  }" | jq -r '.result')

echo -e "\nOllama Summary:\n$ollama_summary"

#Step 3: Format as Email Notification
echo -e "\nFinal Threat Report Email Draft:"
echo "--------------------------------------------------"
echo "Subject: [Threat Advisory] Summary of Latest Cybersecurity Incidents"
echo ""
echo "$ollama_summary"
echo ""
echo "Stay secure,"
echo "Cyber Intelligence Bot"
