// ─── DOM Elements ────────────────────────────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const toggleSidebarBtn = document.getElementById('toggle-sidebar');
const newConversationBtn = document.getElementById('new-conversation-btn');
const conversationList = document.getElementById('conversation-list');
const currentConversationIdInput = document.getElementById('current-conversation-id');
const processingOverlay = document.getElementById('processing-overlay');
const codeArtifactTemplate = document.getElementById('code-artifact-template');
const contextWindowTemplate = document.getElementById('context-window-template');
const confirmDialogTemplate = document.getElementById('confirm-dialog-template');
const fileInput = document.getElementById('file');
const fileNameSpan = document.getElementById('file-name');
const codeForm = document.getElementById('codeForm');
const toggleThemeBtn = document.getElementById('toggle-theme');
const inputTokensSpan = document.getElementById('input-tokens');
const outputTokensSpan = document.getElementById('output-tokens');
const totalTokensSpan = document.getElementById('total-tokens');

const workspacePathInput = document.getElementById('workspace-path-input');
const browseWorkspaceBtn = document.getElementById('browse-workspace-btn');
const clearWorkspaceBtn = document.getElementById('clear-workspace-btn');
const workspaceBadge = document.getElementById('workspace-badge');
const fileTree = document.getElementById('file-tree');
const fileBreadcrumb = document.getElementById('file-breadcrumb');
const fileTreeUp = document.getElementById('file-tree-up');

const browseModal = document.getElementById('browse-modal');
const modalPathInput = document.getElementById('modal-path-input');
const modalDrives = document.getElementById('modal-drives');
const modalFileList = document.getElementById('modal-file-list');
const modalUpBtn = document.getElementById('modal-up-btn');
const modalGoBtn = document.getElementById('modal-go-btn');
const modalSelectBtn = document.getElementById('modal-select-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

const imageLightbox = document.getElementById('image-lightbox');
const lightboxImg = document.getElementById('lightbox-img');
const lightboxCaption = document.getElementById('lightbox-caption');

const fileViewerModal = document.getElementById('file-viewer-modal');
const fileViewerTitle = document.getElementById('file-viewer-title');
const fileViewerCode = document.getElementById('file-viewer-code');
const fileViewerAddCtx = document.getElementById('file-viewer-add-ctx');
const fileViewerCopy = document.getElementById('file-viewer-copy');

let currentWorkspacePath = '';
let currentBrowsePath = '';
let currentFileTreePath = '';
let currentViewerFilePath = '';

// ─── Marked Configuration ────────────────────────────────────────────────────
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,
        gfm: true,
        highlight: function(code, lang) {
            if (window.Prism && lang && Prism.languages[lang]) {
                return Prism.highlight(code, Prism.languages[lang], lang);
            }
            return code;
        }
    });
}

// ─── Toast Notifications ─────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle', warning: 'fa-exclamation-triangle' };
    toast.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ─── Theme Management ────────────────────────────────────────────────────────
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.body.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const icon = toggleThemeBtn.querySelector('i');
    icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
}

// ─── Sidebar Management ─────────────────────────────────────────────────────
function initializeSidebar() {
    const newToggleBtn = document.getElementById('toggle-sidebar');
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed) {
        sidebar.classList.add('collapsed');
        newToggleBtn.querySelector('i').classList.replace('fa-chevron-left', 'fa-chevron-right');
    }

    newToggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        const isNowCollapsed = sidebar.classList.contains('collapsed');
        const icon = newToggleBtn.querySelector('i');
        if (isNowCollapsed) {
            icon.classList.replace('fa-chevron-left', 'fa-chevron-right');
        } else {
            icon.classList.replace('fa-chevron-right', 'fa-chevron-left');
        }
        localStorage.setItem('sidebarCollapsed', isNowCollapsed);
    });
}

// ─── Sidebar Tabs ────────────────────────────────────────────────────────────
function initializeSidebarTabs() {
    document.querySelectorAll('.sidebar-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            const tabId = `tab-${tab.dataset.tab}`;
            document.getElementById(tabId).classList.add('active');

            if (tab.dataset.tab === 'files' && currentWorkspacePath) {
                loadFileTree(currentFileTreePath || currentWorkspacePath);
            }
            if (tab.dataset.tab === 'context') {
                loadContextFiles();
            }
        });
    });
}

// ─── Workspace Management ────────────────────────────────────────────────────
function setWorkspace(path) {
    currentWorkspacePath = path;
    currentFileTreePath = path;
    workspacePathInput.value = path;
    localStorage.setItem('lastWorkspace', path);

    if (path) {
        clearWorkspaceBtn.style.display = '';
        const folderName = path.split(/[/\\]/).filter(Boolean).pop();
        workspaceBadge.textContent = `📁 ${folderName}`;
        workspaceBadge.title = path;
        workspaceBadge.style.display = '';
        loadFileTree(path);
    } else {
        clearWorkspaceBtn.style.display = 'none';
        workspaceBadge.style.display = 'none';
        fileTree.innerHTML = '<div class="file-tree-empty"><i class="fas fa-folder-open"></i><p>Select a workspace to browse files</p></div>';
    }

    const convId = currentConversationIdInput.value;
    if (convId && path) {
        fetch('/set-workspace', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ conversation_id: convId, workspace_path: path })
        });
    }
}

