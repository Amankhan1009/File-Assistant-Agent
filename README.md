# File Assistant Using LangGraph

A secure, persistent, tool-calling AI file assistant built with LangGraph, LangChain, Groq, and SQLite.

The File Assistant accepts natural-language requests through a command-line interface, reasons about filesystem operations, selects and executes registered tools, observes tool results, and continues the LangGraph agent loop until it can produce a final response.

All filesystem operations are restricted to a configured workspace directory.

## Features

- Natural-language file and directory management
- LangGraph-based agent and tool execution loop
- 13 registered filesystem tools
- Persistent conversation threads using SQLite checkpoints
- Multiple isolated conversation sessions using thread IDs
- Bounded model context while retaining complete persisted history
- Restricted workspace path resolution
- Path traversal and absolute path protection
- Safe file creation without overwriting existing paths
- UTF-8 file reading and writing
- File and directory search
- File metadata inspection
- File and directory move and rename operations
- ZIP archive creation and secure extraction
- Explicit safeguards for destructive filesystem operations
- Structured tool error responses
- Tool execution observability without logging file contents
- Application logging to console and file
- Safe CLI error boundaries
- Graph recursion-limit handling
- Persistent storage initialization and cleanup handling
- Automated pytest test suite

## Architecture

The application uses a LangGraph tool-calling agent loop:

```text
START
  |
  v
agent
  |
  v
route_after_agent
  |
  +----------------------+
  |                      |
  | tool calls           | no tool calls
  v                      v
tools                   END
  |
  v
agent
```

The `agent` node invokes the tool-bound language model.

If the model returns tool calls, LangGraph routes execution to the `tools` node. After tool execution, the resulting `ToolMessage` objects are added to graph state and execution returns to the agent.

The loop continues until the model produces a response without additional tool calls.

## Registered Tools

The File Assistant exposes 13 filesystem tools to the agent.

| Tool | Purpose |
| --- | --- |
| `list_directory` | List direct contents of a directory |
| `create_directory` | Create a new directory without overwriting existing paths |
| `delete_directory` | Delete an existing empty directory |
| `read_file` | Read a UTF-8 text file |
| `create_file` | Create a new UTF-8 text file without overwriting |
| `append_file` | Append UTF-8 text to an existing file |
| `search_files` | Recursively search for files by name |
| `search_text` | Recursively search inside UTF-8 text files |
| `get_file_metadata` | Retrieve safe file or directory metadata |
| `delete_file` | Delete an existing regular file |
| `move_path` | Move or rename a file or directory |
| `compress_paths` | Create ZIP archives from workspace paths |
| `extract_archive` | Securely extract ZIP archives |

## Security Model

Filesystem access is restricted to the configured workspace.

The path-resolution layer:

- Rejects absolute paths
- Canonically resolves requested paths
- Rejects paths that escape the workspace
- Prevents parent-directory traversal outside the workspace
- Prevents filesystem tools from accessing paths outside the configured boundary

Destructive operations follow additional restrictions.

The assistant:

- Deletes only explicitly authorized paths
- Does not recursively empty non-empty directories automatically
- Does not delete additional paths merely to make another operation succeed
- Protects the workspace root from deletion and movement
- Does not overwrite existing destination paths during creation, movement, compression, or extraction

ZIP extraction includes validation against:

- Path traversal entries
- Symbolic links
- Excessive archive entry counts
- Excessive extracted data size
- Existing destination contents

## Persistent Conversation Threads

LangGraph state is persisted using `SqliteSaver`.

The SQLite checkpoint database allows conversations to continue across separate CLI executions.

Start the default session:

```bash
python app.py
```

Start or resume a named session:

```bash
python app.py --thread project-alpha
```

Different thread IDs maintain isolated conversation histories.

For example:

```bash
python app.py --thread project-alpha
python app.py --thread project-beta
```

Each thread is stored independently in the SQLite checkpoint database.

## Context Management

Complete graph history is persisted in SQLite, while only a bounded number of recent conversation turns are sent to the language model.

This design:

- Preserves durable conversation state
- Prevents model context from growing indefinitely
- Keeps complete tool-call sequences inside retained turns
- Avoids modifying persisted message history during context selection

