from flask import Flask, request, render_template, jsonify, session, flash
import os
import anthropic
import json
from dotenv import load_dotenv
from database import ConversationDatabase
from typing import List, Dict, Any
from datetime import datetime
import pytz
from flask_assets import Environment, Bundle
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Initialize Flask-Assets
assets = Environment(app)
assets.url = app.static_url_path
scss = Bundle('scss/main.scss', filters='pyscss', output='css/main.css')
assets.register('scss_all', scss)

# Color scheme
COLORS = {
    'primary': '#1E88E5',    # Modern blue
    'secondary': '#424242',  # Dark gray
    'accent': '#00C853',     # Green
    'error': '#D32F2F',      # Red
    'background': '#FAFAFA', # Light gray
    'text': '#212121',       # Near black
    'code_bg': '#263238'     # Dark blue-gray
}

# Initialize database
conversation_db = ConversationDatabase()

# Load the Claude API key from the environment variable
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not CLAUDE_API_KEY:
    print(f"{Fore.RED}API key is missing. Please set the ANTHROPIC_API_KEY environment variable in your .env file.{Style.RESET_ALL}")
    raise ValueError("API key is missing")

# Initialize the Anthropic client
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

def format_timestamp(timestamp: str) -> str:
    """
    Flexibly parse and format timestamp with multiple potential input formats
    
    Supports:
    - '%Y-%m-%d %H:%M:%S.%f'
    - '%Y-%m-%d %H:%M:%S'
    """
    try:
        # Try parsing with microseconds first
        try:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            # Fall back to parsing without microseconds
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        
        local_tz = pytz.timezone('UTC')  # Change to your timezone
        local_dt = local_tz.localize(dt)
        return local_dt.strftime('%B %d, %Y %I:%M %p')
    except ValueError as e:
        # Log the error and return the original timestamp if parsing fails
        print(f"Error parsing timestamp {timestamp}: {e}")
        return timestamp  # Return original string if parsing fails

def prepare_conversation_context(conversation_id: int) -> Dict[str, Any]:
    """
    Retrieve and prepare conversation context for Claude API with improved token optimization
    """
    messages = conversation_db.get_conversation_messages(conversation_id)
    contexts = conversation_db.get_project_contexts(conversation_id)
    code_artifacts = conversation_db.get_code_artifacts(conversation_id)
    
    system_context = """
    You are CodeChat, an AI assistant specialized in software development.
    When processing code, you must ensure the following:
    1. Code logic is correct and complete.
    2. The code is ready to integrate into a working application.
    3. You must check for missing imports, dependencies, or incorrect syntax.
    4. If modifications are required, provide the full updated code with proper reasoning.
    5. Always refer to the codebase in the attached file for context and ensure consistency.
    6. Your output must be clean, well-commented, and adhere to best practices and coding standards.
    7. Any suggestions should aim at improving readability, maintainability, and performance.
    8. When providing code updates, always give the full file, ensuring it's ready to be copied and pasted.
    """
    
    if contexts:
        system_context += "\n\nProject Context Files:\n"
        for context in contexts:
            # Compress the file content before adding to context
            compressed_content = compress_file_content(
                context['file_path'],
                context['file_content']
            )
            system_context += f"\n# File: {context['file_path']}\n{compressed_content}\n"
    
    if code_artifacts:
        system_context += "\n\nCode Artifacts:\n"
        for artifact in code_artifacts:
            compressed_content = compress_file_content(
                f"artifact.{artifact['language']}",
                artifact['content']
            )
            system_context += f"\n# Language: {artifact['language']}\n{compressed_content}\n"
    
    return {
        "system": system_context,
        "messages": [{"role": msg['role'], "content": msg['content']} for msg in messages]
    }