function initializeWorkspace() {
    const lastWorkspace = localStorage.getItem('lastWorkspace');
    if (lastWorkspace) {
        setWorkspace(lastWorkspace);
    }

    browseWorkspaceBtn.addEventListener('click', () => openBrowseModal());
    clearWorkspaceBtn.addEventListener('click', () => setWorkspace(''));
}

// ─── Browse Modal (Folder Picker) ────────────────────────────────────────────
async function openBrowseModal(startPath = '') {
    browseModal.style.display = 'flex';

    if (!startPath) {
        startPath = currentWorkspacePath || '';
    }

    if (!startPath) {
        try {
            const resp = await fetch('/drives');
            const data = await resp.json();
            modalDrives.style.display = 'flex';
            modalDrives.innerHTML = '';
            data.drives.forEach(drive => {
                const btn = document.createElement('button');
                btn.className = 'drive-btn';
                btn.innerHTML = `<i class="fas fa-hdd"></i> <span>${drive.label}</span>`;
                if (drive.free_gb !== undefined) {
                    btn.innerHTML += `<small>${drive.free_gb}GB free</small>`;
                }
                btn.addEventListener('click', () => {
                    modalDrives.style.display = 'none';
                    browseModalPath(drive.path);
                });
                modalDrives.appendChild(btn);
            });
            modalFileList.innerHTML = '<div class="browse-empty">Select a drive to browse</div>';
        } catch (e) {
            console.error('Failed to load drives:', e);
        }
    } else {
        modalDrives.style.display = 'none';
        browseModalPath(startPath);
    }
}

async function browseModalPath(dirPath) {
    try {
        const resp = await fetch(`/browse?path=${encodeURIComponent(dirPath)}`);
        const data = await resp.json();
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }

        currentBrowsePath = data.path;
        modalPathInput.value = data.path;
        modalFileList.innerHTML = '';

        if (data.parent) {
            const parentItem = document.createElement('div');
            parentItem.className = 'browse-item browse-dir';
            parentItem.innerHTML = '<i class="fas fa-arrow-up"></i> <span>..</span>';
            parentItem.addEventListener('click', () => browseModalPath(data.parent));
            modalFileList.appendChild(parentItem);
        }

        data.items.forEach(item => {
            if (!item.is_dir) return;
            const el = document.createElement('div');
            el.className = 'browse-item browse-dir';
            el.innerHTML = `<i class="fas fa-folder"></i> <span>${item.name}</span>`;
            el.addEventListener('click', () => browseModalPath(item.path));
            modalFileList.appendChild(el);
        });

        if (modalFileList.children.length <= (data.parent ? 1 : 0)) {
            const empty = document.createElement('div');
            empty.className = 'browse-empty';
            empty.textContent = 'No subdirectories';
            modalFileList.appendChild(empty);
        }
    } catch (e) {
        showToast('Failed to browse directory', 'error');
    }
}

function initializeBrowseModal() {
    document.querySelectorAll('.modal-close-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal-overlay').style.display = 'none';
        });
    });

    modalCancelBtn.addEventListener('click', () => {
        browseModal.style.display = 'none';
    });

    modalSelectBtn.addEventListener('click', () => {
        if (currentBrowsePath) {
            setWorkspace(currentBrowsePath);
            browseModal.style.display = 'none';
            showToast(`Workspace set: ${currentBrowsePath.split(/[/\\]/).pop()}`, 'success');
        }
    });

    modalUpBtn.addEventListener('click', () => {
        if (currentBrowsePath) {
            const parts = currentBrowsePath.replace(/[/\\]$/, '').split(/[/\\]/);
            if (parts.length > 1) {
                parts.pop();
                browseModalPath(parts.join('\\') || parts.join('/'));
            }
        }
    });

    modalGoBtn.addEventListener('click', () => {
        const path = modalPathInput.value.trim();
        if (path) browseModalPath(path);
    });

    modalPathInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const path = modalPathInput.value.trim();
            if (path) browseModalPath(path);
        }
    });

    browseModal.addEventListener('click', (e) => {
        if (e.target === browseModal) browseModal.style.display = 'none';
    });
}

