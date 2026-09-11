# DocumentUnderstands
## v1.0

### Main
**DocumentUnderstands** is an application on **Python (Flask)**, which used to convert Markdown syntax into documents,
supporting `.docx`, `.odt`, `.pdf` extensions.

### Usage
Run the executable file, then the web application will launch in the browser. **On Linux make sure that you are
launching the application via terminal.**

### Build
For assembly, you can use ***PyInstaller*** following this:

#### Linux / MacOS
```
pyinstaller --onefile --console \
    --hidden-import engineio.async_drivers.threading \
    --hidden-import socketio \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --name DocumentUnderstands app.py
```

#### Windows
```
pyinstaller --onefile --console \
    --hidden-import engineio.async_drivers.threading \
    --hidden-import socketio \
    --add-data "templates;templates" \
    --add-data "static;static" \
    --name DocumentUnderstands app.py
```

**NOTICE**: You should use some important flags.

| Flag              | Reason                                                                                                                                                                            |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--console`       | Opens a terminal window. Required for graceful shutdown and closing browser tabs when the application stops.                                                                      |
| `--add-data`      | Bundles the `templates/` and `static/` folders into the executable. Flask needs these to render HTML and serve static files. Use `:` separator on Linux/macOS and `;` on Windows. |
| `--hidden-import` | Forces PyInstaller to include `socketio` and `engineio.async_drivers.threading` modules, which are loaded dynamically at runtime and would otherwise be missed.                   |

---

### Features

#### Input Methods
- **Paste Markdown** directly into the editor
- **Upload files**: `.md`, `.markdown`, `.txt` (loaded into editor), `.docx` (extracted as Markdown source)
- **Drag & Drop** support for all supported file types

#### Export Settings
- **Text colors**: Preset colors (black, gray, navy, green, burgundy, brown) or custom HEX color
- **Table text color**: Separate color control for table cells
- **Font family**: Choose from Times New Roman, Arial, Calibri, Georgia, Cambria, Verdana, Garamond, or Word default
- **Table mode**:
  - *Converter*: Rich formatting inside cells (bold, italic, links, etc.)
  - *Word-compatible*: Explicit borders, plain text for maximum compatibility
- **Formatting options**:
  - Remove backticks (inline `code` → plain text)
  - Plain code blocks (no monospace styling)
  - Strip bold/italic formatting
  - Remove blockquotes
  - Remove emojis (✅ ❌ and similar symbols)
  - Remove horizontal rules
  - Remove hidden text (white, vanished, or tiny runs in uploaded documents)

#### Supported Export Formats
- **DOCX**: Direct export using `python-docx`
- **ODT**: Converted via LibreOffice (requires LibreOffice installed)
- **PDF**: Converted via LibreOffice (requires LibreOffice installed)

#### User Interface
- **Dark/Light theme** with automatic persistence
- **Responsive design** for desktop and mobile
- **Real-time character count**
- **File preview** for uploaded documents
- **Keyboard shortcut**: `Ctrl+Enter` (or `Cmd+Enter` on macOS) to submit

#### Technical Features
- **Graceful shutdown**: Browser tabs close automatically when the application stops
- **Cross-platform**: Works on Windows, Linux, and macOS
- **Single executable**: No Python installation required for end users
- **Large file support**: Up to 32 MB uploads

---

### Installation (for development)

1. **Clone the repository**:
```bash
git clone <repository-url>
cd DocumentUnderstands
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Install LibreOffice** (required for ODT/PDF export):
   - **Ubuntu/Debian**: `sudo apt install libreoffice`
   - **Fedora**: `sudo dnf install libreoffice`
   - **macOS**: `brew install --cask libreoffice`
   - **Windows**: Download from [libreoffice.org](https://www.libreoffice.org/download/)

5. **Run the application**:
```bash
python app.py
```

The browser will open automatically at `http://127.0.0.1:5000`.

---

### Project Structure

```
DocumentUnderstands/
├── app.py                          # Flask application entry point
├── requirements.txt                # Python dependencies
├── converts/
│   ├── __init__.py
│   ├── ast_nodes.py               # AST node dataclasses
│   └── markdown_to_ast.py         # Markdown parser
├── exports/
│   ├── __init__.py
│   ├── document_export.py         # Export orchestrator
│   ├── docx_spaces.py             # Whitespace preservation utilities
│   ├── export_to_docx.py          # AST to DOCX converter
│   ├── settings.py                # Export settings dataclass
│   └── text_utils.py              # Text utilities (emoji removal)
├── imports/
│   ├── document_processor.py      # DOCX to Markdown extractor
│   └── file_reader.py             # File reading utilities
├── static/
│   └── logo-128px.png             # Application logo
└── templates/
    └── index.html                 # Web interface
```

---

### Requirements

- **Python**: 3.8 or higher (for development)
- **LibreOffice**: Required for ODT and PDF export
- **Supported browsers**: Chrome, Firefox, Edge, Safari (modern versions)

---

### Dependencies

- `flask`: Web framework
- `flask-socketio`: WebSocket support for browser tab management
- `python-docx`: DOCX file manipulation

---

### Known Limitations

1. **Nested lists**: Current parser does not support nested lists (e.g., lists inside lists)
2. **Complex Markdown**: Some advanced Markdown features (footnotes, definition lists, task lists) are not supported
3. **Image support**: Images must be URLs (not local files) and require internet connection
4. **LibreOffice dependency**: ODT and PDF export require LibreOffice to be installed on the system
5. **Browser security**: Some browsers may prevent automatic tab closing after user interaction (form submission). In this case, a "Server stopped" message is displayed instead.

---

### Troubleshooting

**Problem**: Application doesn't close when terminal window is closed.

**Solution**: Ensure you're running with `--console` flag when building with PyInstaller.

**Problem**: ODT/PDF export fails with "LibreOffice not found" error.

**Solution**: Install LibreOffice and ensure `libreoffice` or `soffice` command is in your system PATH.

**Problem**: Browser tab doesn't close automatically after conversion.

**Solution**: This is a browser security restriction. The tab will display "Server stopped" message instead.

---

### License

MIT

---

### Contact

Maxim Oleshko

Email: maksimoleshko05@gmail.com