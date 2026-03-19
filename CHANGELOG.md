# Changelog

## [2026-03-18] - Agent Mode: Workspace & File System Rework

### Added
- **Workspace Selection**: Full folder browser modal with drive listing (Windows drives auto-detected), path navigation, and workspace picker
- **File Explorer Panel**: Sidebar "Files" tab with tree-style file browser for the active workspace, showing file sizes, icons by type, and support for navigating directories
- **Context Management**: Sidebar "Context" tab showing files loaded into conversation context; right-click any file in the Files tab to add it; remove from Context tab
- **Agent System Prompt**: AI now receives the full workspace file tree (3 levels deep) and all context files, enabling it to reason about the entire project structure
- **Apply Code to Files**: When the AI generates code blocks with file paths (```lang:path/to/file```), an "Apply" button appears to write the code directly to disk
- **Image Support**: Images in the workspace are detected and rendered — click to view in a lightbox overlay; image files in the file tree open in the lightbox
- **Qwen3 Thinking Token Stripping**: `<think>...</think>` blocks from Qwen3 model output are automatically stripped before display
- **Markdown Rendering**: Assistant messages now render full Markdown (headings, lists, bold, code blocks, blockquotes) via `marked.js`
- **Toast Notifications**: Non-intrusive toast messages for success/error/info feedback throughout the app
- **File Viewer Modal**: Click any text file in the file tree to view its syntax-highlighted content in a modal, with copy and add-to-context buttons
- **File Write Endpoint**: `POST /write-file` endpoint for the agent to write code changes to disk
- **File Read Endpoint**: `GET /read-file` endpoint for reading workspace files
- **Browse Endpoint**: `GET /browse` endpoint for directory listing
- **Drives Endpoint**: `GET /drives` endpoint for listing available drives
- **Image Serving**: `GET /workspace-image` endpoint for serving workspace images to the browser
- **Add/Remove Context Endpoints**: `POST /add-file-context` and `POST /remove-file-context` for managing conversation context files from the workspace

### Changed
- **database.py**: Added `workspace_path` column to conversations table with migration support, plus `set_workspace()` and `get_workspace()` methods
- **app.py**: Reworked into a full agent backend — new file system endpoints, workspace-aware conversation context, agent-optimized system prompt, thinking token stripping
- **Default Model**: Kept default as `qwen3.5:9b` (configurable via `OLLAMA_MODEL` env var)
- **UI Layout**: Sidebar now has three tabs (Chats, Files, Context) plus workspace selector; messages show user/assistant avatars; dark theme is now the default
- **Message Format**: Messages now render as Markdown with inline code blocks that have language labels, copy buttons, and "Apply" buttons for file-targeted code
- **Conversation Items**: Now show the associated workspace folder name

### Removed
- **Context Window Button**: Removed the standalone "Create Context Window" header button (replaced by the Context tab workflow)

## [2026-03-18] - Model Warmup on Startup

### Added
- **app.py**: Added `warmup_model()` function that sends a minimal request to Ollama at launch, preloading the model into memory/VRAM so the first real user message responds quickly
- **app.py**: Warmup runs in a background thread so the Flask server starts accepting connections immediately
- **app.py**: Warmup is gated on `WERKZEUG_RUN_MAIN` to avoid running twice under the debug reloader

## [2026-03-18] - Switch to Local Ollama LLM

### Changed
- **LLM Backend**: Replaced Anthropic Claude API with local Ollama instance using `qwen3.5:9b` model
- **app.py**: Swapped `anthropic` SDK for `openai` SDK targeting Ollama's OpenAI-compatible endpoint (`http://localhost:11434/v1`)
- **app.py**: Removed Anthropic API key requirement; Ollama runs locally with no key needed
- **app.py**: Updated API call from `client.messages.create()` (Anthropic) to `client.chat.completions.create()` (OpenAI-compatible)
- **app.py**: Updated response parsing to use OpenAI response format (`choices[0].message.content`, `usage.prompt_tokens`, `usage.completion_tokens`)
- **app.py**: Updated error handling from `anthropic.APIError` to `ConnectionError` with Ollama-specific messaging
- **app.py**: Added `OLLAMA_BASE_URL` and `OLLAMA_MODEL` env var support for easy configuration
- **requirements.txt**: Replaced `anthropic` dependency with `openai`
- **README.md**: Updated prerequisites, dependencies, and acknowledgments to reflect Ollama/qwen usage

### Configuration
- `OLLAMA_BASE_URL` defaults to `http://localhost:11434/v1`
- `OLLAMA_MODEL` defaults to `qwen3.5:9b`
- Both can be overridden via `.env` file