// ─── File Tree ───────────────────────────────────────────────────────────────
async function loadFileTree(dirPath) {
    if (!dirPath) return;
    currentFileTreePath = dirPath;

    try {
        const resp = await fetch(`/browse?path=${encodeURIComponent(dirPath)}`);
        const data = await resp.json();
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }

        const relativePath = currentWorkspacePath
            ? dirPath.replace(currentWorkspacePath, '').replace(/^[/\\]/, '') || '/'
            : dirPath;
        fileBreadcrumb.textContent = relativePath;
        fileBreadcrumb.title = dirPath;

        fileTree.innerHTML = '';

        data.items.forEach(item => {
            const el = document.createElement('div');
            el.className = `file-tree-item ${item.is_dir ? 'is-dir' : 'is-file'}`;

            let icon = 'fa-file';
            if (item.is_dir) icon = 'fa-folder';
            else if (item.is_image) icon = 'fa-file-image';
            else {
                const extIcons = {
                    '.py': 'fa-file-code', '.js': 'fa-file-code', '.ts': 'fa-file-code',
                    '.html': 'fa-file-code', '.css': 'fa-file-code', '.json': 'fa-file-code',
                    '.md': 'fa-file-lines', '.txt': 'fa-file-lines',
                    '.sql': 'fa-database', '.sh': 'fa-terminal', '.bat': 'fa-terminal'
                };
                icon = extIcons[item.ext] || 'fa-file';
            }

            const sizeStr = item.size !== undefined ? formatFileSize(item.size) : '';
            el.innerHTML = `
                <i class="fas ${icon}"></i>
                <span class="file-name">${item.name}</span>
                ${sizeStr ? `<span class="file-size">${sizeStr}</span>` : ''}
            `;

            if (item.is_dir) {
                el.addEventListener('click', () => loadFileTree(item.path));
            } else if (item.is_image) {
                el.addEventListener('click', () => openImageLightbox(item.path, item.name));
            } else if (!item.is_binary) {
                el.addEventListener('click', () => openFileViewer(item.path, item.name));
            }

            el.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                if (item.is_dir) {
                    showFileTreeContextMenu(e, [
                        { label: 'Add folder to context', icon: 'fa-folder-plus', action: () => addFolderToContext(item.path) }
                    ]);
                } else if (!item.is_binary) {
                    showFileTreeContextMenu(e, [
                        { label: 'Add to context', icon: 'fa-plus-circle', action: () => addFileToContext(item.path) }
                    ]);
                }
            });

            fileTree.appendChild(el);
        });

        if (data.items.length === 0) {
            fileTree.innerHTML = '<div class="file-tree-empty"><p>Empty directory</p></div>';
        }
    } catch (e) {
        console.error('Failed to load file tree:', e);
    }
}

function formatFileSize(bytes) {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function initializeFileTree() {
    fileTreeUp.addEventListener('click', () => {
        if (currentFileTreePath && currentFileTreePath !== currentWorkspacePath) {
            const parts = currentFileTreePath.replace(/[/\\]$/, '').split(/[/\\]/);
            parts.pop();
            const parent = parts.join('\\') || parts.join('/');
            if (parent && parent.length >= (currentWorkspacePath || '').length) {
                loadFileTree(parent);
            }
        }
    });
}

// ─── Image Lightbox ──────────────────────────────────────────────────────────
function openImageLightbox(imagePath, caption = '') {
    lightboxImg.src = `/workspace-image?path=${encodeURIComponent(imagePath)}`;
    lightboxCaption.textContent = caption || imagePath.split(/[/\\]/).pop();
    imageLightbox.style.display = 'flex';
}

function initializeLightbox() {
    imageLightbox.addEventListener('click', (e) => {
        if (e.target === imageLightbox || e.target.closest('.lightbox-close')) {
            imageLightbox.style.display = 'none';
        }
    });
}

// ─── File Viewer ─────────────────────────────────────────────────────────────
async function openFileViewer(filePath, fileName) {
    try {
        const resp = await fetch(`/read-file?path=${encodeURIComponent(filePath)}`);
        const data = await resp.json();
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }

        if (data.is_image) {
            openImageLightbox(filePath, fileName);
            return;
        }

        currentViewerFilePath = filePath;
        fileViewerTitle.textContent = fileName || data.name;
        fileViewerCode.textContent = data.content;
        fileViewerCode.className = `language-${data.language || 'plaintext'}`;

        if (window.Prism) {
            Prism.highlightElement(fileViewerCode);
        }

        fileViewerModal.style.display = 'flex';
    } catch (e) {
        showToast('Failed to read file', 'error');
    }
}

function initializeFileViewer() {
    fileViewerAddCtx.addEventListener('click', () => {
        if (currentViewerFilePath) {
            addFileToContext(currentViewerFilePath);
        }
    });

    fileViewerCopy.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(fileViewerCode.textContent);
            showToast('Copied to clipboard', 'success');
        } catch (e) {
            showToast('Copy failed', 'error');
        }
    });

    fileViewerModal.addEventListener('click', (e) => {
        if (e.target === fileViewerModal) fileViewerModal.style.display = 'none';
    });
}

