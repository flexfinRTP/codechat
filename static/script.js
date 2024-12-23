// DOM Elements
const sidebar = document.getElementById('sidebar');
const toggleSidebarBtn = document.getElementById('toggle-sidebar');
const newConversationBtn = document.getElementById('new-conversation-btn');
const conversationList = document.getElementById('conversation-list');
const createContextWindowBtn = document.getElementById('create-context-window');
const currentConversationIdInput = document.getElementById('current-conversation-id');
const processingOverlay = document.getElementById('processing-overlay');
const contextWindowTemplate = document.getElementById('context-window-template');
const codeArtifactTemplate = document.getElementById('code-artifact-template');
const confirmDialogTemplate = document.getElementById('confirm-dialog-template');
const fileInput = document.getElementById('file');
const fileNameSpan = document.getElementById('file-name');
const codeForm = document.getElementById('codeForm');
const toggleThemeBtn = document.getElementById('toggle-theme');

// Token counters
const inputTokensSpan = document.getElementById('input-tokens');
const outputTokensSpan = document.getElementById('output-tokens');
const totalTokensSpan = document.getElementById('total-tokens');

// Theme Management
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
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

// Syntax Highlighting
function initializePrismJS() {
    const prismCSS = document.createElement('link');
    prismCSS.rel = 'stylesheet';
    prismCSS.href = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css';
    document.head.appendChild(prismCSS);

    const prismJS = document.createElement('script');
    prismJS.src = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js';
    prismJS.onload = loadPrismLanguages;
    document.head.appendChild(prismJS);
}

function loadPrismLanguages() {
    const languages = [
        'python',
        'javascript',
        'typescript',
        'css',
        'markup',
        'json',
        'yaml',
        'bash',
        'sql'
    ];

    languages.forEach(lang => {
        const script = document.createElement('script');
        script.src = `https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-${lang}.min.js`;
        document.head.appendChild(script);
    });
}

function initializeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleSidebarBtn = document.getElementById('toggle-sidebar');
    const mainContent = document.querySelector('.main-content');
    
    // Remove any existing click handlers
    toggleSidebarBtn.replaceWith(toggleSidebarBtn.cloneNode(true));
    const newToggleBtn = document.getElementById('toggle-sidebar');
    
    // Get the initial state from localStorage
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed) {
        sidebar.classList.add('collapsed');
        mainContent.style.marginLeft = '60px';
        newToggleBtn.querySelector('i').classList.replace('fa-chevron-left', 'fa-chevron-right');
    }
    
    newToggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        const isNowCollapsed = sidebar.classList.contains('collapsed');
        
        // Update main content margin
        mainContent.style.marginLeft = isNowCollapsed ? '60px' : '300px';
        
        // Update button icon
        const icon = newToggleBtn.querySelector('i');
        if (isNowCollapsed) {
            icon.classList.replace('fa-chevron-left', 'fa-chevron-right');
        } else {
            icon.classList.replace('fa-chevron-right', 'fa-chevron-left');
        }
        
        // Save state
        localStorage.setItem('sidebarCollapsed', isNowCollapsed);
    });
}
// Conversation Container Management
function getConversationContainer() {
    let container = document.getElementById('conversation-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'conversation-container';
        container.style.height = 'calc(100vh - 300px)'; // Set fixed height
        container.style.overflowY = 'auto'; // Enable vertical scrolling
        document.querySelector('.main-content').appendChild(container);
    }
    return container;
}


// Context Window Management
function createContextWindow(content, language = 'text', title = 'Code Output') {
    const existingWindows = document.querySelectorAll('.context-window');
    existingWindows.forEach(window => window.remove());

    const contextWindow = contextWindowTemplate.content.cloneNode(true).querySelector('.context-window');
    const windowTitle = contextWindow.querySelector('.window-title span');
    const contentArea = contextWindow.querySelector('.context-window-content');
    const copyBtn = contextWindow.querySelector('.context-copy-btn');
    const closeBtn = contextWindow.querySelector('.context-close-btn');
    const copyIndicator = contextWindow.querySelector('.copy-indicator');

    windowTitle.textContent = title;

    // Create code block with proper formatting
    const preElement = document.createElement('pre');
    const codeElement = document.createElement('code');
    codeElement.className = `language-${language}`;
    codeElement.textContent = content;
    preElement.appendChild(codeElement);
    contentArea.appendChild(preElement);

    if (window.Prism) {
        Prism.highlightElement(codeElement);
    }

    copyBtn.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(content);
            copyIndicator.textContent = 'Copied!';
            setTimeout(() => {
                copyIndicator.textContent = '';
            }, 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
            copyIndicator.textContent = 'Copy failed';
        }
    });

    closeBtn.addEventListener('click', () => {
        contextWindow.remove();
    });

    document.body.appendChild(contextWindow);
}

