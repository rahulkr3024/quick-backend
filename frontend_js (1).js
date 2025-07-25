// API Configuration
const API_BASE_URL = 'http://localhost:5000/api';
let sessionId = localStorage.getItem('quicky_session_id') || generateSessionId();
localStorage.setItem('quicky_session_id', sessionId);

// Utility Functions
function generateSessionId() {
    return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
}

function showError(message) {
    // Create error notification
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-notification';
    errorDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 10px 25px -5px rgba(239, 68, 68, 0.25);
        z-index: 1000;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
    errorDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
            <svg style="width: 20px; height: 20px;" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(errorDiv);
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

function showSuccess(message) {
    // Create success notification
    const successDiv = document.createElement('div');
    successDiv.className = 'success-notification';
    successDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.25);
        z-index: 1000;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
    successDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
            <svg style="width: 20px; height: 20px;" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <polyline points="20,6 9,17 4,12"></polyline>
            </svg>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(successDiv);
    setTimeout(() => {
        successDiv.remove();
    }, 3000);
}

// Add CSS animation for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);

// Tool switching functionality
const toolButtons = document.querySelectorAll('.tool-button');
const toolContents = document.querySelectorAll('.tool-content');
let currentTool = 'video';

toolButtons.forEach(button => {
    button.addEventListener('click', () => {
        const tool = button.dataset.tool;
        currentTool = tool;
        
        // Remove active class from all buttons
        toolButtons.forEach(btn => {
            btn.classList.remove('active');
            btn.querySelector('.active-indicator')?.remove();
        });
        
        // Add active class to clicked button
        button.classList.add('active');
        const indicator = document.createElement('div');
        indicator.className = 'active-indicator';
        button.appendChild(indicator);
        
        // Hide all tool contents
        toolContents.forEach(content => {
            content.classList.add('hidden');
        });
        
        // Show selected tool content
        document.getElementById(tool + '-content').classList.remove('hidden');
    });
});

// Format button functionality
const formatButtons = document.querySelectorAll('.format-button');
const formatBadge = document.getElementById('format-badge');
let currentFormat = 'bullets';

const formatColors = {
    bullets: 'linear-gradient(90deg, #3b82f6 0%, #06b6d4 100%)',
    paragraphs: 'linear-gradient(90deg, #10b981 0%, #059669 100%)',
    notes: 'linear-gradient(90deg, #8b5cf6 0%, #7c3aed 100%)',
    mindmap: 'linear-gradient(90deg, #ec4899 0%, #be185d 100%)',
    keywords: 'linear-gradient(90deg, #6366f1 0%, #4f46e5 100%)',
    slides: 'linear-gradient(90deg, #f59e0b 0%, #f97316 100%)'
};

const formatLabels = {
    bullets: 'Bullet Points',
    paragraphs: 'Paragraphs',
    notes: 'Short Notes',
    mindmap: 'Mind Map',
    keywords: 'Keywords',
    slides: 'Slides'
};

formatButtons.forEach(button => {
    button.addEventListener('click', () => {
        const format = button.dataset.format;
        currentFormat = format;
        
        // Remove active class from all format buttons
        formatButtons.forEach(btn => {
            btn.classList.remove('active');
            btn.classList.remove('bullets', 'paragraphs', 'notes', 'mindmap', 'keywords', 'slides');
        });
        
        // Add active class to clicked button
        button.classList.add('active', format);
        
        // Update format badge
        formatBadge.textContent = formatLabels[format];
        formatBadge.style.background = formatColors[format];
    });
});

// File upload functionality
function setupFileUpload() {
    const uploadArea = document.querySelector('.upload-area');
    const chooseFileBtn = uploadArea.querySelector('button');
    let fileInput;

    // Create hidden file input
    if (!fileInput) {
        fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.pdf,.docx,.doc';
        fileInput.style.display = 'none';
        document.body.appendChild(fileInput);
    }

    // Click event
    chooseFileBtn.addEventListener('click', () => {
        fileInput.click();
    });

    // File selection
    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            await uploadFile(file);
        }
    });

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = 'rgba(251, 191, 36, 0.5)';
    });

    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = 'rgba(251, 191, 36, 0.3)';
    });

    uploadArea.addEventListener('drop', async (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = 'rgba(251, 191, 36, 0.3)';
        
        const file = e.dataTransfer.files[0];
        if (file) {
            await uploadFile(file);
        }
    });
}

async function uploadFile(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);

        // Show upload progress
        const uploadArea = document.querySelector('.upload-area');
        const originalContent = uploadArea.innerHTML;
        uploadArea.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; gap: 16px;">
                <div class="spinner"></div>
                <p style="color: #d1d5db;">Uploading and processing file...</p>
            </div>
        `;

        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            // Update upload area with success
            uploadArea.innerHTML = `
                <svg style="width: 48px; height: 48px; color: