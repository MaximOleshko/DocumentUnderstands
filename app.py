import threading
import webbrowser
import time
import atexit
import logging

from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO

from converts.markdown_to_ast import MarkdownParser
from exports.document_export import OUTPUT_FORMATS, export_document, export_from_docx_bytes
from exports.settings import ExportSettings
from imports.document_processor import process_docx_bytes

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

HOST = '127.0.0.1'
PORT = 5000

TEXT_EXTENSIONS = {'md', 'markdown', 'txt'}
DOCUMENT_EXTENSIONS = {'docx'}

# Werkzeug setup
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

logging.getLogger("socketio").setLevel(logging.ERROR)
logging.getLogger("engineio").setLevel(logging.ERROR)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    output_format = request.form.get('output_format', 'docx')
    if output_format not in OUTPUT_FORMATS:
        return render_template('index.html', error='Please select a valid export format.'), 400

    settings = ExportSettings.from_form(request.form)
    uploaded = request.files.get('source_file')

    try:
        if uploaded and uploaded.filename:
            extension = uploaded.filename.rsplit('.', 1)[-1].lower()
            if extension in DOCUMENT_EXTENSIONS:
                processed = process_docx_bytes(uploaded.read(), settings)
                buffer = export_from_docx_bytes(processed, output_format)
            elif extension in TEXT_EXTENSIONS:
                markdown_text = uploaded.read().decode('utf-8').strip()
                if not markdown_text:
                    return render_template('index.html', error='The uploaded file is empty.'), 400
                buffer = _convert_markdown(markdown_text, settings, output_format)
            else:
                return render_template(
                    'index.html',
                    error='Supported files: .md, .markdown, .txt, .docx',
                ), 400
        else:
            markdown_text = request.form.get('markdown', '').strip()
            if not markdown_text:
                return render_template(
                    'index.html',
                    error='Enter Markdown text or upload a document.',
                ), 400
            buffer = _convert_markdown(markdown_text, settings, output_format)
    except UnicodeDecodeError:
        return render_template('index.html', error='Could not read file. Please use UTF-8 encoding.'), 400
    except Exception as exc:
        return render_template('index.html', error=f'Conversion failed: {exc}'), 500

    meta = OUTPUT_FORMATS[output_format]
    return send_file(
        buffer,
        as_attachment=True,
        download_name=meta['filename'],
        mimetype=meta['mimetype'],
    )

def _convert_markdown(markdown_text: str, settings: ExportSettings, output_format: str):
    parser = MarkdownParser()
    ast = parser.parse(markdown_text)
    return export_document(ast, settings, output_format)


def _open_browser():
    webbrowser.open(f'http://{HOST}:{PORT}')

def on_shutdown():
    print("Shutting down...")
    try:
        socketio.emit('close_tab')
        time.sleep(0.3)
    except:
        pass

atexit.register(on_shutdown)

if __name__ == '__main__':
    print("DocumentUnderstands v1.0 started.")
    print(f"Application opening on {HOST}, port {PORT} automatically... Please check your browser.")
    print("If you want to exit, press Ctrl + C or just close this window.")

    threading.Timer(1.0, _open_browser).start()
    app.run(host=HOST, port=PORT, debug=False)