// Code Artifact Management
function createCodeArtifact(content, language, isLatest = false) {
    const artifact = codeArtifactTemplate.content.cloneNode(true).querySelector('.code-artifact');
    const languageBadge = artifact.querySelector('.language-badge');
    const previewBtn = artifact.querySelector('.preview-btn');
    const copyBtn = artifact.querySelector('.copy-btn');
    const codeElement = artifact.querySelector('code');

    // Map common language names to Prism-supported languages
    const languageMap = {
        'python': 'python',
        'javascript': 'javascript',
        'typescript': 'typescript',
        'html': 'markup',
        'css': 'css',
        'json': 'json',
        'yaml': 'yaml',
        'bash': 'bash',
        'shell': 'bash',
        'sql': 'sql',
        'jsx': 'jsx',
        'tsx': 'tsx',
        'markup': 'markup'
    };

    const prismLanguage = languageMap[language.toLowerCase()] || 'markup';
    
    languageBadge.textContent = language;
    codeElement.className = `language-${prismLanguage}`;
    codeElement.textContent = content;

    if (window.Prism) {
        Prism.highlightElement(codeElement);
    }

    // Show code in context window automatically if it's the latest
    if (isLatest) {
        setTimeout(() => {
            createContextWindow(content, prismLanguage, 'Latest Code Output');
        }, 100);
    }

    previewBtn.addEventListener('click', () => {
        createContextWindow(content, prismLanguage);
    });

    copyBtn.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(content);
            copyBtn.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => {
                copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            }, 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    });

    return artifact;
}

function formatMessageContent(content) {
    // Replace newlines with proper HTML breaks
    content = content.replace(/\n\n/g, '</p><p>');
    content = content.replace(/\n/g, '<br>');
    
    // Wrap in paragraphs if not already
    if (!content.startsWith('<p>')) {
        content = `<p>${content}</p>`;
    }
    
    return content;
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Enhanced Message Creation
function createMessageElement(message) {
    const messageElement = document.createElement('div');
    messageElement.className = `message ${message.role}-message`;
    
    const contentElement = document.createElement('div');
    contentElement.className = 'message-content';
    contentElement.innerHTML = formatMessageContent(message.content);
    
    const metaElement = document.createElement('div');
    metaElement.className = 'message-meta';
    
    const timestampSpan = document.createElement('span');
    timestampSpan.className = 'message-timestamp';
    timestampSpan.textContent = message.formatted_time || formatTimestamp(message.timestamp);
    
    metaElement.appendChild(timestampSpan);
    
    // Add artifact buttons if message has associated artifacts
    if (message.artifacts && message.artifacts.length > 0) {
        const artifactButtons = document.createElement('div');
        artifactButtons.className = 'message-artifacts';
        
        message.artifacts.forEach((artifact, index) => {
            const button = document.createElement('button');
            button.className = 'artifact-button';
            button.innerHTML = `<i class="fas fa-code"></i> ${artifact.language}`;
            button.addEventListener('click', () => {
                createContextWindow(artifact.content, artifact.language, `Code Output ${index + 1}`);
            });
            artifactButtons.appendChild(button);
        });
        
        metaElement.appendChild(artifactButtons);
    }
    
    messageElement.appendChild(contentElement);
    messageElement.appendChild(metaElement);
    
    return messageElement;
}

// Confirmation Dialog
function showConfirmDialog(title, message, onConfirm) {
    const dialog = confirmDialogTemplate.content.cloneNode(true).querySelector('.dialog-overlay');
    const titleElement = dialog.querySelector('h3');
    const contentElement = dialog.querySelector('.dialog-content');
    const confirmBtn = dialog.querySelector('.confirm-btn');
    const cancelBtn = dialog.querySelector('.cancel-btn');
    const closeBtn = dialog.querySelector('.close-btn');

    titleElement.textContent = title;
    contentElement.textContent = message;

    confirmBtn.addEventListener('click', () => {
        onConfirm();
        dialog.remove();
    });

    [cancelBtn, closeBtn].forEach(btn => {
        btn.addEventListener('click', () => {
            dialog.remove();
        });
    });

    document.body.appendChild(dialog);
}

// Conversation Management
function initializeConversationHandlers() {
    conversationList.addEventListener('click', handleConversationClick);
    conversationList.addEventListener('dblclick', handleConversationRename);
}

async function handleConversationClick(event) {
    const conversationItem = event.target.closest('.conversation-item');
    if (!conversationItem) return;

    const renameBtn = event.target.closest('.rename-btn');
    const deleteBtn = event.target.closest('.delete-btn');

    if (renameBtn) {
        handleConversationRename(conversationItem);
    } else if (deleteBtn) {
        handleConversationDelete(conversationItem);
    } else {
        await loadConversation(conversationItem.dataset.convId);
    }
}

function handleConversationRename(conversationItem) {
    const nameText = conversationItem.querySelector('.name-text');
    const nameEdit = conversationItem.querySelector('.name-edit');
    
    nameText.style.display = 'none';
    nameEdit.style.display = 'block';
    nameEdit.focus();
    nameEdit.select();

    const saveRename = async () => {
        const newName = nameEdit.value.trim();
        if (!newName) return;

        try {
            const response = await fetch('/rename-conversation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    conversation_id: conversationItem.dataset.convId,
                    name: newName
                })
            });

            if (response.ok) {
                nameText.textContent = newName;
                nameText.style.display = 'block';
                nameEdit.style.display = 'none';
            } else {
                throw new Error('Failed to rename conversation');
            }
        } catch (error) {
            console.error('Error renaming conversation:', error);
            // Revert changes
            nameEdit.value = nameText.textContent;
        }
    };

    nameEdit.addEventListener('blur', saveRename);
    nameEdit.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveRename();
        }
    });
}