The current model context limit is 10 recent conversation turns.

## Observability and Logging

The application uses structured logging for important runtime events.

Logged events include:

- Application startup and shutdown
- Agent invocation start and completion
- Agent routing decisions
- Tool execution start and completion
- Tool name
- Tool success status
- Tool error type
- Tool execution duration
- Graph recursion-limit failures
- Unexpected graph execution failures
- Persistent storage initialization and cleanup failures

Tool arguments, file contents, and sensitive tool results are not written to application logs.

Runtime logs are written to:

```text
logs/file_assistant.log
```

The log file is ignored by Git.

## Project Structure

```text
File-Assistant/
├── app.py
├── core/
│   ├── config.py
│   ├── llm.py
│   ├── logging.py
│   ├── paths.py
│   └── prompts.py
├── database/
│   └── checkpointer.py
├── graph/
│   ├── builder.py
│   ├── nodes.py
│   ├── routing.py
│   ├── state.py
│   └── tool_observability.py
├── tools/
│   ├── archive_tools.py
│   ├── common.py
│   ├── delete_tools.py
│   ├── directory_tools.py
│   ├── metadata_tools.py
│   ├── move_tools.py
│   ├── read_tools.py
│   ├── registry.py
│   ├── schemas.py
│   ├── search_tools.py
│   └── write_tools.py
├── tests/
│   ├── test_app.py
│   ├── test_graph.py
│   ├── test_paths.py
│   └── test_tools.py
├── workspace/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.14 or a compatible Python version supported by the pinned dependencies
- Groq API key

The project uses:

- LangChain
- LangGraph
- LangGraph SQLite Checkpoint Saver
- LangChain Groq integration
- python-dotenv
- pydantic-settings
- pytest

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd File-Assistant
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate the virtual environment.

On macOS or Linux:

```bash
source venv/bin/activate
```

On Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Configure the environment variables:

```text
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
WORKSPACE_ROOT=workspace
```

`GROQ_API_KEY` is required.

`GROQ_MODEL` is optional and defaults to `openai/gpt-oss-120b`.

`WORKSPACE_ROOT` is optional and defaults to `workspace`.

The workspace path must be relative and must resolve inside the project directory.

## Usage

Start the assistant:

```bash
python app.py
```

Use a named persistent conversation:

```bash
python app.py --thread project-alpha
```

Restart the same thread later to continue its persisted conversation history:

```bash
python app.py --thread project-alpha
```

Different thread IDs maintain isolated persistent conversation histories.

Example interaction:

```text
File Assistant started.
Session: file-assistant-cli
Type 'exit' or 'quit' to stop.

You: Create a file called notes.txt containing my project notes.

Assistant: The file notes.txt was created successfully.

You: Read notes.txt.

Assistant: The file contains: my project notes.

You: exit

File Assistant stopped.
```

## Running Tests

Run the complete test suite:

```bash
python -m pytest -q
```

Current verified result:

```text
124 passed
```

The automated tests cover:

- Workspace path security
- Path traversal rejection
- Read-only filesystem tools
- File and directory creation
- File appending
- Search tools
- Delete operations
- Move and rename operations
- ZIP compression and extraction
- Archive security boundaries
- Tool registry behavior
- LangGraph routing
- Agent context management
- Tool execution observability
- SQLite checkpoint persistence
- Persistent thread isolation
- Application CLI behavior
- Runtime error boundaries
- Graph recursion-limit handling
- Persistent storage initialization and cleanup failures

## Repository Hygiene

The repository excludes runtime and sensitive files including:

- `.env`
- Python virtual environments
- Python bytecode and cache directories
- pytest caches and coverage artifacts
- macOS `.DS_Store` files
- IDE configuration
- Runtime log files
- SQLite checkpoint databases
- Runtime workspace contents
- Build and packaging artifacts

`.env.example`, `logs/.gitkeep`, and `workspace/.gitkeep` remain trackable.

## Technology Stack

- Python
- LangGraph
- LangChain
- Groq
- SQLite
- pytest

## License

No license has been added yet.