// ─── File Tree Context Menu ───────────────────────────────────────────────────
function showFileTreeContextMenu(event, items) {
    document.querySelectorAll('.ftree-ctx-menu').forEach(m => m.remove());
    const menu = document.createElement('div');
    menu.className = 'ftree-ctx-menu';
    items.forEach(item => {
        const btn = document.createElement('button');
        btn.className = 'ftree-ctx-item';
        btn.innerHTML = `<i class="fas ${item.icon}"></i> ${item.label}`;
        btn.addEventListener('click', () => { menu.remove(); item.action(); });
        menu.appendChild(btn);
    });
    menu.style.left = `${event.clientX}px`;
    menu.style.top = `${event.clientY}px`;
    document.body.appendChild(menu);
    const cleanup = (e) => {
        if (!menu.contains(e.target)) { menu.remove(); document.removeEventListener('click', cleanup); }
    };
    setTimeout(() => document.addEventListener('click', cleanup), 0);
}

// ─── Context Management ──────────────────────────────────────────────────────
async function addFolderToContext(folderPath) {
    const convId = currentConversationIdInput.value;
    if (!convId) { showToast('Create a conversation first', 'warning'); return; }

    showToast('Adding folder files to context...', 'info', 5000);
    try {
        const resp = await fetch('/add-folder-context', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ conversation_id: convId, folder_path: folderPath })
        });
        const data = await resp.json();
        if (data.error) {
            showToast(data.error, 'error');
        } else {
            showToast(`${data.message} (${data.skipped_count} skipped)`, 'success', 4000);
            loadContextFiles();
        }
    } catch (e) {
        showToast('Failed to add folder', 'error');
    }
}

async function addFileToContext(filePath) {
    const convId = currentConversationIdInput.value;
    if (!convId) {
        showToast('Create a conversation first', 'warning');
        return;
    }

    try {
        const resp = await fetch('/add-file-context', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ conversation_id: convId, file_path: filePath })
        });
        const data = await resp.json();
        if (data.error) {
            showToast(data.error, 'error');
        } else {
            showToast(data.message, 'success');
            loadContextFiles();
        }
    } catch (e) {
        showToast('Failed to add context', 'error');
    }
}

async function removeFileFromContext(filePath) {
    const convId = currentConversationIdInput.value;
    if (!convId) return;

    try {
        const resp = await fetch('/remove-file-context', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ conversation_id: convId, file_path: filePath })
        });
        const data = await resp.json();
        if (data.error) {
            showToast(data.error, 'error');
        } else {
            showToast('Removed from context', 'info');
            loadContextFiles();
        }
    } catch (e) {
        showToast('Failed to remove context', 'error');
    }
}

async function loadContextFiles() {
    const convId = currentConversationIdInput.value;
    const container = document.getElementById('context-file-list');

    if (!convId) {
        container.innerHTML = '<div class="context-empty"><i class="fas fa-layer-group"></i><p>No active conversation</p></div>';
        return;
    }

    try {
        const resp = await fetch(`/load-conversation/${convId}`);
        const data = await resp.json();

        if (!data.contexts || data.contexts.length === 0) {
            container.innerHTML = '<div class="context-empty"><i class="fas fa-layer-group"></i><p>No files in context</p><small>Right-click files in the Files tab to add</small></div>';
            return;
        }

        container.innerHTML = '';
        data.contexts.forEach(ctx => {
            const name = ctx.file_path.split(/[/\\]/).pop();
            const el = document.createElement('div');
            el.className = 'context-file-item';
            el.innerHTML = `
                <div class="context-file-info">
                    <i class="fas fa-file-code"></i>
                    <span class="context-file-name" title="${ctx.file_path}">${name}</span>
                </div>
                <button class="icon-btn small remove-ctx-btn" title="Remove from context">
                    <i class="fas fa-times"></i>
                </button>
            `;
            el.querySelector('.context-file-info').addEventListener('click', () => {
                openFileViewer(ctx.file_path, name);
            });
            el.querySelector('.remove-ctx-btn').addEventListener('click', () => {
                removeFileFromContext(ctx.file_path);
            });
            container.appendChild(el);
        });
    } catch (e) {
        console.error('Failed to load context files:', e);
    }
}

// ─── Conversation Container ──────────────────────────────────────────────────
function getConversationContainer() {
    return document.getElementById('conversation-container');
}

// ─── Context Window (Code Preview Popup) ─────────────────────────────────────
function createContextWindow(content, language = 'text', title = 'Code Preview') {
    document.querySelectorAll('.context-window').forEach(w => w.remove());

    const contextWindow = contextWindowTemplate.content.cloneNode(true).querySelector('.context-window');
    contextWindow.querySelector('.window-title span').textContent = title;
    const contentArea = contextWindow.querySelector('.context-window-content');
    const copyBtn = contextWindow.querySelector('.context-copy-btn');
    const closeBtn = contextWindow.querySelector('.context-close-btn');
    const copyIndicator = contextWindow.querySelector('.copy-indicator');

    const pre = document.createElement('pre');
    const code = document.createElement('code');
    code.className = `language-${language}`;
    code.textContent = content;
    pre.appendChild(code);
    contentArea.appendChild(pre);
    if (window.Prism) Prism.highlightElement(code);

    copyBtn.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(content);
            copyIndicator.textContent = 'Copied!';
            setTimeout(() => { copyIndicator.textContent = ''; }, 2000);
        } catch (err) {
            copyIndicator.textContent = 'Copy failed';
        }
    });
    closeBtn.addEventListener('click', () => contextWindow.remove());
    document.body.appendChild(contextWindow);
}