function handleConversationDelete(conversationItem) {
    showConfirmDialog(
        'Delete Conversation',
        'Are you sure you want to delete this conversation? This action cannot be undone.',
        async () => {
            try {
                const response = await fetch('/delete-conversation', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams({
                        conversation_id: conversationItem.dataset.convId
                    })
                });

                if (response.ok) {
                    conversationItem.remove();
                    if (currentConversationIdInput.value === conversationItem.dataset.convId) {
                        newConversationBtn.click();
                    }
                } else {
                    throw new Error('Failed to delete conversation');
                }
            } catch (error) {
                console.error('Error deleting conversation:', error);
            }
        }
    );
}

function detectLanguage(filePath) {
    const extensions = {
        '.py': 'python',
        '.js': 'javascript',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.md': 'markdown',
        '.sql': 'sql',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.xml': 'xml',
        '.sh': 'bash',
        '.bash': 'bash',
        '.ts': 'typescript',
        '.jsx': 'jsx',
        '.tsx': 'tsx'
    };
    
    const ext = '.' + filePath.split('.').pop().toLowerCase();
    return extensions[ext] || 'plaintext';
}

async function loadConversation(conversationId) {
    try {
        const response = await fetch(`/load-conversation/${conversationId}`);
        const data = await response.json();
        
        currentConversationIdInput.value = conversationId;
        
        const container = getConversationContainer();
        container.innerHTML = '';
        
        // Process messages and their associated artifacts
        data.messages.forEach(message => {
            // Create message element
            const messageElement = createMessageElement(message);
            container.appendChild(messageElement);
            
            // Find artifacts associated with this message's timestamp
            const messageArtifacts = data.artifacts.filter(artifact => 
                new Date(artifact.timestamp).getTime() >= new Date(message.timestamp).getTime() &&
                new Date(artifact.timestamp).getTime() <= new Date(message.timestamp).getTime() + 1000
            );
            
            // Create artifact elements
            messageArtifacts.forEach(artifact => {
                const artifactElement = createCodeArtifact(
                    artifact.content,
                    artifact.language,
                    false // Not latest since we're loading history
                );
                container.appendChild(artifactElement);
            });
        });

        // Update token counters
        if (data.tokens) {
            updateTokenCounters({
                total_input_tokens: data.tokens.total_input_tokens,
                total_output_tokens: data.tokens.total_output_tokens,
                total_tokens: data.tokens.total_input_tokens + data.tokens.total_output_tokens
            });
        }

        // Process any project contexts
        if (data.contexts && data.contexts.length > 0) {
            data.contexts.forEach(context => {
                const contextButton = document.createElement('button');
                contextButton.className = 'context-file-button';
                contextButton.innerHTML = `
                    <i class="fas fa-file-code"></i>
                    ${context.file_path}
                `;
                contextButton.addEventListener('click', () => {
                    createContextWindow(
                        context.file_content,
                        context.file_type || detectLanguage(context.file_path),
                        context.file_path
                    );
                });
                container.insertBefore(contextButton, container.firstChild);
            });
        }

        container.scrollTop = container.scrollHeight;
    } catch (error) {
        console.error('Error loading conversation:', error);
        showErrorMessage('Failed to load conversation');
    }
}

