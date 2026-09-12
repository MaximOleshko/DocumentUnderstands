/* =========================================================
   DocumentUnderstands — main script
   ========================================================= */
(function () {
    'use strict';

    // ---- DOM cache ----
    const root          = document.documentElement;
    const textarea      = document.getElementById('markdown');
    const charCount     = document.getElementById('char-count');
    const form          = document.getElementById('convert-form');
    const submitBtn     = document.getElementById('submit-btn');
    const btnLabel      = document.getElementById('btn-label');
    const dropZone      = document.getElementById('drop-zone');
    const fileInput     = document.getElementById('file-input');
    const uploadBtn     = document.getElementById('upload-btn');
    const fileBadge     = document.getElementById('file-badge');
    const exportHint    = document.getElementById('export-hint');
    const sourceFile    = document.getElementById('source-file');
    const documentPanel = document.getElementById('document-panel');
    const documentName  = document.getElementById('document-name');
    const sourceTitle   = document.getElementById('source-title');
    const clearDocument = document.getElementById('clear-document');
    const editorCard    = document.querySelector('.editor-card');
    const toast         = document.getElementById('toast');
    const formatRadios  = document.querySelectorAll('input[name="output_format"]');
    const themeToggle   = document.getElementById('theme-toggle');
    const themeIcon     = document.getElementById('theme-icon');
    const themeLabel    = document.getElementById('theme-label');

    // Hidden text settings
    const stripHiddenCheckbox = document.getElementById('strip-hidden-checkbox');
    const hiddenTextSettings  = document.getElementById('hidden-text-settings');
    const minSizeSlider       = document.getElementById('min-size-slider');
    const minSizeInput        = document.getElementById('min-size-input');
    const customColorsContainer = document.getElementById('custom-colors-container');
    const addColorBtn         = document.getElementById('add-color-btn');

    let colorCounter = 0;

    const formatLabels = {
        docx: { file: 'document.docx', action: 'Convert to DOCX' },
        odt:  { file: 'document.odt',  action: 'Convert to ODT'  },
        pdf:  { file: 'document.pdf',  action: 'Convert to PDF'  },
    };

    // ---- Socket.IO: graceful close ----
    if (typeof io !== 'undefined') {
        const socket = io();
        socket.on('close_tab', function () {
            console.log('Closing tab by signal...');
            window.open('', '_self', '');
            window.close();
        });
    }

    // ---- Toast ----
    function showToast(message) {
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2800);
    }

    // ---- Counter ----
    function updateCount() {
        if (sourceFile.files.length) {
            const sizeKb = Math.max(1, Math.round(sourceFile.files[0].size / 1024));
            charCount.textContent = `${sizeKb.toLocaleString('en-US')} KB document`;
            return;
        }
        charCount.textContent = `${textarea.value.length.toLocaleString('en-US')} characters`;
    }

    // ---- Document mode (docx attached) ----
    function setDocumentMode(file) {
        const transfer = new DataTransfer();
        if (file) transfer.items.add(file);
        sourceFile.files = transfer.files;

        const attached = Boolean(file);
        documentPanel.hidden = !attached;
        editorCard.classList.toggle('document-mode', attached);
        sourceTitle.textContent = attached ? 'Document' : 'Markdown';
        textarea.required = !attached;
        if (attached) {
            documentName.textContent = file.name;
            fileBadge.textContent = file.name;
            fileBadge.classList.add('visible');
        } else {
            fileBadge.textContent = '';
            fileBadge.classList.remove('visible');
        }
        updateCount();
    }

    // ---- Format pills UI ----
    function updateFormatUi() {
        const selected = document.querySelector('input[name="output_format"]:checked')?.value || 'docx';
        const meta = formatLabels[selected];
        exportHint.innerHTML = `Download <strong>${meta.file}</strong>`;
        if (!submitBtn.disabled) btnLabel.textContent = meta.action;
    }

    // ---- Theme ----
    function updateThemeUi(theme) {
        const isDark = theme === 'dark';
        themeIcon.textContent = isDark ? '☀' : '☾';
        themeLabel.textContent = isDark ? 'Light' : 'Dark';
    }
    function setTheme(theme) {
        root.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        updateThemeUi(theme);
    }

    // ---- File import ----
    async function importFile(file) {
        const name = file.name.toLowerCase();
        const allowed = ['.md', '.markdown', '.txt', '.docx'];
        if (!allowed.some((ext) => name.endsWith(ext))) {
            showToast('Supported: .md, .txt, .docx');
            return;
        }
        if (name.endsWith('.docx')) {
            setDocumentMode(file);
            showToast(`Attached document: ${file.name}`);
            return;
        }
        setDocumentMode(null);
        textarea.value = await file.text();
        fileBadge.textContent = file.name;
        fileBadge.classList.add('visible');
        updateCount();
        showToast(`Loaded: ${file.name}`);
    }

    // ---- Custom hidden colors management ----
    function addCustomHiddenColor(hex = '#FFFF00') {
        colorCounter += 1;
        const row = document.createElement('div');
        row.className = 'custom-color-row';
        row.innerHTML = `
            <input type="color"
                   name="hidden_color_custom-hidden-color-${colorCounter}"
                   value="${hex}" form="convert-form">
            <code>${hex.toUpperCase()}</code>
            <button type="button" class="remove-color-btn">✕</button>
        `;
        const picker = row.querySelector('input[type="color"]');
        const label  = row.querySelector('code');
        picker.addEventListener('input', () => {
            label.textContent = picker.value.toUpperCase();
        });
        row.querySelector('.remove-color-btn').addEventListener('click', () => row.remove());
        customColorsContainer.appendChild(row);
    }

    // ---- Event bindings ----
    themeToggle.addEventListener('click', () => {
        const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        setTheme(next);
    });
    updateThemeUi(root.getAttribute('data-theme') || 'dark');

    textarea.addEventListener('input', updateCount);
    updateCount();
    updateFormatUi();

    formatRadios.forEach((radio) => radio.addEventListener('change', updateFormatUi));

    // Form submit via fetch (keeps history.length === 1, so window.close() still works)
    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        if (!sourceFile.files.length && !textarea.value.trim()) {
            showToast('Enter Markdown or attach a .docx file');
            return;
        }

        submitBtn.disabled = true;
        btnLabel.textContent = 'Converting…';

        try {
            const formData = new FormData(form);
            const response = await fetch('/convert', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const text = await response.text();
                const errorMatch = text.match(/class="error"[^>]*>([^<]+)/);
                const errorMsg = errorMatch ? errorMatch[1] : `Server error: ${response.status}`;
                showToast(errorMsg);
                return;
            }

            const disposition = response.headers.get('Content-Disposition');
            let filename = 'document.docx';
            if (disposition) {
                const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (match && match[1]) filename = match[1].replace(/['"]/g, '');
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showToast(`Downloaded: ${filename}`);
        } catch (err) {
            showToast(`Network error: ${err.message}`);
        } finally {
            submitBtn.disabled = false;
            updateFormatUi();
        }
    });

    clearDocument.addEventListener('click', () => {
        setDocumentMode(null);
        showToast('Document removed');
    });

    textarea.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') form.requestSubmit();
    });

    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        if (fileInput.files[0]) importFile(fileInput.files[0]);
        fileInput.value = '';
    });

    ['dragenter', 'dragover'].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.add('is-dragover');
        });
    });
    ['dragleave', 'drop'].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.remove('is-dragover');
        });
    });
    dropZone.addEventListener('drop', (event) => {
        const file = event.dataTransfer.files[0];
        if (file) importFile(file);
    });

    // Custom color pickers (top-level body/table) auto-select their radio
    document.getElementById('custom-color-picker').addEventListener('input', () => {
        document.getElementById('color-custom').checked = true;
    });
    document.getElementById('table-custom-color-picker').addEventListener('input', () => {
        document.getElementById('table-color-custom').checked = true;
    });

    // ---- Hidden text settings ----
    if (stripHiddenCheckbox && hiddenTextSettings) {
        const syncHiddenSettingsVisibility = () => {
            hiddenTextSettings.hidden = !stripHiddenCheckbox.checked;
        };
        stripHiddenCheckbox.addEventListener('change', syncHiddenSettingsVisibility);
        syncHiddenSettingsVisibility();
    }

    if (minSizeSlider && minSizeInput) {
        minSizeSlider.addEventListener('input', () => { minSizeInput.value = minSizeSlider.value; });
        minSizeInput.addEventListener('input', () => { minSizeSlider.value = minSizeInput.value; });
    }

    if (addColorBtn) {
        addColorBtn.addEventListener('click', () => addCustomHiddenColor());
    }
})();
