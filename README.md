# 📁 File Assistant Using LangGraph

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20AI-purple)](https://www.langchain.com/langgraph)
[![LangChain](https://img.shields.io/badge/LangChain-Framework-green)](https://www.langchain.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?logo=streamlit)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Persistence-003B57?logo=sqlite)](https://sqlite.org/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7)](https://render.com/)

</div>

---

## 🚀 Overview

**File Assistant** is a production-ready **Agentic AI File Management System** built with **LangGraph**, **LangChain**, **FastAPI**, **Streamlit**, **Groq LLM**, and **SQLite**.

Instead of mapping user requests to predefined functions, the assistant reasons about natural-language instructions, selects the appropriate filesystem tool, executes it, observes the results, and continues the reasoning loop until it can provide a final response.

The application follows a modern client-server architecture:

- **Streamlit** provides the interactive chat interface.
- **FastAPI** exposes REST APIs.
- **LangGraph** orchestrates the AI agent.
- **SQLite** persists conversations.
- **Thread-isolated workspaces** securely separate user files.
- **Docker** enables consistent deployment.
- **Render** hosts the production application.

---

# ✨ Features

## 🤖 AI Agent

- LangGraph Tool-Calling Agent
- Multi-step reasoning
- Automatic tool selection
- Agent loop with observation
- Persistent conversation memory
- Context window optimization
- Structured tool responses
- Graceful error recovery

---

## 📁 File Management

Supports **13 filesystem tools** including:

- Create files
- Read files
- Append to files
- Delete files
- Create directories
- Delete directories
- Move & rename
- Search files
- Search text
- Retrieve metadata
- ZIP compression
- ZIP extraction
- Directory listing

---

## 💬 Conversations

- Persistent chat history
- SQLite checkpoints
- Multiple conversations
- Thread isolation
- Resume previous sessions
- Conversation switching
- Recent context optimization

---

## 🌐 Web Application

Interactive Streamlit frontend with:

- Chat interface
- Sidebar conversations
- Workspace explorer
- File preview
- Multiple conversation support
- Real-time responses

---

## 🔒 Security

The assistant never accesses arbitrary filesystem locations.

Security protections include:

- Absolute path rejection
- Path traversal prevention
- Workspace sandboxing
- Thread-isolated workspaces
- Secure ZIP extraction
- Safe overwrite protection
- UTF-8 validation
- Structured error handling

---

# 🏗️ System Architecture

```text
                    ┌────────────────────────────┐
                    │      Streamlit Frontend    │
                    │   Chat UI + Workspace UI   │
                    └─────────────┬──────────────┘
                                  │
                           HTTP REST API
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │       FastAPI Backend      │
                    │     Conversation APIs      │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │     LangGraph Agent        │
                    │  Tool Calling + Routing    │
                    └─────────────┬──────────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             ▼                    ▼                    ▼
      SQLite Checkpoints     File Tools         Workspace Isolation
             │                    │                    │
             └────────────────────┴────────────────────┘
                                  │
                                  ▼
                           Workspace Files
```

---

# 🤖 LangGraph Workflow

The application follows a classic LangGraph agent loop.

```text
                START
                  │
                  ▼
             Agent Node
                  │
                  ▼
          Route After Agent
          ┌────────┴────────┐
          │                 │
    Tool Calls          No Tool Calls
          │                 │
          ▼                 ▼
      Tool Node            END
          │
          ▼
      Agent Node
```

### Workflow

1. User sends a request.
2. The LLM reasons about the task.
3. LangGraph determines whether tools are required.
4. Required filesystem tools execute.
5. Tool outputs are returned to the LLM.
6. The LLM continues reasoning.
7. The loop ends when a final response is generated.

---

# 📦 Tech Stack

| Category | Technologies |
|-----------|--------------|
| Language | Python 3.14 |
| Agent Framework | LangGraph |
| LLM Framework | LangChain |
| LLM | Groq (OpenAI GPT-OSS-120B) |
| Backend | FastAPI |
| Frontend | Streamlit |
| Persistence | SQLite |
| API Validation | Pydantic |
| Testing | Pytest |
| Deployment | Docker, Render |
| Version Control | Git & GitHub |

---

# 📚 Table of Contents

- Overview
- Features
- Architecture
- Tool Registry
- Security Model
- Project Structure
- Installation
- Environment Variables
- Running the Application
- REST API
- Docker
- Deployment
- Testing
- Logging
- Roadmap
- License

# 🛠️ Registered File System Tools

The AI agent has access to **13 secure filesystem tools**.

Rather than calling tools directly, the LangGraph agent reasons about the user's request, selects the appropriate tool(s), executes them, observes the results, and continues the reasoning loop until it can generate a final response.

| Tool | Description |
|------|-------------|
| `list_directory` | List the contents of a directory |
| `create_directory` | Create a new directory |
| `delete_directory` | Delete an empty directory |
| `read_file` | Read UTF-8 text files |
| `create_file` | Create new text files safely |
| `append_file` | Append text to existing files |
| `delete_file` | Delete files |
| `move_path` | Move or rename files/directories |
| `search_files` | Search files by filename |
| `search_text` | Search inside UTF-8 text files |
| `get_file_metadata` | Retrieve file metadata |
| `compress_paths` | Create ZIP archives |
| `extract_archive` | Securely extract ZIP archives |

---

# 🔒 Security Model

The File Assistant was designed with security as a first-class concern.

Every filesystem operation is executed inside a restricted workspace boundary.

## Path Protection

The application automatically rejects:

- Absolute paths
- Path traversal (`../`)
- Escaping the workspace
- Invalid workspace roots

Only files located inside the current workspace can be accessed.

---

## Thread-Isolated Workspaces

Each conversation has its own isolated workspace.

Instead of writing files into a shared directory, every conversation receives its own dedicated workspace.

```text
workspace/
└── threads/
    ├── e8d83...
    │   ├── notes.txt
    │   └── reports/
    ├── 6bc91...
    │   ├── todo.txt
    │   └── demo.txt
    └── ...
```

Each workspace is identified using a deterministic SHA-256 hash derived from the conversation thread ID.

This guarantees:

- Conversation isolation
- File isolation
- Secure concurrent usage
- Predictable workspace mapping

---

## Secure Tool Execution

Before every filesystem tool executes:

1. The LangGraph thread ID is extracted.
2. The corresponding workspace is resolved.
3. The workspace is bound using `ContextVar`.
4. All filesystem paths are resolved inside that workspace.
5. The previous workspace is restored automatically.

This allows multiple conversations to execute safely without interfering with one another.

---

## ZIP Archive Protection

ZIP extraction includes several security checks.

Protected against:

- Path traversal entries
- Symbolic links
- Oversized archives
- Excessive extraction size
- Existing destination overwrite

---

# 💬 Persistent Conversations

Conversation history is persisted using **LangGraph SQLite Checkpointers**.

Unlike stateless chat applications, conversations continue even after restarting the application.

Each conversation maintains:

- User messages
- Assistant responses
- Tool calls
- Tool observations
- LangGraph execution state

---

## Multiple Conversations

The application supports multiple independent conversations.

```text
Conversation A
├── Chat History
├── Workspace
└── Files

Conversation B
├── Chat History
├── Workspace
└── Files
```

Each conversation has:

- Independent memory
- Independent workspace
- Independent files
- Independent LangGraph checkpoints

---

# 🧠 Context Management

Although the complete conversation history is stored inside SQLite, only the most recent conversation turns are sent to the LLM.

Benefits:

- Lower token usage
- Faster responses
- Reduced costs
- Stable context length

Current configuration:

```
10 recent conversation turns
```

Meanwhile, the complete conversation history remains available inside SQLite.

---

# 🌐 Frontend

The project includes a modern **Streamlit** frontend.

Features include:

- AI chat interface
- Conversation sidebar
- Workspace explorer
- File preview
- Multiple conversation support
- Responsive layout

Unlike the CLI version, the frontend communicates with the backend exclusively through REST APIs.

---

# ⚡ Backend

The FastAPI backend exposes REST APIs used by the frontend.

Responsibilities include:

- LangGraph execution
- Conversation persistence
- Workspace management
- File preview
- Conversation retrieval
- Security enforcement

---

# 📡 REST API

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/chat` | Execute one AI interaction |
| GET | `/conversations` | Retrieve conversations |
| GET | `/threads/{thread_id}/messages` | Conversation history |
| GET | `/workspace` | Retrieve workspace tree |
| GET | `/preview` | Preview file contents |

---

# 🔄 Frontend–Backend Communication

The frontend never accesses the filesystem directly.

Instead, it communicates with the backend through HTTP APIs.

```text
           Streamlit Frontend
                  │
        ┌─────────┴──────────┐
        │                    │
        ▼                    ▼
 GET /workspace        GET /preview
        │                    │
        └─────────┬──────────┘
                  ▼
            FastAPI Backend
                  │
                  ▼
         Thread Workspace
                  │
                  ▼
               File System
```

This architecture allows the frontend and backend to run as completely independent services.

---

# 📂 Project Structure

```text
File-Assistant/
│
├── api/
│   ├── main.py
│   ├── schemas.py
│   └── __init__.py
│
├── frontend/
│   ├── app.py
│   ├── api_client.py
│   ├── conversation.py
│   ├── preview.py
│   ├── workspace.py
│   ├── workspace_ui.py
│   └── ...
│
├── core/
│   ├── config.py
│   ├── llm.py
│   ├── logging.py
│   ├── paths.py
│   ├── prompts.py
│   └── workspace_context.py
│
├── graph/
│   ├── builder.py
│   ├── nodes.py
│   ├── routing.py
│   ├── state.py
│   └── tool_observability.py
│
├── tools/
│   ├── directory_tools.py
│   ├── write_tools.py
│   ├── read_tools.py
│   ├── delete_tools.py
│   ├── metadata_tools.py
│   ├── move_tools.py
│   ├── search_tools.py
│   ├── archive_tools.py
│   └── registry.py
│
├── database/
│   └── checkpointer.py
│
├── workspace/
│
├── logs/
│
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── requirements.txt
└── README.md
```

# ⚙️ Prerequisites

Before running the project, ensure you have the following installed:

- Python **3.14+**
- Git
- Docker Desktop *(optional but recommended)*
- Groq API Key

---

# 📥 Installation

## Clone the Repository

```bash
https://github.com/Amankhan1009/File-Assistant-Agent.git
cd File-Assistant-Agent
```

---

## Create a Virtual Environment

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows (PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.env` file in the project root.

```env
GROQ_API_KEY=your_groq_api_key

GROQ_MODEL=openai/gpt-oss-120b

WORKSPACE_ROOT=workspace

DATABASE_PATH=database/checkpoints.sqlite
```

---

## Environment Variable Reference

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Your Groq API key |
| `GROQ_MODEL` | LLM used by the assistant |
| `WORKSPACE_ROOT` | Root directory for thread workspaces |
| `DATABASE_PATH` | SQLite checkpoint database |

---

# 🚀 Running the Project

The project consists of two independent services.

- FastAPI Backend
- Streamlit Frontend

---

## 1️⃣ Start the Backend

```bash
uvicorn api.main:app --reload
```

Backend:

```
http://127.0.0.1:8000
```

Swagger UI:

```
http://127.0.0.1:8000/docs
```

ReDoc:

```
http://127.0.0.1:8000/redoc
```

---

## 2️⃣ Start the Frontend

Open another terminal.

```bash
streamlit run frontend/app.py
```

Frontend:

```
http://localhost:8501
```

---

# 🐳 Docker Support

The application includes separate Docker images for:

- Backend
- Frontend

This mirrors the production deployment architecture.

---

## Build Backend

```bash
docker build \
-f Dockerfile.backend \
-t file-assistant-backend .
```

---

## Run Backend

```bash
docker run -p 8000:8000 \
file-assistant-backend
```

---

## Build Frontend

```bash
docker build \
-f Dockerfile.frontend \
-t file-assistant-frontend .
```

---

## Run Frontend

```bash
docker run -p 8501:8501 \
file-assistant-frontend
```

---

# 🐳 Docker Compose

The repository includes a Docker Compose configuration that starts both services together.

Start both containers:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up -d
```

Stop:

```bash
docker compose down
```

---

# 🌍 Production Deployment

The application is designed to be deployed as two independent services.

```text
                 Internet
                     │
         ┌───────────┴────────────┐
         │                        │
         ▼                        ▼
 Streamlit Frontend        FastAPI Backend
         │                        │
         └──────────┬─────────────┘
                    ▼
             LangGraph Agent
                    │
                    ▼
        Thread-Isolated Workspaces
```

This architecture provides:

- Independent scaling
- Separation of concerns
- Secure filesystem ownership
- Clean API boundaries

---

# ☁️ Render Deployment

The project is deployed using **two Render services**.

## Backend

Responsibilities:

- LangGraph execution
- Tool execution
- SQLite persistence
- Workspace management
- REST APIs

---

## Frontend

Responsibilities:

- Chat interface
- Conversation history
- Workspace explorer
- File preview
- API communication

---

# 🧩 Multi-Architecture Docker Images

Docker images are published for:

- linux/amd64
- linux/arm64

This allows the application to run on:

- Apple Silicon Macs
- Intel Macs
- Linux servers
- Cloud platforms

Verify image architectures:

```bash
docker buildx imagetools inspect <image-name>
```

---

# 💾 Persistent Storage

Conversation history is persisted using SQLite.

```
SQLite
      │
      ▼
LangGraph Checkpointer
      │
      ▼
Conversation Memory
```

Each conversation stores:

- User messages
- AI responses
- Tool calls
- Tool observations
- Graph state

---

# 📁 Workspace Storage

Each conversation receives its own isolated workspace.

Example:

```text
workspace/
└── threads/
    ├── a4d78d...
    │   ├── notes.txt
    │   └── report.pdf
    │
    ├── 81fb6a...
    │   ├── todo.txt
    │   └── images/
    │
    └── ...
```

The frontend never accesses these files directly.

Instead, it communicates with the backend using:

- `/workspace`
- `/preview`

ensuring that all filesystem operations remain securely isolated within the backend.

---

# 📊 Logging

Application logs include:

- Agent execution
- Tool execution
- Routing decisions
- Errors
- Runtime events
- API activity

Sensitive information is never written to logs.

Log location:

```text
logs/file_assistant.log
```

# 📡 REST API Reference

The frontend communicates with the backend exclusively through REST APIs.

| Method | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Check backend health |
| `POST` | `/chat` | Execute one File Assistant interaction |
| `GET` | `/conversations` | Retrieve all conversations |
| `GET` | `/threads/{thread_id}/messages` | Retrieve conversation history |
| `GET` | `/workspace` | Retrieve the workspace tree for a conversation |
| `GET` | `/preview` | Retrieve a UTF-8 preview of a file |

---

# 🧪 Running Tests

Run the complete test suite:

```bash
pytest
```

or

```bash
python -m pytest
```

**Current test status:**

```text
231 passed
```

The automated test suite covers:

- Workspace security
- Thread workspace isolation
- Path traversal prevention
- File creation
- File reading
- File appending
- Directory operations
- Search tools
- Metadata retrieval
- Delete operations
- Move & rename
- ZIP compression
- ZIP extraction
- Tool registry
- LangGraph routing
- Context management
- SQLite persistence
- REST API endpoints
- Frontend–Backend integration
- Workspace APIs
- File preview APIs
---

# 📈 Performance Considerations

The application is designed for long-running conversations.

Key optimizations include:

- Persistent LangGraph checkpoints
- Bounded LLM context
- Workspace isolation
- Stateless REST APIs
- Efficient filesystem resolution
- Secure path validation
- Lightweight Streamlit frontend

---

# 📦 Repository Hygiene

The repository excludes runtime and generated files including:

- `.env`
- `venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.coverage`
- `.DS_Store`
- SQLite databases
- Runtime logs
- Workspace files
- Build artifacts
- IDE configuration

Only source code and required project assets are tracked.

---

# 🛣️ Future Improvements

Planned enhancements include:

- File upload support
- File download support
- Drag-and-drop uploads
- Syntax highlighting
- Markdown preview
- Image preview
- Authentication
- User accounts
- Cloud object storage
- Vector memory for long-term context
- Streaming LLM responses
- WebSocket support
- Role-based permissions
- File version history
- Multi-user collaboration
- Kubernetes deployment
- CI/CD pipeline
- Observability dashboards

---

# 🤝 Contributing

Contributions are welcome!

If you'd like to contribute:

1. Fork the repository
2. Create a feature branch

```bash
git checkout -b feature/my-feature
```

3. Commit your changes

```bash
git commit -m "Add my feature"
```

4. Push your branch

```bash
git push origin feature/my-feature
```

5. Open a Pull Request

---

# 👨‍💻 Author

**Md Aman Alam**

AI Engineer | Machine Learning | Agentic AI | Generative AI

- GitHub: https://github.com/Amankhan1009
- LinkedIn: *[linkedin](https://www.linkedin.com/in/md-aman-alam-a04552289/?skipRedirect=true)*

---

# 🙏 Acknowledgements

This project was built using:

- LangGraph
- LangChain
- FastAPI
- Streamlit
- Groq
- SQLite
- Docker
- Render

Special thanks to the open-source community for building the tools that made this project possible.

---

# 📄 License

This project is licensed under the **No license has been added yet.**.

You are free to:

- Use
- Modify
- Distribute
- Contribute

under the terms of the MIT License.

---

# ⭐ Support

If you found this project useful:

⭐ Star the repository

🍴 Fork the project

🛠️ Build something amazing with it

---

<div align="center">

## Thank you for visiting this project!

If you enjoyed exploring **File Assistant Using LangGraph**, consider giving the repository a ⭐ on GitHub.

**Happy Coding! 🚀**

</div>