def preprocess_code_content(content: str) -> str:
    """
    Preprocess code content to reduce token usage while maintaining context.
    
    This function:
    1. Removes empty lines
    2. Strips whitespace
    3. Removes comments (while keeping docstrings)
    4. Compresses multiple spaces
    """
    import re
    from textwrap import dedent
    
    # Split into lines for processing
    lines = content.split('\n')
    processed_lines = []
    
    in_multiline_comment = False
    in_docstring = False
    docstring_quotes = None
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Handle docstrings
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
            
        # Skip comment lines
        if re.match(r'^\s*#.*$', line):
            continue
            
        # Remove inline comments while preserving strings
        if not in_multiline_comment:
            # Handle strings first
            parts = []
            last_end = 0
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
                    
        # Remove extra whitespace
        line = ' '.join(line.split())
        
        if line:
            processed_lines.append(line)
            
    # Join lines and dedent
    processed_content = '\n'.join(processed_lines)
    processed_content = dedent(processed_content)
    
    return processed_content

def compress_file_content(file_path: str, content: str) -> str:
    """
    Compress file content based on file type while maintaining readability.
    """
    ext = file_path.split('.')[-1].lower()
    
    # Don't compress certain file types
    if ext in ['json', 'yaml', 'yml']:
        return content
        
    return preprocess_code_content(content)

@app.route("/")
def index():
    """Render the main application interface"""
    recent_conversations = conversation_db.get_conversation_history()
    for conv in recent_conversations:
        conv['formatted_time'] = format_timestamp(conv['last_updated'])
    return render_template(
        "index.html",
        conversations=recent_conversations,
        colors=COLORS
    )

@app.route("/new-conversation", methods=["POST"])
def new_conversation():
    """Create a new conversation with improved naming"""
    name = request.form.get("name", "New Chat")
    
    # Clean up the name if it's too long
    if len(name) > 100:
        name = name[:97] + "..."
    
    conversation_id = conversation_db.create_conversation(name)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return jsonify({
        "conversation_id": conversation_id,
        "name": name,
        "timestamp": timestamp,
        "formatted_time": format_timestamp(timestamp)
    })

@app.route("/rename-conversation", methods=["POST"])
def rename_conversation():
    """Rename an existing conversation with validation"""
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
    """Soft delete a conversation with confirmation"""
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
    """Load a conversation with all associated data"""
    try:
        messages = conversation_db.get_conversation_messages(conversation_id)
        contexts = conversation_db.get_project_contexts(conversation_id)
        conversation_tokens = conversation_db.get_conversation_tokens(conversation_id)
        code_artifacts = conversation_db.get_code_artifacts(conversation_id)
        
        # Format timestamps for display
        for message in messages:
            message['formatted_time'] = format_timestamp(message['timestamp'])
            # Associate artifacts with messages based on timestamp
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
            "colors": COLORS
        })
    except Exception as e:
        logger.error(f"Failed to load conversation {conversation_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/process", methods=["POST"])
