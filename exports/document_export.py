import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional

from converts.ast_nodes import Document
from exports.export_to_docx import ExportToDocx
from exports.settings import ExportSettings

OUTPUT_FORMATS = {
    'docx': {
        'filename': 'document.docx',
        'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    },
    'odt': {
        'filename': 'document.odt',
        'mimetype': 'application/vnd.oasis.opendocument.text',
    },
    'pdf': {
        'filename': 'document.pdf',
        'mimetype': 'application/pdf',
    },
}

LIBREOFFICE_FORMATS = frozenset({'odt', 'pdf'})


def export_document(ast: Document, settings: ExportSettings, output_format: str) -> BytesIO:
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f'Unsupported format: {output_format}')

    if output_format == 'docx':
        return _export_to_docx(ast, settings)

    docx_buffer = _export_to_docx(ast, settings)
    return _convert_docx_with_libreoffice(docx_buffer, output_format)


def export_from_docx_bytes(docx_buffer: BytesIO, output_format: str) -> BytesIO:
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f'Unsupported format: {output_format}')
    if output_format == 'docx':
        docx_buffer.seek(0)
        return docx_buffer
    return _convert_docx_with_libreoffice(docx_buffer, output_format)


def _export_to_docx(ast: Document, settings: ExportSettings) -> BytesIO:
    buffer = BytesIO()
    exporter = ExportToDocx(settings=settings)
    exporter.export(ast)
    exporter.doc.save(buffer)
    buffer.seek(0)
    return buffer


def _find_libreoffice() -> Optional[str]:
    for command in ('libreoffice', 'soffice'):
        if shutil.which(command):
            return command
    return None


def _convert_docx_with_libreoffice(docx_buffer: BytesIO, target_format: str) -> BytesIO:
    if target_format not in LIBREOFFICE_FORMATS:
        raise ValueError(f'LibreOffice does not support format: {target_format}')

    command = _find_libreoffice()
    if not command:
        raise RuntimeError(
            'Install LibreOffice (libreoffice or soffice) to export ODT and PDF.'
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source = temp_path / 'document.docx'
        source.write_bytes(docx_buffer.getvalue())

        result = subprocess.run(
            [
                command,
                '--headless',
                '--convert-to',
                target_format,
                '--outdir',
                str(temp_path),
                str(source),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or 'unknown error'
            raise RuntimeError(
                f'LibreOffice failed to create {target_format.upper()}: {stderr}'
            )

        output_file = temp_path / f'document.{target_format}'
        if not output_file.exists():
            raise RuntimeError('LibreOffice did not produce an output file.')

        return BytesIO(output_file.read_bytes())