// Form Submission
async function handleFormSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const prompt = formData.get('prompt');
    
    if (!prompt.trim()) {
        return; // Don't submit empty prompts
    }
    
    processingOverlay.classList.add('active');
    
    try {
        // Handle new conversation creation
        if (!currentConversationIdInput.value) {
            const conversationName = generateConversationName(prompt);
            const response = await fetch('/new-conversation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    name: conversationName
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to create new conversation');
            }
            
            const data = await response.json();
            currentConversationIdInput.value = data.conversation_id;
            
            // Add new conversation to list
            const newConversationItem = createConversationListItem(data);
            conversationList.insertBefore(newConversationItem, conversationList.firstChild);
        }
        
        // Add conversation ID to form data
        formData.set('conversation_id', currentConversationIdInput.value);
        
        // Process the prompt
        const response = await fetch('/process', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Failed to process request');
        }

        const data = await response.json();
        const container = getConversationContainer();
        
        // Add user message
        const userMessage = createMessageElement({
            role: 'user',
            content: prompt,
            formatted_time: new Date().toLocaleTimeString()
        });
        container.appendChild(userMessage);

        // Add assistant message with artifacts
        const assistantMessage = createMessageElement({
            role: 'assistant',
            content: data.response,
            formatted_time: data.timestamp
        }, data.artifacts);
        container.appendChild(assistantMessage);

        // Process code artifacts
        if (data.artifacts && data.artifacts.length > 0) {
            data.artifacts.forEach((artifact, index) => {
                const artifactElement = createCodeArtifact(
                    artifact.content,
                    artifact.language,
                    index === data.artifacts.length - 1 // Show latest artifact
                );
                container.appendChild(artifactElement);
            });
        }

        // Update token counters
        updateTokenCounters(data.total_tokens);

        // Clear inputs
        event.target.reset();
        fileNameSpan.textContent = 'Attach File';

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;

    } catch (error) {
        console.error('Error:', error);
        const errorMessage = createMessageElement({
            role: 'error',
            content: error.message,
            formatted_time: new Date().toLocaleTimeString()
        });
        getConversationContainer().appendChild(errorMessage);
    } finally {
        processingOverlay.classList.remove('active');
    }
}

// Token Counter Updates
function updateTokenCounters(tokens) {
    if (tokens) {
        inputTokensSpan.textContent = tokens.total_input_tokens;
        outputTokensSpan.textContent = tokens.total_output_tokens;
        totalTokensSpan.textContent = tokens.total_tokens;
    }
}

function generateConversationName(prompt) {
    // Take first sentence or first 40 characters
    let name = prompt.split(/[.!?]/)[0].trim();
    if (name.length > 40) {
        name = name.substring(0, 37) + '...';
    }
    return name || 'New Chat';
}

