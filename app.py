from flask import Flask, request, render_template, jsonify, session, flash, send_file, abort
import os
import re
import threading
import string
import mimetypes
from pathlib import Path
from openai import OpenAI
import json
from dotenv import load_dotenv
from database import ConversationDatabase
from typing import List, Dict, Any, Optional
from datetime import datetime
import pytz
from flask_assets import Environment, Bundle
from colorama import init, Fore, Style

init()
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

assets = Environment(app)
assets.url = app.static_url_path
scss = Bundle('scss/main.scss', filters='pyscss', output='css/main.css')
assets.register('scss_all', scss)

COLORS = {
    'primary': '#1E88E5',
    'secondary': '#424242',
    'accent': '#00C853',
    'error': '#D32F2F',
    'background': '#FAFAFA',
    'text': '#212121',
    'code_bg': '#263238'
}

conversation_db = ConversationDatabase()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico'}
BINARY_EXTENSIONS = {'.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.zip', '.tar',
                     '.gz', '.7z', '.rar', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
                     '.ppt', '.pptx', '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
                     '.woff', '.woff2', '.ttf', '.otf', '.eot', '.pyc', '.pyo', '.class'}
IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.env',
               'env', '.idea', '.vscode', '.cursor', 'dist', 'build', '.next',
               '.nuxt', 'target', 'bin', 'obj', '.tox', '.mypy_cache', '.pytest_cache',
               'coverage', '.nyc_output', '.sass-cache'}


def warmup_model():
    try:
        print(f"{Fore.YELLOW}Warming up model '{OLLAMA_MODEL}'...{Style.RESET_ALL}")
        import time
        start = time.time()
        client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
            temperature=0,
        )
        elapsed = round(time.time() - start, 1)
        print(f"{Fore.GREEN}Model '{OLLAMA_MODEL}' warmed up in {elapsed}s — ready for fast responses{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Model warmup failed: {e}{Style.RESET_ALL}")


def strip_thinking_tokens(text: str) -> str:
    """Strip <think>...</think> blocks from Qwen3 model output."""
    return re.sub(r'<think>[\s\S]*?</think>', '', text).strip()


def format_timestamp(timestamp: str) -> str:
    try:
        try:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        local_tz = pytz.timezone('UTC')
        local_dt = local_tz.localize(dt)
        return local_dt.strftime('%B %d, %Y %I:%M %p')
    except ValueError as e:
        print(f"Error parsing timestamp {timestamp}: {e}")
        return timestamp


def is_safe_path(path: str, workspace: str = None) -> bool:
    """Validate that a path is safe to access."""
    try:
        resolved = Path(path).resolve()
        if workspace:
            ws_resolved = Path(workspace).resolve()
            return str(resolved).startswith(str(ws_resolved))
        return resolved.exists()
    except (ValueError, OSError):
        return False