// ─── Code Artifact Creation ──────────────────────────────────────────────────
function createCodeArtifact(content, language, filePath = null, isLatest = false) {
    const artifact = codeArtifactTemplate.content.cloneNode(true).querySelector('.code-artifact');
    const languageBadge = artifact.querySelector('.language-badge');
    const filePathSpan = artifact.querySelector('.file-path');
    const previewBtn = artifact.querySelector('.preview-btn');
    const copyBtn = artifact.querySelector('.copy-btn');
    const applyBtn = artifact.querySelector('.apply-btn');
    const codeElement = artifact.querySelector('code');

    const languageMap = {
        'python': 'python', 'javascript': 'javascript', 'typescript': 'typescript',
        'html': 'markup', 'css': 'css', 'json': 'json', 'yaml': 'yaml',
        'bash': 'bash', 'shell': 'bash', 'sql': 'sql', 'jsx': 'jsx',
        'tsx': 'tsx', 'markup': 'markup', 'go': 'go', 'rust': 'rust',
        'java': 'java', 'csharp': 'csharp', 'c': 'c', 'cpp': 'cpp'
    };

    const prismLang = languageMap[language.toLowerCase()] || 'markup';
    languageBadge.textContent = language;
    codeElement.className = `language-${prismLang}`;
    codeElement.textContent = content;
    if (window.Prism) Prism.highlightElement(codeElement);

    if (filePath) {
        filePathSpan.textContent = filePath;
        filePathSpan.title = filePath;
        applyBtn.style.display = '';
        applyBtn.addEventListener('click', () => applyCodeToFile(content, filePath));
    }

    if (isLatest) {
        setTimeout(() => createContextWindow(content, prismLang, filePath || 'Latest Code Output'), 100);
    }

    previewBtn.addEventListener('click', () => createContextWindow(content, prismLang, filePath || 'Code Preview'));

    copyBtn.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(content);
            copyBtn.innerHTML = '<i class="fas fa-check"></i>';
            showToast('Copied!', 'success', 1500);
            setTimeout(() => { copyBtn.innerHTML = '<i class="fas fa-copy"></i>'; }, 2000);
        } catch (err) {
            console.error('Copy failed:', err);
        }
    });

    return artifact;
}

// ─── Apply Code to File ─────────────────────────────────────────────────────
async function applyCodeToFile(content, filePath) {
    let fullPath = filePath;
    if (currentWorkspacePath && !filePath.match(/^[A-Za-z]:[/\\]/) && !filePath.startsWith('/')) {
        const sep = currentWorkspacePath.includes('\\') ? '\\' : '/';
        fullPath = currentWorkspacePath + sep + filePath;
    }

    showConfirmDialog(
        'Apply Code to File',
        `Write this code to:\n${fullPath}`,
        async () => {
            try {
                const resp = await fetch('/write-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        path: fullPath,
                        content: content,
                        workspace: currentWorkspacePath
                    })
                });
                const data = await resp.json();
                if (data.error) {
                    showToast(data.error, 'error');
                } else {
                    showToast(`Saved: ${filePath}`, 'success');
                    if (currentFileTreePath) loadFileTree(currentFileTreePath);
                }
            } catch (e) {
                showToast('Failed to write file', 'error');
            }
        }
    );
}