// Event Listeners
function initializeEventListeners() {
    toggleSidebarBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        const icon = toggleSidebarBtn.querySelector('i');
        icon.classList.toggle('fa-chevron-left');
        icon.classList.toggle('fa-chevron-right');
    });

    newConversationBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/new-conversation', {
                method: 'POST',
                body: new FormData()
            });
            const data = await response.json();
            
            // Update current conversation ID
            currentConversationIdInput.value = data.conversation_id;
            
            // Clear conversation container
            const container = getConversationContainer();
            container.innerHTML = '';
            
            // Clear form inputs
            codeForm.reset();
            fileNameSpan.textContent = 'Attach File';
            
            // Reset token counters
            updateTokenCounters({
                total_input_tokens: 0,
                total_output_tokens: 0,
                total_tokens: 0
            });

            // Add new conversation to list
            const newConversationItem = createConversationListItem(data);
            conversationList.insertBefore(newConversationItem, conversationList.firstChild);
        } catch (error) {
            console.error('Error creating new conversation:', error);
        }
    });

    createContextWindowBtn.addEventListener('click', () => {
        const container = getConversationContainer();
        const currentContent = container.textContent.trim();
        if (currentContent) {
            createContextWindow(currentContent, 'text', 'Conversation Context');
        }
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            fileNameSpan.textContent = file.name;
            // Add file type indicator
            const fileType = file.name.split('.').pop().toLowerCase();
            fileNameSpan.className = `file-name file-type-${fileType}`;
        } else {
            fileNameSpan.textContent = 'Attach File';
            fileNameSpan.className = 'file-name';
        }
    });

    codeForm.addEventListener('submit', handleFormSubmit);
    
    toggleThemeBtn.addEventListener('click', toggleTheme);

    // Handle keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + / to toggle sidebar
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            toggleSidebarBtn.click();
        }
        
        // Ctrl/Cmd + N for new conversation
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            newConversationBtn.click();
        }
        
        // Escape to close context window
        if (e.key === 'Escape') {
            const contextWindow = document.querySelector('.context-window');
            if (contextWindow) {
                contextWindow.remove();
            }
        }
    });

    // Handle window resize for responsive layout
    window.addEventListener('resize', () => {
        if (window.innerWidth < 768) {
            sidebar.classList.add('collapsed');
        }
    });

    // Handle drag and drop file upload
    const dropZone = document.querySelector('.prompt-area');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('drag-active');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('drag-active');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length) {
            fileInput.files = files;
            const event = new Event('change');
            fileInput.dispatchEvent(event);
        }
    });
}

// Add delete confirmation dialog
function showDeleteConfirmation(conversationItem) {
    const dialog = document.createElement('div');
    dialog.className = 'delete-confirmation';
    dialog.innerHTML = `
        <div class="delete-confirmation-content">
            <p>Delete this conversation?</p>
            <div class="delete-confirmation-actions">
                <button class="cancel-btn">Cancel</button>
                <button class="confirm-btn">Delete</button>
            </div>
        </div>
    `;
    
    conversationItem.appendChild(dialog);
    
    const cancelBtn = dialog.querySelector('.cancel-btn');
    const confirmBtn = dialog.querySelector('.confirm-btn');
    
    cancelBtn.addEventListener('click', () => {
        dialog.remove();
    });
    
    confirmBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/delete-conversation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    conversation_id: conversationItem.dataset.convId
                })
            });

            if (response.ok) {
                conversationItem.remove();
                if (currentConversationIdInput.value === conversationItem.dataset.convId) {
                    newConversationBtn.click();
                }
            } else {
                throw new Error('Failed to delete conversation');
            }
        } catch (error) {
            console.error('Error deleting conversation:', error);
        }
    });
}

// Helper Functions
function createConversationListItem(data) {
    const item = document.createElement('div');
    item.className = 'conversation-item';
    item.dataset.convId = data.conversation_id;
    
    item.innerHTML = `
        <div class="conversation-info">
            <div class="conversation-name">
                <span class="name-text">${data.name}</span>
                <input type="text" class="name-edit" value="${data.name}" style="display: none;">
            </div>
            <small class="conversation-timestamp">${data.timestamp}</small>
        </div>
        <div class="conversation-actions">
            <button class="icon-btn small rename-btn" title="Rename">
                <i class="fas fa-pencil"></i>
            </button>
            <button class="icon-btn small delete-btn" title="Delete">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    
    // Add delete confirmation handling
    const deleteBtn = item.querySelector('.delete-btn');
    deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        showDeleteConfirmation(item);
    });
    
    return item;
}

function showWelcomeScreen() {
    const container = getConversationContainer();
    container.innerHTML = `
        <div class="welcome-screen">
            <i class="fas fa-code-branch welcome-icon"></i>
            <h2>Welcome to CodeChat</h2>
            <p>Start a new conversation to begin coding with AI assistance.</p>
            <button onclick="newConversationBtn.click()" class="primary-btn">
                <i class="fas fa-plus"></i>
                New Conversation
            </button>
        </div>
    `;
}

// Initialize Application
function initializeApplication() {
    initializeTheme();
    initializePrismJS();
    initializeConversationHandlers();
    initializeEventListeners();
    initializeSidebar();
    
    // Show welcome message instead of creating new conversation
    showWelcomeScreen();
}

// Start the application
document.addEventListener('DOMContentLoaded', initializeApplication);