def process():
    """Process user input with improved error handling and response formatting"""
    conversation_id = request.form.get("conversation_id")
    if not conversation_id:
        conversation_id = conversation_db.create_conversation()

    prompt = request.form.get("prompt")
    file = request.files.get("file")

    if not prompt and not file:
        return jsonify({"error": "Please provide a prompt or attach a file."}), 400

    try:
        # Handle file upload with compression
        if file:
            filename = file.filename
            file_content = file.read().decode("utf-8")
            
            # Compress file content before storing
            compressed_content = compress_file_content(filename, file_content)
            
            # Store original file size and compressed size in metadata
            metadata = {
                "original_size": len(file_content),
                "compressed_size": len(compressed_content),
                "compression_ratio": round(len(compressed_content) / len(file_content) * 100, 2)
            }
            
            conversation_db.add_project_context(
                conversation_id,
                filename,
                compressed_content,
                metadata=json.dumps(metadata)
            )

        # Prepare and send request to Claude API
        context = prepare_conversation_context(conversation_id)
        context["messages"].append({"role": "user", "content": prompt or ""})

        # Get project contexts for validation
        project_contexts = conversation_db.get_project_contexts(conversation_id)

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            temperature=0.7,
            system=context["system"],
            messages=context["messages"]
        )
        
        response_text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # Save messages and update tokens
        conversation_db.add_message(conversation_id, "user", prompt, input_tokens)
        conversation_db.add_message(conversation_id, "assistant", response_text, output_tokens=output_tokens)

        # Process code artifacts
        artifacts = []
        import re

        # First pass: Extract code blocks with language tags
        code_block_pattern = r'```(\w+)?\n([\s\S]*?)```'
        for match in re.finditer(code_block_pattern, response_text):
            language = match.group(1) or 'text'
            code_content = match.group(2).strip()
            
            if code_content:
                # Detect language if not specified or is 'text'
                if not language or language == 'text':
                    if 'def ' in code_content or 'class ' in code_content or 'import ' in code_content:
                        language = 'python'
                    elif 'function ' in code_content or 'const ' in code_content or 'let ' in code_content:
                        language = 'javascript'
                    elif '<' in code_content and '>' in code_content:
                        language = 'html'
                    elif '{' in code_content and '}' in code_content and ';' in code_content:
                        language = 'css'
                
                # Store artifact in database
                artifact_id = conversation_db.add_code_artifact(
                    conversation_id, 
                    code_content, 
                    language
                )
                
                # Add to response artifacts
                artifacts.append({
                    "id": artifact_id,
                    "content": code_content,
                    "language": language,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                # Replace code block with placeholder to avoid double-processing
                response_text = response_text.replace(match.group(0), f'[Code block in {language}]')

        # Second pass: Look for code patterns in remaining text
        code_patterns = [
            (r'(?:^|\n)((?:def|class|async def|from|import) [^\n]+(?:\n(?:    |\t)[^\n]+)*)', 'python'),
            (r'(?:^|\n)((?:function|const|let|var|class|async function) [^\n]+(?:\n    [^\n]+)*)', 'javascript'),
            (r'(?:^|\n)((?:<[^>]+>)(?:\n|.)*?(?:</[^>]+>))', 'html'),
            (r'(?:^|\n)([a-z-]+\s*{[^}]*})', 'css')
        ]

        for pattern, lang in code_patterns:
            matches = re.finditer(pattern, response_text)
            for match in matches:
                code_content = match.group(1).strip()
                if code_content and not any(a['content'] == code_content for a in artifacts):
                    # Store artifact
                    artifact_id = conversation_db.add_code_artifact(
                        conversation_id,
                        code_content,
                        lang
                    )
                    
                    artifacts.append({
                        "id": artifact_id,
                        "content": code_content,
                        "language": lang,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

        # Get updated token counts
        total_tokens = conversation_db.get_conversation_tokens(conversation_id)

        # Prepare the enhanced response
        response_data = {
            "conversation_id": conversation_id,
            "response": response_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "artifacts": artifacts,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": {
                "model": "claude-3-5-sonnet-20241022",
                "conversation_name": conversation_db.get_conversation_name(conversation_id),
                "has_context_files": bool(project_contexts),
                "artifact_count": len(artifacts)
            }
        }

        # Log successful processing
        print(f"{Fore.GREEN}Successfully processed request for conversation {conversation_id}{Style.RESET_ALL}")
        print(f"Generated {len(artifacts)} code artifacts")
        print(f"Total tokens: {total_tokens['total_tokens']}")

        return jsonify(response_data)

    except anthropic.APIError as api_error:
        error_message = f"Claude API Error: {str(api_error)}"
        print(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
        return jsonify({"error": error_message}), 503

    except Exception as e:
        error_message = f"Processing Error: {str(e)}"
        print(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
        return jsonify({
            "error": error_message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Resource not found",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal server error",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 500

if __name__ == "__main__":
    # Print startup information
    print(f"{Fore.CYAN}Starting CodeChat Server{Style.RESET_ALL}")
    print(f"Environment: {'Development' if app.debug else 'Production'}")
    print(f"Database: {conversation_db.db_path}")
    print(f"Color Scheme: {', '.join(f'{k}: {v}' for k, v in COLORS.items())}")
    
    # Initialize the database
    try:
        conversation_db._migrate_database()
        print(f"{Fore.GREEN}Database initialized successfully{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Database initialization failed: {str(e)}{Style.RESET_ALL}")
        raise

    # Start the application
    app.run(
        debug=True,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        use_reloader=True
    )