// ─── Message Formatting ─────────────────────────────────────────────────────
function formatMessageContent(content) {
    if (typeof marked !== 'undefined') {
        let formatted = content;
        const codeBlocks = [];
        formatted = formatted.replace(/```(\w+)?(?::([^\n]+))?\n([\s\S]*?)```/g, (match, lang, path, code) => {
            const placeholder = `%%CODEBLOCK_${codeBlocks.length}%%`;
            codeBlocks.push({ lang: lang || 'text', path: path || null, code: code.trim() });
            return placeholder;
        });

        formatted = marked.parse(formatted);

        codeBlocks.forEach((block, i) => {
            const prismLang = block.lang || 'text';
            let highlighted = block.code;
            if (window.Prism && Prism.languages[prismLang]) {
                highlighted = Prism.highlight(block.code, Prism.languages[prismLang], prismLang);
            }
            const pathLabel = block.path ? `<span class="code-path-label">${block.path}</span>` : '';
            const applyBtnHtml = block.path
                ? `<button class="inline-apply-btn" data-path="${block.path}" data-code-idx="${i}"><i class="fas fa-file-import"></i> Apply</button>`
                : '';
            const copyBtnHtml = `<button class="inline-copy-btn" data-code-idx="${i}"><i class="fas fa-copy"></i></button>`;
            const codeHtml = `<div class="inline-code-block">
                <div class="inline-code-header">
                    <span class="inline-code-lang">${block.lang}</span>
                    ${pathLabel}
                    <div class="inline-code-actions">${applyBtnHtml}${copyBtnHtml}</div>
                </div>
                <pre><code class="language-${prismLang}">${highlighted}</code></pre>
            </div>`;
            formatted = formatted.replace(`%%CODEBLOCK_${i}%%`, codeHtml);
        });

        // Detect workspace images in response
        if (currentWorkspacePath) {
            formatted = formatted.replace(
                /(?:!\[([^\]]*)\]\(([^)]+)\))/g,
                (match, alt, src) => {
                    if (src.match(/\.(png|jpg|jpeg|gif|webp|svg|bmp)$/i)) {
                        const imgSrc = `/workspace-image?path=${encodeURIComponent(src)}`;
                        return `<div class="chat-image-container"><img src="${imgSrc}" alt="${alt || src}" class="chat-image" onclick="openImageLightbox('${src}', '${alt || src}')"><span class="chat-image-caption">${alt || src.split(/[/\\]/).pop()}</span></div>`;
                    }
                    return match;
                }
            );
        }

        return formatted;
    }

    content = content.replace(/\n\n/g, '</p><p>');
    content = content.replace(/\n/g, '<br>');
    if (!content.startsWith('<p>')) content = `<p>${content}</p>`;
    return content;
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

// ─── Message Element Creation ────────────────────────────────────────────────
function createMessageElement(message) {
    const el = document.createElement('div');
    el.className = `message ${message.role}-message`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = message.role === 'user'
        ? '<i class="fas fa-user"></i>'
        : '<i class="fas fa-robot"></i>';

    const body = document.createElement('div');
    body.className = 'message-body';

    const contentEl = document.createElement('div');
    contentEl.className = 'message-content';
    contentEl.innerHTML = formatMessageContent(message.content);

    const metaEl = document.createElement('div');
    metaEl.className = 'message-meta';
    const ts = document.createElement('span');
    ts.className = 'message-timestamp';
    ts.textContent = message.formatted_time || formatTimestamp(message.timestamp);
    metaEl.appendChild(ts);

    body.appendChild(contentEl);
    body.appendChild(metaEl);
    el.appendChild(avatar);
    el.appendChild(body);

    // Wire up inline code block buttons after rendering
    setTimeout(() => {
        el.querySelectorAll('.inline-apply-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const codeEl = btn.closest('.inline-code-block').querySelector('code');
                const path = btn.dataset.path;
                applyCodeToFile(codeEl.textContent, path);
            });
        });
        el.querySelectorAll('.inline-copy-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const codeEl = btn.closest('.inline-code-block').querySelector('code');
                try {
                    await navigator.clipboard.writeText(codeEl.textContent);
                    btn.innerHTML = '<i class="fas fa-check"></i>';
                    setTimeout(() => { btn.innerHTML = '<i class="fas fa-copy"></i>'; }, 2000);
                } catch (e) { console.error('Copy failed:', e); }
            });
        });
    }, 0);

    return el;
}

// ─── Confirm Dialog ──────────────────────────────────────────────────────────
function showConfirmDialog(title, message, onConfirm) {
    const dialog = confirmDialogTemplate.content.cloneNode(true).querySelector('.dialog-overlay');
    dialog.querySelector('h3').textContent = title;
    dialog.querySelector('.dialog-content').textContent = message;
    dialog.querySelector('.confirm-btn').addEventListener('click', () => { onConfirm(); dialog.remove(); });
    [dialog.querySelector('.cancel-btn'), dialog.querySelector('.close-btn')].forEach(b => {
        b.addEventListener('click', () => dialog.remove());
    });
    document.body.appendChild(dialog);
}

// ─── Conversation Handlers ───────────────────────────────────────────────────
function initializeConversationHandlers() {
    conversationList.addEventListener('click', handleConversationClick);
}

async function handleConversationClick(event) {
    const item = event.target.closest('.conversation-item');
    if (!item) return;

    if (event.target.closest('.rename-btn')) {
        handleConversationRename(item);
    } else if (event.target.closest('.delete-btn')) {
        handleConversationDelete(item);
    } else {
        await loadConversation(item.dataset.convId);
        if (item.dataset.workspace) {
            setWorkspace(item.dataset.workspace);
        }
    }
}

