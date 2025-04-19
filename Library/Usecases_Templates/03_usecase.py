#!/bin/bash

#Token
TOKEN="YOUR_TOKEN_HERE"

#Step 1: Parse CSV using MCP ID 6 (parse_file)
parsed_rows=$(curl -s -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 6,
    "type": "tool",
    "name": "parse_file",
    "arguments": {
      "file_type": "csv",
      "file_content": "id,text\\n1,Unauthorized access detected\\n2,Phishing attempt reported"
    }
  }' | jq -c '.')

echo -e "\nParsed CSV:\n$parsed_rows"

#Step 2: Extract text values for embedding
texts=$(echo "$parsed_rows" | jq -r '.[].text' | jq -Rs 'split("\n") | map(select(. != ""))')

echo -e "\nTexts to Embed:\n$texts"

#Step 3: Generate embeddings using Ollama MCP ID 2 (assumes model=bge)
embeddings=$(curl -s -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"mcp_id\": 2,
    \"type\": \"tool\",
    \"name\": \"prompt_ollama\",
    \"arguments\": {
      \"model\": \"bge-base-en-v1.5\",
      \"prompt\": \"$texts\"
    }
  }" | jq -c '.result')

echo -e "\nEmbeddings:\n$embeddings"

#Step 4: Store in ChromaDB (MCP ID 5)
store_result=$(curl -s -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"mcp_id\": 5,
    \"type\": \"tool\",
    \"name\": \"chromadb_store_and_query\",
    \"arguments\": {
      \"collection_name\": \"alerts_collection\",
      \"documents\": $texts,
      \"ids\": [\"alert1\", \"alert2\"],
      \"embeddings\": $embeddings
    }
  }" | jq -r '.result')

echo -e "\nChromaDB Store Result:\n$store_result"

#Step 5: Query ChromaDB using a user search term (MCP ID 5)
query_result=$(curl -s -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 5,
    "type": "tool",
    "name": "chromadb_store_and_query",
    "arguments": {
      "collection_name": "alerts_collection",
      "query_texts": ["unauthorized activity"]
    }
  }' | jq -c '.')

echo -e "\nChromaDB Search Result:\n$query_result"

#Step 6: Summarize top matches using Ollama (MCP ID 2)
summary=$(curl -s -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"mcp_id\": 2,
    \"type\": \"tool\",
    \"name\": \"prompt_ollama\",
    \"arguments\": {
      \"model\": \"mistral\",
      \"prompt\": \"Summarize the security alerts most similar to the search: unauthorized activity\\n$query_result\"
    }
  }" | jq -r '.result')

echo -e "\nFinal Summary:\n$summary"
