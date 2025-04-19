# CraftMCP
![image](https://github.com/user-attachments/assets/a67a2bc1-9e33-4fb1-a519-21821c11ccfd)


**CraftMCP** is a modern development suite and orchestration framework for building, managing, and running **Model Context Protocol (MCP)** servers in Python — entirely via REST APIs.

It empowers developers to compose and publish modular AI pipelines without manually editing files, writing boilerplate code, or juggling command-line interfaces. With just a few authenticated API calls, you can:

- Create and structure MCP tools, prompts, resources, and full servers  
- Run any MCP instance dynamically using `uv` and `stdio` transport  
- Execute tools/prompts in real-time through `/infere-mcp` with dynamic I/O  
- Chain MCPs together as end-to-end workflows using simple bash scripts or any REST friendly software.

---

## 🧱 Is It a Framework or a Suite?

**CraftMCP is both:**

- A lightweight **framework** for defining and running structured MCP logic using Python decorators and stdio transport  
- A full **development suite** with built-in REST API, workspace management, authentication, and test case orchestration

It’s designed to be extensible, secure, and cloud/container-friendly — making it ideal for internal teams, AI ops platforms, or power users managing complex prompt + tool chains.

---

## ⚙️ Setup

You can run CraftMCP in two ways:

### 1. Docker (Recommended)

#### On Linux or Windows WSL

```bash
docker pull hshehata/craftmcp:latest
docker run -d -p 8000:8000 -v craftmcp_data:/app hshehata/craftmcp
docker logs $(docker ps -lq) 2>&1 | grep "Admin token"
docker stop $(docker ps -lq) && docker rm -f $(docker ps -lq)
```

- Re-run:

```bash
docker run -d -p 8000:8000 -v craftmcp_data:/app craftmcp
```

---

### 2. Local Python App

```bash
git clone https://github.com/your-org/craftmcp
cd craftmcp
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py
```

---

## 📚 Comes with Sample Use Cases

CraftMCP ships with ready-to-test **MCP examples** and **chained workflows** located in:

- `Library/MCPs/` – atomic use case scripts (`*.sh`)
- `Library/Usecases_Templates/` – multi-step use cases chaining MCPs

### Predefined MCPs:

- **Ollama Prompting** — LLMs like OpenAI, local models, supports summarization and embedding use cases  
- **Internet Search** — via SerpAPI for retrieving threat news or context  
- **CSV/JSON Parsing** — parse structured content passed as string, supports flattening nested JSON  
- **ChromaDB Integration** — store and search vector embeddings using document IDs  
- **Splunk SPL Search** — blocking SPL queries using bearer tokens  
- **VirusTotal IP/Hash Reputation** — enrich file hashes or IPs with detection scores and verdicts

---

### Example Use Case Chains:

- 🛡️ Retrieve breaking cybersecurity news or threat campaign updates from the web  
  → Summarize via a local Ollama LLM  
  → Format threat report as an email-ready message

- 🔎 Enrich IOCs from Splunk logs (SPL query for top IPs)  
  → Query VirusTotal for each IP  
  → Summarize reputation results with Ollama into an advisory

- 📊 Parse a CSV/JSON string  
  → Generate BGE embeddings using Ollama  
  → Store them in ChromaDB  
  → Search similar entries based on a query  
  → Summarize top hits with Ollama

---

Each MCP and use case is testable using simple bash scripts with `curl`, and extendable via your own prompts, tools, and logic.

---

## 📡 API Overview

All endpoints are authenticated via token. Admin token is generated on first run.

---

## API Endpoint Reference and Usage Guide

| Endpoint                    | Method | Description and Usage Example |
|-----------------------------|--------|-------------------------------|
| `/create-user`             | POST   | Create a user. Body: `{"username": "alice", "is_admin": true}` |
| `/list-users`              | GET    | List users (admin only). Auth required. |
| `/refresh-user-token`      | POST   | Refresh a user token. Body: `{"user_id": 1}` |
| `/delete-user`             | POST   | Delete a user. Body: `{"user_id": 1}` |
| `/create-mcp`              | POST   | Create an MCP. Body: `{"name": "demo", "imports": ["..."], "globals": {"KEY": "val"}}` |
| `/list-mcps`               | GET    | List MCPs owned by the user. |
| `/modify-mcp`              | POST   | Modify MCP metadata. Body: `{"mcp_id": 1, "globals": {...}}` |
| `/delete-mcp`              | POST   | Delete MCP. Body: `{"mcp_id": 1}` |
| `/export-mcp`              | GET    | Export MCP structure (excluding code). Query: `?mcp_id=1` |
| `/create-tool`             | POST   | Add a tool. Body: `{"tool_name": "name", "snippet": "...", "params": {...}, "is_async": false}` |
| `/link-tool`               | POST   | Link tool to MCP. Body: `{"tool_id": 1, "mcp_id": 1}` |
| `/unlink-tool`             | POST   | Unlink tool. Body: `{"tool_id": 1, "mcp_id": 1}` |
| `/list-tools`              | GET    | List tools for user. Auth required. |
| `/modify-tool`             | POST   | Update tool snippet/params. Body: `{"tool_id": 1, "snippet": "..."}` |
| `/export-tool`             | GET    | Export tool metadata. Query: `?tool_id=1` |
| `/delete-tool`             | POST   | Delete a tool. Body: `{"tool_id": 1}` |
| `/create-resource`         | POST   | Add a resource. Body: `{"name": "R", "value": "text", "mcp_id": 1}` |
| `/link-resource`           | POST   | Link resource. Body: `{"resource_id": 1, "mcp_id": 1}` |
| `/unlink-resource`         | POST   | Unlink resource. Body: `{"resource_id": 1, "mcp_id": 1}` |
| `/list-resources`          | GET    | List user resources. |
| `/modify-resource`         | POST   | Modify resource. Body: `{"resource_id": 1, "value": "new"}` |
| `/export-resource`         | GET    | Export resource metadata. Query: `?resource_id=1` |
| `/delete-resource`         | POST   | Delete a resource. Body: `{"resource_id": 1}` |
| `/create-prompt`           | POST   | Add a prompt. Body: `{"name": "prompt", "template": "Hi {{name}}", "params": {"name": "str"}}` |
| `/link-prompt`             | POST   | Link prompt. Body: `{"prompt_id": 1, "mcp_id": 1}` |
| `/unlink-prompt`           | POST   | Unlink prompt. Body: `{"prompt_id": 1, "mcp_id": 1}` |
| `/list-prompts`            | GET    | List all user prompts. |
| `/modify-prompt`           | POST   | Modify prompt text or params. Body: `{"prompt_id": 1, "template": "...", "params": {...}}` |
| `/export-prompt`           | GET    | Export prompt details. Query: `?prompt_id=1` |
| `/delete-prompt`           | POST   | Delete prompt. Body: `{"prompt_id": 1}` |
| `/install-library`         | POST   | Install a pip library. Body: `{"name": "requests"}` |
| `/list-libraries`          | POST   | View installed libs. Body: `{}` |
| `/delete-library`          | POST   | Uninstall a lib. Body: `{"name": "chromadb"}` |
| `/export-full-mcp`         | GET    | Download final MCP Python code. Query: `?mcp_id=1` |
| `/run-mcp`                 | POST   | Start MCP server runtime. Body: `{"mcp_id": 1}` |
| `/mcps-status`             | POST   | Show status of all user MCPs. |
| `/stop-mcp`                | POST   | Stop MCP runtime. Body: `{"mcp_id": 1}` |
| `/infere-mcp`              | POST   | Invoke tools, prompts, or resources. Body: `{"mcp_id": 1, "type": "tool", "name": "tool_name", "arguments": {...}}` |

---

For more details on all available API endpoints and interactive testing, visit the Swagger docs at:

**http://localhost:8000/docs** (after starting the Docker container)


---

## 🧪 WIP Endpoints (Coming Soon)

| Endpoint                | Method | Description                                  |
|-------------------------|--------|----------------------------------------------|
| `/create-helper`       | POST   | Create a helper function (WIP)               |
| `/link-helper`         | POST   | Link a helper to an MCP (WIP)                |
| `/unlink-helper`       | POST   | Unlink a helper from an MCP (WIP)            |
| `/list-helpers`        | GET    | List helper functions (WIP)                  |
| `/modify-helper`       | POST   | Modify a helper function (WIP)               |
| `/export-helper`       | GET    | Export a helper function (WIP)               |
| `/delete-helper`       | POST   | Delete a helper function (WIP)               |
| `/byo-mcp-upload`      | POST   | Bring your own MCP Python file (WIP)         |
| `/byo-mcp-describe`    | POST   | Extract tools/prompts/resources from file    |

---

## Next Steps

- Finalize helper and BYOMCP integration
- Add role-based access control, cert-based auth, parameter encryption
- Publish `Usecases_Templates` as Postman collections and bash workflows
- Encourage open MCP submissions and integrations

---

## 🤝 Contributing

Feel free to fork, contribute, or open an issue. Let's keep it simple — and powerful.

---

📎 Reference: https://modelcontextprotocol.io
---

## Using the MCP Library and Usecases

CraftMCP ships with ready-to-run shell scripts for each individual MCP and full chained use cases under:

- `Library/MCPs/` → one script per MCP (e.g., `02_prompt_ollama.sh`)
- `Library/Usecases_Templates/` → chained use cases combining multiple MCPs (e.g., `usecase_01_threat_advisory.sh`)

Each use case is executed using only `/infere-mcp` calls and references previously created MCPs. You are expected to:

- Provide your token
- Modify the scripts to match your data or endpoint setup
- Ensure MCPs and Tools are created before running chained use cases
- Optionally, adjust models, summaries, or chaining logic for your needs

This setup ensures high modularity and separation between MCP definition and use-case execution.

> These examples are written in Bash for simplicity, but the approach is not limited to Bash. You can execute the same REST calls from Python, Postman, JS, or any tool that supports HTTP requests.

Feel free to contribute more MCPs or use cases. Tweak and test freely — it’s designed for that.

---