function handleConversationRename(item) {
    const nameText = item.querySelector('.name-text');
    const nameEdit = item.querySelector('.name-edit');
    nameText.style.display = 'none';
    nameEdit.style.display = 'block';
    nameEdit.focus();
    nameEdit.select();

    const saveRename = async () => {
        const newName = nameEdit.value.trim();
        if (!newName) return;
        try {
            const resp = await fetch('/rename-conversation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ conversation_id: item.dataset.convId, name: newName })
            });
            if (resp.ok) {
                nameText.textContent = newName;
                nameText.style.display = 'block';
                nameEdit.style.display = 'none';
            }
        } catch (e) {
            nameEdit.value = nameText.textContent;
        }
    };

    nameEdit.addEventListener('blur', saveRename);
    nameEdit.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); saveRename(); }
    });
}

function handleConversationDelete(item) {
    showConfirmDialog(
        'Delete Conversation',
        'Are you sure you want to delete this conversation?',
        async () => {
            try {
                const resp = await fetch('/delete-conversation', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: new URLSearchParams({ conversation_id: item.dataset.convId })
                });
                if (resp.ok) {
                    item.remove();
                    if (currentConversationIdInput.value === item.dataset.convId) {
                        currentConversationIdInput.value = '';
                        showWelcomeScreen();
                    }
                }
            } catch (e) {
                console.error('Delete failed:', e);
            }
        }
    );
}

function detectLanguage(filePath) {
    const ext = '.' + filePath.split('.').pop().toLowerCase();
    const map = {
        '.py': 'python', '.js': 'javascript', '.html': 'html', '.css': 'css',
        '.json': 'json', '.md': 'markdown', '.sql': 'sql', '.yml': 'yaml',
        '.yaml': 'yaml', '.xml': 'xml', '.sh': 'bash', '.bash': 'bash',
        '.ts': 'typescript', '.jsx': 'jsx', '.tsx': 'tsx', '.go': 'go',
        '.rs': 'rust', '.java': 'java', '.cs': 'csharp', '.cpp': 'cpp', '.c': 'c'
    };
    return map[ext] || 'plaintext';
}

async function loadConversation(conversationId) {
    try {
        const resp = await fetch(`/load-conversation/${conversationId}`);
        const data = await resp.json();

        currentConversationIdInput.value = conversationId;
        const container = getConversationContainer();
        container.innerHTML = '';

        data.messages.forEach(message => {
            container.appendChild(createMessageElement(message));
        });

        if (data.tokens) {
            updateTokenCounters({
                total_input_tokens: data.tokens.total_input_tokens,
                total_output_tokens: data.tokens.total_output_tokens,
                total_tokens: data.tokens.total_input_tokens + data.tokens.total_output_tokens
            });
        }

        if (data.workspace_path) {
            setWorkspace(data.workspace_path);
        }

        container.scrollTop = container.scrollHeight;
        loadContextFiles();
    } catch (e) {
        console.error('Error loading conversation:', e);
        showToast('Failed to load conversation', 'error');
    }
}

// ─── Form Submission ─────────────────────────────────────────────────────────
async function handleFormSubmit(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const prompt = formData.get('prompt');
    if (!prompt.trim()) return;

    processingOverlay.classList.add('active');

    try {
        if (!currentConversationIdInput.value) {
            const conversationName = generateConversationName(prompt);
            const body = new URLSearchParams({ name: conversationName });
            if (currentWorkspacePath) {
                body.append('workspace_path', currentWorkspacePath);
            }
            const resp = await fetch('/new-conversation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body
            });
            if (!resp.ok) throw new Error('Failed to create new conversation');
            const data = await resp.json();
            currentConversationIdInput.value = data.conversation_id;
            const newItem = createConversationListItem(data);
            conversationList.insertBefore(newItem, conversationList.firstChild);

            const container = getConversationContainer();
            const welcome = container.querySelector('.welcome-screen');
            if (welcome) welcome.remove();
        }

        formData.set('conversation_id', currentConversationIdInput.value);

        const resp = await fetch('/process', { method: 'POST', body: formData });
        if (!resp.ok) throw new Error('Failed to process request');

        const data = await resp.json();
        const container = getConversationContainer();

        container.appendChild(createMessageElement({
            role: 'user', content: prompt,
            formatted_time: new Date().toLocaleTimeString()
        }));

        container.appendChild(createMessageElement({
            role: 'assistant', content: data.response,
            formatted_time: data.timestamp
        }));

        if (data.artifacts && data.artifacts.length > 0) {
            data.artifacts.forEach((artifact, index) => {
                container.appendChild(createCodeArtifact(
                    artifact.content, artifact.language,
                    artifact.file_path,
                    index === data.artifacts.length - 1
                ));
            });
        }

        updateTokenCounters(data.total_tokens);
        event.target.reset();
        fileNameSpan.textContent = 'Attach File';
        container.scrollTop = container.scrollHeight;
    } catch (e) {
        console.error('Error:', e);
        getConversationContainer().appendChild(createMessageElement({
            role: 'error', content: e.message,
            formatted_time: new Date().toLocaleTimeString()
        }));
    } finally {
        processingOverlay.classList.remove('active');
    }
}

