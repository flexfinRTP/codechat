give a formatted readme based on the code.Here's a formatted README.md for your project:

# CodeChat - AI Code Assistant

An intelligent code assistant powered by Claude AI that helps developers with code analysis, generation, and improvements.

## Features

- Real-time code assistance and suggestions
- File upload support for code context
- Conversation history and management
- Project context preservation
- Syntax highlighting and code formatting
- Responsive UI with sidebar navigation
- Context windows for reference

## Prerequisites

- Python 3.11+
- Anthropic API Key

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/codechat.git
cd codechat
```

2. Create and activate virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Unix/MacOS
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root and add your Anthropic API key:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

1. delete venv folder

2. python -m venv venv

3. venv\Scripts\activate

4. pip install -r requirements.txt

5. Start the application:
```bash
python app.py
```

6. Open your browser and navigate to `http://localhost:5000`

7. Features:
   - Create new conversations using the "+" button
   - Upload code files for context
   - Enter prompts for code assistance
   - View conversation history in the sidebar
   - Create context windows for reference
   - Copy responses to clipboard

## Project Structure

```
codechat/
├── app.py              # Main Flask application
├── database.py         # SQLite database operations
├── static/
│   ├── script.js      # Frontend JavaScript
│   └── style.css      # CSS styles
├── templates/
│   └── index.html     # Main HTML template
├── requirements.txt    # Python dependencies
└── conversations.db    # SQLite database
```

## Dependencies

- Flask
- Anthropic API
- SQLite
- Python-dotenv
- Additional requirements in requirements.txt

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Anthropic for the Claude AI API
- Flask framework
- SQLite database