def get_directory_tree(root_path: str, max_depth: int = 3, current_depth: int = 0) -> str:
    """Build a text-based directory tree for the system prompt."""
    if current_depth >= max_depth:
        return ""
    
    tree_lines = []
    try:
        root = Path(root_path)
        items = sorted(root.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        
        for item in items:
            if item.name in IGNORE_DIRS or item.name.startswith('.'):
                continue
            if item.suffix.lower() in BINARY_EXTENSIONS:
                continue
            
            indent = "  " * current_depth
            if item.is_dir():
                tree_lines.append(f"{indent}📁 {item.name}/")
                subtree = get_directory_tree(str(item), max_depth, current_depth + 1)
                if subtree:
                    tree_lines.append(subtree)
            else:
                size_kb = item.stat().st_size / 1024
                tree_lines.append(f"{indent}📄 {item.name} ({size_kb:.1f}KB)")
    except PermissionError:
        tree_lines.append(f"{'  ' * current_depth}⛔ [Permission Denied]")
    except Exception:
        pass
    
    return "\n".join(tree_lines)


def build_agent_system_prompt(workspace_path: str = None, contexts: list = None, code_artifacts: list = None) -> str:
    """Build the system prompt with workspace awareness for the coding agent."""
    prompt = """You are CodeChat, an AI coding agent with full access to the user's workspace.
You can read, analyze, and suggest modifications to any file in the workspace.

RULES:
1. When providing code changes, ALWAYS specify the target file path using this format:
   ```language:path/to/file.ext
   <code here>
   ```
2. Provide COMPLETE file contents when modifying files — never partial snippets.
3. You can reference any file in the workspace by its relative path.
4. When asked to create new files, use the same format with the new file path.
5. Analyze errors, suggest fixes, and explain your reasoning clearly.
6. For images in the workspace, you can reference them by path — the UI will render them.
7. Always consider the full project context when making changes.
"""

    if workspace_path and os.path.isdir(workspace_path):
        tree = get_directory_tree(workspace_path, max_depth=3)
        prompt += f"\n\nWORKSPACE: {workspace_path}\n"
        prompt += f"FILE STRUCTURE:\n{tree}\n"

    if contexts:
        prompt += "\n\nLOADED CONTEXT FILES:\n"
        for context in contexts:
            prompt += f"\n--- {context['file_path']} ---\n{context['file_content']}\n"

    if code_artifacts:
        prompt += "\n\nPREVIOUS CODE ARTIFACTS:\n"
        for artifact in code_artifacts:
            prompt += f"\n--- {artifact['language']} ---\n{artifact['content']}\n"

    return prompt


def prepare_conversation_context(conversation_id: int) -> Dict[str, Any]:
    messages = conversation_db.get_conversation_messages(conversation_id)
    contexts = conversation_db.get_project_contexts(conversation_id)
    code_artifacts = conversation_db.get_code_artifacts(conversation_id)
    workspace_path = conversation_db.get_workspace(conversation_id)

    system_context = build_agent_system_prompt(workspace_path, contexts, code_artifacts)

    return {
        "system": system_context,
        "messages": [{"role": msg['role'], "content": msg['content']} for msg in messages],
        "workspace_path": workspace_path
    }


def preprocess_code_content(content: str) -> str:
    lines = content.split('\n')
    processed_lines = []
    in_multiline_comment = False
    in_docstring = False
    docstring_quotes = None

    for line in lines:
        if not line.strip():
            continue
        if not in_docstring and not in_multiline_comment:
            docstring_start = re.match(r'\s*(\'\'\'|""").*', line)
            if docstring_start:
                in_docstring = True
                docstring_quotes = docstring_start.group(1)
                processed_lines.append(line.strip())
                continue
        if in_docstring:
            processed_lines.append(line.strip())
            if line.strip().endswith(docstring_quotes):
                in_docstring = False
            continue
        if re.match(r'^\s*#.*$', line):
            continue
        if not in_multiline_comment:
            in_string = False
            string_char = None
            for i, char in enumerate(line):
                if char in '"\'':
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                if char == '#' and not in_string:
                    line = line[:i].rstrip()
                    break
        line = ' '.join(line.split())
        if line:
            processed_lines.append(line)

    from textwrap import dedent
    processed_content = '\n'.join(processed_lines)
    processed_content = dedent(processed_content)
    return processed_content


def compress_file_content(file_path: str, content: str) -> str:
    ext = file_path.split('.')[-1].lower()
    if ext in ['json', 'yaml', 'yml']:
        return content
    return preprocess_code_content(content)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    recent_conversations = conversation_db.get_conversation_history()
    for conv in recent_conversations:
        conv['formatted_time'] = format_timestamp(conv['last_updated'])
    return render_template(
        "index.html",
        conversations=recent_conversations,
        colors=COLORS,
        model_name=OLLAMA_MODEL
    )


@app.route("/new-conversation", methods=["POST"])
def new_conversation():
    name = request.form.get("name", "New Chat")
    workspace_path = request.form.get("workspace_path", None)

    if len(name) > 100:
        name = name[:97] + "..."

    conversation_id = conversation_db.create_conversation(name, workspace_path=workspace_path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({
        "conversation_id": conversation_id,
        "name": name,
        "workspace_path": workspace_path,
        "timestamp": timestamp,
        "formatted_time": format_timestamp(timestamp)
    })


@app.route("/rename-conversation", methods=["POST"])
def rename_conversation():
    conversation_id = request.form.get("conversation_id")
    new_name = request.form.get("name")

    if not conversation_id or not new_name:
        return jsonify({"error": "Conversation ID and new name are required"}), 400
    if len(new_name) > 100:
        return jsonify({"error": "Conversation name too long"}), 400

    try:
        success = conversation_db.rename_conversation(conversation_id, new_name)
        if success:
            return jsonify({
                "message": "Conversation renamed successfully",
                "conversation_id": conversation_id,
                "new_name": new_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        return jsonify({"error": "Conversation not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/delete-conversation", methods=["POST"])
def delete_conversation():
    conversation_id = request.form.get("conversation_id")
    if not conversation_id:
        return jsonify({"error": "Conversation ID is required"}), 400

    try:
        success = conversation_db.delete_conversation(conversation_id)
        if success:
            return jsonify({
                "message": "Conversation deleted successfully",
                "conversation_id": conversation_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        return jsonify({"error": "Conversation not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/load-conversation/<int:conversation_id>")
def load_conversation(conversation_id):
    try:
        messages = conversation_db.get_conversation_messages(conversation_id)
        contexts = conversation_db.get_project_contexts(conversation_id)
        conversation_tokens = conversation_db.get_conversation_tokens(conversation_id)
        code_artifacts = conversation_db.get_code_artifacts(conversation_id)
        workspace_path = conversation_db.get_workspace(conversation_id)

        for message in messages:
            message['formatted_time'] = format_timestamp(message['timestamp'])
            message['artifacts'] = [
                artifact for artifact in code_artifacts
                if abs(datetime.strptime(artifact['timestamp'], '%Y-%m-%d %H:%M:%S').timestamp() -
                      datetime.strptime(message['timestamp'], '%Y-%m-%d %H:%M:%S').timestamp()) <= 1
            ]

        return jsonify({
            "messages": messages,
            "contexts": contexts,
            "tokens": conversation_tokens,
            "artifacts": code_artifacts,
            "workspace_path": workspace_path,
            "colors": COLORS
        })
    except Exception as e:
        print(f"{Fore.RED}Failed to load conversation {conversation_id}: {str(e)}{Style.RESET_ALL}")
        return jsonify({"error": str(e)}), 500


# ─── File System / Workspace Endpoints ────────────────────────────────────────

@app.route("/drives")
def list_drives():
    """List available drives (Windows) or root dirs."""
    drives = []
    if os.name == 'nt':
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    total, used, free = 0, 0, 0
                    import shutil
                    usage = shutil.disk_usage(drive)
                    total = usage.total
                    free = usage.free
                    drives.append({
                        "path": drive,
                        "label": f"{letter}:",
                        "total_gb": round(total / (1024**3), 1),
                        "free_gb": round(free / (1024**3), 1)
                    })
                except Exception:
                    drives.append({"path": drive, "label": f"{letter}:"})
    else:
        drives.append({"path": "/", "label": "/"})
        home = str(Path.home())
        drives.append({"path": home, "label": f"~ ({home})"})
    return jsonify({"drives": drives})


@app.route("/browse")
def browse_directory():
    """Browse a directory and return its contents."""
    dir_path = request.args.get("path", "")
    if not dir_path:
        return jsonify({"error": "Path is required"}), 400

    try:
        dir_path = str(Path(dir_path).resolve())
        if not os.path.isdir(dir_path):
            return jsonify({"error": "Directory not found"}), 404

        items = []
        for entry in sorted(Path(dir_path).iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if entry.name in IGNORE_DIRS:
                continue
            try:
                item = {
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                }
                if not entry.is_dir():
                    stat = entry.stat()
                    item["size"] = stat.st_size
                    item["ext"] = entry.suffix.lower()
                    item["is_image"] = entry.suffix.lower() in IMAGE_EXTENSIONS
                    item["is_binary"] = entry.suffix.lower() in BINARY_EXTENSIONS
                items.append(item)
            except PermissionError:
                continue

        parent = str(Path(dir_path).parent)
        return jsonify({
            "path": dir_path,
            "parent": parent if parent != dir_path else None,
            "items": items
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/read-file")
def read_file():
    """Read a file's content."""
    file_path = request.args.get("path", "")
    if not file_path:
        return jsonify({"error": "Path is required"}), 400

    try:
        fp = Path(file_path).resolve()
        if not fp.is_file():
            return jsonify({"error": "File not found"}), 404

        if fp.suffix.lower() in IMAGE_EXTENSIONS:
            return jsonify({
                "path": str(fp),
                "is_image": True,
                "image_url": f"/workspace-image?path={str(fp)}"
            })

        if fp.suffix.lower() in BINARY_EXTENSIONS:
            return jsonify({"error": "Binary files cannot be read as text"}), 400

        size = fp.stat().st_size
        if size > 5 * 1024 * 1024:
            return jsonify({"error": "File too large (>5MB)"}), 400

        content = fp.read_text(encoding='utf-8', errors='replace')
        return jsonify({
            "path": str(fp),
            "name": fp.name,
            "content": content,
            "size": size,
            "language": _detect_language(fp.name),
            "is_image": False
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/write-file", methods=["POST"])
def write_file():
    """Write content to a file in the workspace."""
    data = request.get_json() if request.is_json else {
        "path": request.form.get("path"),
        "content": request.form.get("content")
    }
    file_path = data.get("path", "")
    content = data.get("content", "")
    workspace = data.get("workspace", "")

    if not file_path:
        return jsonify({"error": "Path is required"}), 400

    try:
        fp = Path(file_path).resolve()

        if workspace and not is_safe_path(str(fp), workspace):
            return jsonify({"error": "Path is outside the workspace"}), 403

        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding='utf-8')

        return jsonify({
            "message": f"File written successfully: {fp.name}",
            "path": str(fp),
            "size": len(content)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/set-workspace", methods=["POST"])
def set_workspace():
    """Set the workspace path for a conversation."""
    conversation_id = request.form.get("conversation_id")
    workspace_path = request.form.get("workspace_path", "")

    if not conversation_id:
        return jsonify({"error": "Conversation ID is required"}), 400

    try:
        resolved = str(Path(workspace_path).resolve()) if workspace_path else None
        if resolved and not os.path.isdir(resolved):
            return jsonify({"error": "Directory not found"}), 404

        success = conversation_db.set_workspace(conversation_id, resolved)
        if success:
            return jsonify({
                "message": "Workspace set successfully",
                "workspace_path": resolved
            })
        return jsonify({"error": "Conversation not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/workspace-image")
def workspace_image():
    """Serve an image file from the filesystem."""
    file_path = request.args.get("path", "")
    if not file_path:
        abort(400)

    fp = Path(file_path).resolve()
    if not fp.is_file():
        abort(404)
    if fp.suffix.lower() not in IMAGE_EXTENSIONS:
        abort(400)

    mime = mimetypes.guess_type(str(fp))[0] or 'application/octet-stream'
    return send_file(str(fp), mimetype=mime)


@app.route("/add-file-context", methods=["POST"])
def add_file_context():
    """Add a workspace file to the conversation context."""
    conversation_id = request.form.get("conversation_id")
    file_path = request.form.get("file_path")

    if not conversation_id or not file_path:
        return jsonify({"error": "Conversation ID and file path are required"}), 400

    try:
        fp = Path(file_path).resolve()
        if not fp.is_file():
            return jsonify({"error": "File not found"}), 404

        if fp.suffix.lower() in BINARY_EXTENSIONS:
            return jsonify({"error": "Binary files cannot be added as context"}), 400

        content = fp.read_text(encoding='utf-8', errors='replace')
        compressed = compress_file_content(fp.name, content)

        metadata = {
            "original_size": len(content),
            "compressed_size": len(compressed),
            "source": "workspace"
        }

        context_id = conversation_db.add_project_context(
            conversation_id, str(fp), compressed,
            file_type=_detect_language(fp.name),
            metadata=json.dumps(metadata)
        )

        return jsonify({
            "message": f"Added {fp.name} to context",
            "context_id": context_id,
            "file_path": str(fp),
            "size": len(compressed)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/add-folder-context", methods=["POST"])
def add_folder_context():
    """Recursively add all text files in a folder to conversation context."""
    conversation_id = request.form.get("conversation_id")
    folder_path = request.form.get("folder_path")
    max_files = int(request.form.get("max_files", 50))

    if not conversation_id or not folder_path:
        return jsonify({"error": "Conversation ID and folder path are required"}), 400

    try:
        root = Path(folder_path).resolve()
        if not root.is_dir():
            return jsonify({"error": "Directory not found"}), 404

        added = []
        skipped = []
        for fp in sorted(root.rglob("*")):
            if len(added) >= max_files:
                break
            if not fp.is_file():
                continue
            if any(part in IGNORE_DIRS for part in fp.parts):
                continue
            if fp.suffix.lower() in BINARY_EXTENSIONS or fp.suffix.lower() in IMAGE_EXTENSIONS:
                skipped.append(fp.name)
                continue
            if fp.stat().st_size > 1 * 1024 * 1024:
                skipped.append(fp.name)
                continue

            try:
                content = fp.read_text(encoding='utf-8', errors='replace')
                compressed = compress_file_content(fp.name, content)
                metadata = json.dumps({
                    "original_size": len(content),
                    "compressed_size": len(compressed),
                    "source": "workspace_folder"
                })
                conversation_db.add_project_context(
                    conversation_id, str(fp), compressed,
                    file_type=_detect_language(fp.name),
                    metadata=metadata
                )
                added.append(str(fp))
            except Exception:
                skipped.append(fp.name)

        return jsonify({
            "message": f"Added {len(added)} files from {root.name}/",
            "added_count": len(added),
            "skipped_count": len(skipped),
            "files": [Path(f).name for f in added]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/remove-file-context", methods=["POST"])
def remove_file_context():
    """Remove a file from conversation context."""
    conversation_id = request.form.get("conversation_id")
    file_path = request.form.get("file_path")

    if not conversation_id or not file_path:
        return jsonify({"error": "Conversation ID and file path are required"}), 400

    try:
        with conversation_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM project_contexts 
                WHERE conversation_id = ? AND file_path = ?
            ''', (conversation_id, file_path))
            if cursor.rowcount > 0:
                return jsonify({"message": f"Removed context: {file_path}"})
            return jsonify({"error": "Context not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Process / Chat Endpoint ─────────────────────────────────────────────────

@app.route("/process", methods=["POST"])
def process():
    conversation_id = request.form.get("conversation_id")
    if not conversation_id:
        conversation_id = conversation_db.create_conversation()

    prompt = request.form.get("prompt")
    file = request.files.get("file")

    if not prompt and not file:
        return jsonify({"error": "Please provide a prompt or attach a file."}), 400

    try:
        if file:
            filename = file.filename
            file_content = file.read().decode("utf-8")
            compressed_content = compress_file_content(filename, file_content)
            metadata = {
                "original_size": len(file_content),
                "compressed_size": len(compressed_content),
                "compression_ratio": round(len(compressed_content) / len(file_content) * 100, 2)
            }
            conversation_db.add_project_context(
                conversation_id, filename, compressed_content,
                metadata=json.dumps(metadata)
            )

        context = prepare_conversation_context(conversation_id)
        context["messages"].append({"role": "user", "content": prompt or ""})

        project_contexts = conversation_db.get_project_contexts(conversation_id)
        api_messages = [{"role": "system", "content": context["system"]}] + context["messages"]

        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=api_messages,
            max_tokens=4096,
            temperature=0.7
        )

        response_text = response.choices[0].message.content
        response_text = strip_thinking_tokens(response_text)

        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        conversation_db.add_message(conversation_id, "user", prompt, input_tokens)
        conversation_db.add_message(conversation_id, "assistant", response_text, output_tokens=output_tokens)

        artifacts = []
        code_block_pattern = r'```(\w+)?(?::([^\n]+))?\n([\s\S]*?)```'
        for match in re.finditer(code_block_pattern, response_text):
            language = match.group(1) or 'text'
            file_path = match.group(2) or None
            code_content = match.group(3).strip()

            if code_content:
                if not language or language == 'text':
                    if 'def ' in code_content or 'class ' in code_content or 'import ' in code_content:
                        language = 'python'
                    elif 'function ' in code_content or 'const ' in code_content or 'let ' in code_content:
                        language = 'javascript'
                    elif '<' in code_content and '>' in code_content:
                        language = 'html'
                    elif '{' in code_content and '}' in code_content and ';' in code_content:
                        language = 'css'

                artifact_id = conversation_db.add_code_artifact(
                    conversation_id, code_content, language
                )

                artifacts.append({
                    "id": artifact_id,
                    "content": code_content,
                    "language": language,
                    "file_path": file_path,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

        total_tokens = conversation_db.get_conversation_tokens(conversation_id)

        response_data = {
            "conversation_id": conversation_id,
            "response": response_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "artifacts": artifacts,
            "workspace_path": context.get("workspace_path"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": {
                "model": OLLAMA_MODEL,
                "conversation_name": conversation_db.get_conversation_name(conversation_id),
                "has_context_files": bool(project_contexts),
                "artifact_count": len(artifacts)
            }
        }

        print(f"{Fore.GREEN}Successfully processed request for conversation {conversation_id}{Style.RESET_ALL}")
        print(f"Generated {len(artifacts)} code artifacts")
        print(f"Total tokens: {total_tokens['total_tokens']}")

        return jsonify(response_data)

    except ConnectionError as conn_error:
        error_message = f"Ollama Connection Error: {str(conn_error)} - Is Ollama running at {OLLAMA_BASE_URL}?"
        print(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
        return jsonify({"error": error_message}), 503

    except Exception as e:
        error_message = f"Processing Error: {str(e)}"
        print(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
        return jsonify({
            "error": error_message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _detect_language(filename: str) -> str:
    ext_map = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'jsx', '.tsx': 'tsx', '.html': 'html', '.htm': 'html',
        '.css': 'css', '.scss': 'scss', '.sass': 'sass', '.less': 'less',
        '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
        '.xml': 'xml', '.md': 'markdown', '.sql': 'sql',
        '.sh': 'bash', '.bash': 'bash', '.bat': 'batch', '.ps1': 'powershell',
        '.java': 'java', '.kt': 'kotlin', '.go': 'go', '.rs': 'rust',
        '.rb': 'ruby', '.php': 'php', '.cs': 'csharp', '.cpp': 'cpp',
        '.c': 'c', '.h': 'c', '.hpp': 'cpp', '.swift': 'swift',
        '.r': 'r', '.lua': 'lua', '.dart': 'dart',
        '.toml': 'toml', '.ini': 'ini', '.cfg': 'ini',
        '.env': 'bash', '.gitignore': 'bash', '.dockerignore': 'bash',
        '.dockerfile': 'docker', '.tf': 'hcl',
    }
    ext = Path(filename).suffix.lower()
    return ext_map.get(ext, 'plaintext')


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        "error": "Resource not found",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 500


if __name__ == "__main__":
    print(f"{Fore.CYAN}Starting CodeChat Agent Server{Style.RESET_ALL}")
    print(f"Environment: {'Development' if app.debug else 'Production'}")
    print(f"LLM Backend: Ollama @ {OLLAMA_BASE_URL}")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Database: {conversation_db.db_path}")

    try:
        conversation_db._migrate_database()
        print(f"{Fore.GREEN}Database initialized successfully{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Database initialization failed: {str(e)}{Style.RESET_ALL}")
        raise

    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        warmup_thread = threading.Thread(target=warmup_model, daemon=True)
        warmup_thread.start()

    app.run(
        debug=True,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        use_reloader=True
    )