// ─── Token Counters ──────────────────────────────────────────────────────────
function updateTokenCounters(tokens) {
    if (tokens) {
        inputTokensSpan.textContent = tokens.total_input_tokens || 0;
        outputTokensSpan.textContent = tokens.total_output_tokens || 0;
        totalTokensSpan.textContent = tokens.total_tokens || 0;
    }
}

function generateConversationName(prompt) {
    let name = prompt.split(/[.!?]/)[0].trim();
    if (name.length > 40) name = name.substring(0, 37) + '...';
    return name || 'New Chat';
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function createConversationListItem(data) {
    const item = document.createElement('div');
    item.className = 'conversation-item';
    item.dataset.convId = data.conversation_id;
    item.dataset.workspace = data.workspace_path || '';
    const wsName = data.workspace_path ? data.workspace_path.split(/[/\\]/).filter(Boolean).pop() : '';
    item.innerHTML = `
        <div class="conversation-info">
            <div class="conversation-name">
                <span class="name-text">${data.name}</span>
                <input type="text" class="name-edit" value="${data.name}" style="display: none;">
            </div>
            <small class="conversation-timestamp">${data.timestamp || ''}</small>
            ${wsName ? `<small class="conversation-workspace"><i class="fas fa-folder"></i> ${wsName}</small>` : ''}
        </div>
        <div class="conversation-actions">
            <button class="icon-btn small rename-btn" title="Rename"><i class="fas fa-pencil"></i></button>
            <button class="icon-btn small delete-btn" title="Delete"><i class="fas fa-trash"></i></button>
        </div>
    `;
    return item;
}

function showWelcomeScreen() {
    const container = getConversationContainer();
    container.innerHTML = `
        <div class="welcome-screen">
            <i class="fas fa-terminal welcome-icon"></i>
            <h2>CodeChat Agent</h2>
            <p>Select a workspace and start coding with your AI agent.</p>
            <div class="welcome-actions">
                <button onclick="document.getElementById('browse-workspace-btn').click()" class="primary-btn">
                    <i class="fas fa-folder-open"></i> Select Workspace
                </button>
                <button onclick="document.getElementById('new-conversation-btn').click()" class="secondary-btn">
                    <i class="fas fa-plus"></i> New Chat
                </button>
            </div>
        </div>
    `;
}

// ─── Event Listeners ─────────────────────────────────────────────────────────
function initializeEventListeners() {
    newConversationBtn.addEventListener('click', async () => {
        try {
            const body = new URLSearchParams({ name: 'New Chat' });
            if (currentWorkspacePath) body.append('workspace_path', currentWorkspacePath);
            const resp = await fetch('/new-conversation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body
            });
            const data = await resp.json();
            currentConversationIdInput.value = data.conversation_id;
            getConversationContainer().innerHTML = '';
            codeForm.reset();
            fileNameSpan.textContent = 'Attach File';
            updateTokenCounters({ total_input_tokens: 0, total_output_tokens: 0, total_tokens: 0 });
            conversationList.insertBefore(createConversationListItem(data), conversationList.firstChild);
        } catch (e) {
            console.error('Error creating conversation:', e);
        }
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            fileNameSpan.textContent = file.name;
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            if (file.size > 1024 * 1024) {
                fileNameSpan.title = `${sizeMB}MB - will be compressed`;
            }
        } else {
            fileNameSpan.textContent = 'Attach File';
        }
    });

    codeForm.addEventListener('submit', handleFormSubmit);
    toggleThemeBtn.addEventListener('click', toggleTheme);

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            document.getElementById('toggle-sidebar').click();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            newConversationBtn.click();
        }
        if (e.key === 'Escape') {
            document.querySelectorAll('.context-window').forEach(w => w.remove());
            imageLightbox.style.display = 'none';
            fileViewerModal.style.display = 'none';
            browseModal.style.display = 'none';
        }
    });

    const dropZone = document.querySelector('.prompt-area');
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev => {
        dropZone.addEventListener(ev, (e) => { e.preventDefault(); e.stopPropagation(); }, false);
    });
    ['dragenter', 'dragover'].forEach(ev => {
        dropZone.addEventListener(ev, () => dropZone.classList.add('drag-active'));
    });
    ['dragleave', 'drop'].forEach(ev => {
        dropZone.addEventListener(ev, () => dropZone.classList.remove('drag-active'));
    });
    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length) {
            fileInput.files = files;
            fileInput.dispatchEvent(new Event('change'));
        }
    });
}

// ─── Initialize Application ──────────────────────────────────────────────────
function initializeApplication() {
    initializeTheme();
    initializeSidebar();
    initializeSidebarTabs();
    initializeWorkspace();
    initializeBrowseModal();
    initializeFileTree();
    initializeLightbox();
    initializeFileViewer();
    initializeConversationHandlers();
    initializeEventListeners();
    showWelcomeScreen();
}

document.addEventListener('DOMContentLoaded', initializeApplication);
