#!/bin/bash

#Token
TOKEN="YOUR_TOKEN_HERE"

#Step 1: Create MCP (ID = 5)
curl -X POST http://localhost:8000/create-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "chromadb-store-search",
    "description": "Store and search documents in ChromaDB, with optional precomputed embeddings.",
    "imports": ["import chromadb"],
    "globals": {
      "CHROMA_PERSIST_DIR": "chromadb"
    }
  }'

#Step 2: Create Tool (ID = 5)
curl -X POST http://localhost:8000/create-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "chromadb_store_and_query",
    "snippet": "    import chromadb\n    client = chromadb.Client(chromadb.config.Settings(\n        persist_directory=CHROMA_PERSIST_DIR\n    ))\n    collection = client.get_or_create_collection(name=collection_name)\n    if embeddings:\n        collection.add(documents=documents, ids=ids, embeddings=embeddings)\n        return \"Embeddings stored successfully.\"\n    if query_texts:\n        results = collection.query(query_texts=query_texts, n_results=3)\n        return str(results)\n    collection.add(documents=documents, ids=ids)\n    return \"Documents stored successfully.\"",
    "is_async": false,
    "params": {
      "collection_name": { "type": "str" },
      "documents": { "type": "list", "default": [] },
      "ids": { "type": "list", "default": [] },
      "query_texts": { "type": "list", "default": [] },
      "embeddings": { "type": "list", "default": [] }
    }
  }'

#Step 3: Link Tool ID 5 to MCP ID 5
curl -X POST http://localhost:8000/link-tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_id": 5, "mcp_id": 5}'

#Step 4: Install chromadb
curl -X POST http://localhost:8000/install-library \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "chromadb"}'

#Step 5: Run MCP
curl -X POST http://localhost:8000/run-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mcp_id": 5}'

#Step 6: Store with Embeddings
curl -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 5,
    "type": "tool",
    "name": "chromadb_store_and_query",
    "arguments": {
      "collection_name": "my_notes",
      "documents": ["the sun is hot"],
      "ids": ["doc1"],
      "embeddings": [[0.1, 0.05, 0.3, 0.44, 0.17, 0.02]]
    }
  }'

#Step 7: Query Documents
curl -X POST http://localhost:8000/infere-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_id": 5,
    "type": "tool",
    "name": "chromadb_store_and_query",
    "arguments": {
      "collection_name": "my_notes",
      "query_texts": ["hot weather"]
    }
  }'
