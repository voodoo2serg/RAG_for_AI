/**
 * Universal File Upload Widget
 * Reusable drag-and-drop component with progress tracking
 * 
 * @version 1.0.0
 * @author AI Agent
 */

class FileUploadWidget {
    constructor(options = {}) {
        this.config = {
            container: null,
            uploadUrl: null,
            accept: '*',
            maxFileSize: 100 * 1024 * 1024, // 100MB
            maxFiles: null,
            parallel: 3,
            autoUpload: true,
            headers: {},
            formData: {},
            retryAttempts: 3,
            retryDelay: 1000,
            ...options
        };

        this.files = [];
        this.uploadQueue = [];
        this.activeUploads = 0;
        this.stats = { uploaded: 0, failed: 0, total: 0 };

        this.callbacks = {
            onSelect: options.onSelect || (() => {}),
            onProgress: options.onProgress || (() => {}),
            onComplete: options.onComplete || (() => {}),
            onError: options.onError || (() => {}),
            onRetry: options.onRetry || (() => {}),
            onRemove: options.onRemove || (() => {})
        };

        this.init();
    }

    init() {
        this.container = typeof this.config.container === 'string' 
            ? document.querySelector(this.config.container)
            : this.config.container;

        if (!this.container) {
            throw new Error('FileUploadWidget: container not found');
        }

        this.render();
        this.bindEvents();
    }

    render() {
        this.container.innerHTML = `
            <div class="fuw-container">
                <div class="fuw-dropzone" id="${this.getId('dropzone')}">
                    <div class="fuw-dropzone-icon">📁</div>
                    <div class="fuw-dropzone-text">Перетащите файлы сюда</div>
                    <div class="fuw-dropzone-hint">или нажмите для выбора</div>
                    <input type="file" 
                           class="fuw-file-input" 
                           id="${this.getId('input')}"
                           accept="${this.config.accept}"
                           multiple
                    >
                </div>
                
                <div class="fuw-file-list" id="${this.getId('list')}"></div>
                
                <div class="fuw-stats" id="${this.getId('stats')}" style="display: none;">
                    <span class="fuw-stat-total">Всего: <b>0</b></span>
                    <span class="fuw-stat-uploaded">✓ <b>0</b></span>
                    <span class="fuw-stat-failed">✗ <b>0</b></span>
                </div>
                
                <div class="fuw-actions" id="${this.getId('actions')}" style="display: none;">
                    <button class="fuw-btn fuw-btn-primary" id="${this.getId('upload')}">
                        Загрузить все
                    </button>
                    <button class="fuw-btn fuw-btn-secondary" id="${this.getId('clear')}">
                        Очистить
                    </button>
                </div>
            </div>
        `;

        this.injectStyles();
    }

    getId(suffix) {
        return `fuw-${this.container.id || 'widget'}-${suffix}`;
    }

    injectStyles() {
        if (document.getElementById('fuw-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'fuw-styles';
        styles.textContent = `
            .fuw-container {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                color: #c9d1d9;
            }

            .fuw-dropzone {
                border: 3px dashed #30363d;
                border-radius: 12px;
                padding: 40px 30px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                background: #161b22;
            }

            .fuw-dropzone:hover, .fuw-dropzone.dragover {
                border-color: #58a6ff;
                background: rgba(88, 166, 255, 0.05);
            }

            .fuw-dropzone-icon {
                font-size: 3em;
                margin-bottom: 15px;
                opacity: 0.6;
            }

            .fuw-dropzone-text {
                font-size: 1.1em;
                margin-bottom: 8px;
            }

            .fuw-dropzone-hint {
                color: #8b949e;
                font-size: 0.9em;
            }

            .fuw-file-input {
                display: none;
            }

            .fuw-file-list {
                margin-top: 20px;
            }

            .fuw-file-item {
                display: flex;
                align-items: center;
                background: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px 16px;
                margin-bottom: 10px;
                transition: border-color 0.2s;
            }

            .fuw-file-item:hover {
                border-color: #58a6ff;
            }

            .fuw-file-item.uploading {
                border-color: #58a6ff;
            }

            .fuw-file-item.success {
                border-color: #3fb950;
            }

            .fuw-file-item.error {
                border-color: #f85149;
            }

            .fuw-file-icon {
                font-size: 1.5em;
                margin-right: 12px;
            }

            .fuw-file-info {
                flex: 1;
                min-width: 0;
            }

            .fuw-file-name {
                font-weight: 500;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .fuw-file-meta {
                font-size: 0.85em;
                color: #8b949e;
                margin-top: 2px;
            }

            .fuw-file-progress {
                width: 100px;
                margin: 0 16px;
            }

            .fuw-progress-bar {
                height: 6px;
                background: #30363d;
                border-radius: 3px;
                overflow: hidden;
            }

            .fuw-progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #58a6ff, #3fb950);
                border-radius: 3px;
                transition: width 0.3s ease;
                width: 0%;
            }

            .fuw-progress-text {
                font-size: 0.75em;
                color: #8b949e;
                text-align: center;
                margin-top: 4px;
            }

            .fuw-file-status {
                font-size: 1.2em;
                margin-left: 12px;
            }

            .fuw-file-remove {
                background: none;
                border: none;
                color: #8b949e;
                cursor: pointer;
                font-size: 1.2em;
                padding: 4px 8px;
                border-radius: 4px;
                transition: all 0.2s;
                margin-left: 8px;
            }

            .fuw-file-remove:hover {
                color: #f85149;
                background: rgba(248, 81, 73, 0.1);
            }

            .fuw-file-retry {
                background: #1f6feb;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.85em;
                margin-left: 8px;
                transition: background 0.2s;
            }

            .fuw-file-retry:hover {
                background: #388bfd;
            }

            .fuw-stats {
                display: flex;
                gap: 20px;
                margin-top: 20px;
                padding: 12px 16px;
                background: #161b22;
                border-radius: 8px;
                border: 1px solid #30363d;
            }

            .fuw-stat-total { color: #8b949e; }
            .fuw-stat-uploaded { color: #3fb950; }
            .fuw-stat-failed { color: #f85149; }

            .fuw-actions {
                display: flex;
                gap: 12px;
                margin-top: 20px;
            }

            .fuw-btn {
                padding: 10px 20px;
                border-radius: 6px;
                border: 1px solid;
                cursor: pointer;
                font-size: 0.95em;
                transition: all 0.2s;
            }

            .fuw-btn-primary {
                background: #238636;
                border-color: #238636;
                color: white;
            }

            .fuw-btn-primary:hover {
                background: #2ea043;
            }

            .fuw-btn-secondary {
                background: transparent;
                border-color: #30363d;
                color: #8b949e;
            }

            .fuw-btn-secondary:hover {
                border-color: #8b949e;
                color: #c9d1d9;
            }

            .fuw-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }

            @keyframes fuw-pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }

            .fuw-file-item.uploading .fuw-file-icon {
                animation: fuw-pulse 1.5s infinite;
            }
        `;

        document.head.appendChild(styles);
    }

    bindEvents() {
        const dropzone = this.container.querySelector('.fuw-dropzone');
        const input = this.container.querySelector('.fuw-file-input');
        const uploadBtn = this.container.querySelector('.fuw-btn-primary');
        const clearBtn = this.container.querySelector('.fuw-btn-secondary');

        // Click to select
        dropzone.addEventListener('click', () => input.click());

        // File selection
        input.addEventListener('change', (e) => this.handleFiles(e.target.files));

        // Drag & drop
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });

        // Buttons
        uploadBtn?.addEventListener('click', () => this.uploadAll());
        clearBtn?.addEventListener('click', () => this.clear());
    }

    handleFiles(fileList) {
        const newFiles = Array.from(fileList).map(file => ({
            id: Math.random().toString(36).substr(2, 9),
            file,
            name: file.name,
            size: file.size,
            formattedSize: this.formatSize(file.size),
            status: 'pending', // pending, uploading, success, error
            progress: 0,
            retries: 0,
            error: null
        }));

        // Validation
        const validFiles = newFiles.filter(f => {
            if (f.size > this.config.maxFileSize) {
                f.status = 'error';
                f.error = `File too large (max ${this.formatSize(this.config.maxFileSize)})`;
                return false;
            }
            return true;
        });

        // Max files check
        if (this.config.maxFiles && this.files.length + validFiles.length > this.config.maxFiles) {
            const allowed = this.config.maxFiles - this.files.length;
            validFiles.splice(allowed);
            this.showError(`Maximum ${this.config.maxFiles} files allowed`);
        }

        this.files.push(...validFiles);
        this.stats.total = this.files.length;

        this.renderFileList();
        this.updateStats();
        this.callbacks.onSelect([...this.files]);

        if (this.config.autoUpload) {
            this.uploadAll();
        }
    }

    renderFileList() {
        const list = this.container.querySelector('.fuw-file-list');
        const actions = this.container.querySelector('.fuw-actions');

        if (this.files.length === 0) {
            list.innerHTML = '';
            actions.style.display = 'none';
            return;
        }

        actions.style.display = 'flex';

        list.innerHTML = this.files.map(f => `
            <div class="fuw-file-item ${f.status}" data-id="${f.id}">
                <div class="fuw-file-icon">${this.getFileIcon(f)}</div>
                <div class="fuw-file-info">
                    <div class="fuw-file-name">${f.name}</div>
                    <div class="fuw-file-meta">${f.formattedSize}${f.error ? ' • ' + f.error : ''}</div>
                </div>
                <div class="fuw-file-progress">
                    <div class="fuw-progress-bar">
                        <div class="fuw-progress-fill" style="width: ${f.progress}%"></div>
                    </div>
                    <div class="fuw-progress-text">${f.progress}%</div>
                </div>
                <div class="fuw-file-status">${this.getStatusIcon(f)}</div>
                ${f.status === 'error' ? `<button class="fuw-file-retry" data-id="${f.id}">↻ Retry</button>` : ''}
                <button class="fuw-file-remove" data-id="${f.id}">✕</button>
            </div>
        `).join('');

        // Bind remove buttons
        list.querySelectorAll('.fuw-file-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.dataset.id;
                this.removeFile(id);
            });
        });

        // Bind retry buttons
        list.querySelectorAll('.fuw-file-retry').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.dataset.id;
                this.retryFile(id);
            });
        });
    }

    getFileIcon(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        const icons = {
            json: '📋',
            csv: '📊',
            pdf: '📄',
            txt: '📝',
            md: '📝',
            html: '🌐',
            xml: '📰'
        };
        return icons[ext] || '📎';
    }

    getStatusIcon(file) {
        const icons = {
            pending: '⏸',
            uploading: '⏳',
            success: '✓',
            error: '✗'
        };
        return icons[file.status] || '?';
    }

    updateStats() {
        const stats = this.container.querySelector('.fuw-stats');
        if (this.files.length === 0) {
            stats.style.display = 'none';
            return;
        }

        stats.style.display = 'flex';
        stats.querySelector('.fuw-stat-total b').textContent = this.stats.total;
        stats.querySelector('.fuw-stat-uploaded b').textContent = this.stats.uploaded;
        stats.querySelector('.fuw-stat-failed b').textContent = this.stats.failed;
    }

    async uploadAll() {
        const pending = this.files.filter(f => f.status === 'pending' || f.status === 'error');
        if (pending.length === 0) return;

        // Process in parallel with limit
        const queue = [...pending];
        const workers = Array(this.config.parallel).fill().map(() => 
            this.processQueue(queue)
        );

        await Promise.all(workers);

        this.callbacks.onComplete([...this.files]);
    }

    async processQueue(queue) {
        while (queue.length > 0) {
            const file = queue.shift();
            await this.uploadFile(file);
        }
    }

    async uploadFile(file) {
        if (!file || file.status === 'success') return;

        file.status = 'uploading';
        file.progress = 0;
        this.renderFileList();

        const formData = new FormData();
        formData.append('file', file.file);
        
        // Add extra form fields
        Object.entries(this.config.formData).forEach(([key, value]) => {
            formData.append(key, value);
        });

        try {
            const xhr = new XMLHttpRequest();
            
            const uploadPromise = new Promise((resolve, reject) => {
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        file.progress = Math.round((e.loaded / e.total) * 100);
                        this.renderFileList();
                        this.callbacks.onProgress(file, file.progress);
                    }
                });

                xhr.addEventListener('load', () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        resolve(xhr.response);
                    } else {
                        reject(new Error(xhr.statusText || `HTTP ${xhr.status}`));
                    }
                });

                xhr.addEventListener('error', () => reject(new Error('Network error')));
                xhr.addEventListener('abort', () => reject(new Error('Upload aborted')));
            });

            xhr.open('POST', this.config.uploadUrl);
            
            // Set headers
            Object.entries(this.config.headers).forEach(([key, value]) => {
                xhr.setRequestHeader(key, value);
            });

            xhr.send(formData);

            await uploadPromise;

            file.status = 'success';
            file.progress = 100;
            this.stats.uploaded++;

        } catch (error) {
            file.retries++;
            
            if (file.retries < this.config.retryAttempts) {
                file.status = 'pending';
                this.callbacks.onRetry(file, file.retries);
                await this.delay(this.config.retryDelay);
                return this.uploadFile(file);
            } else {
                file.status = 'error';
                file.error = error.message;
                this.stats.failed++;
                this.callbacks.onError(file, error);
            }
        }

        this.renderFileList();
        this.updateStats();
    }

    retryFile(id) {
        const file = this.files.find(f => f.id === id);
        if (file) {
            file.status = 'pending';
            file.progress = 0;
            file.retries = 0;
            file.error = null;
            this.uploadFile(file);
        }
    }

    removeFile(id) {
        const index = this.files.findIndex(f => f.id === id);
        if (index > -1) {
            const file = this.files[index];
            this.files.splice(index, 1);
            
            if (file.status === 'success') this.stats.uploaded--;
            if (file.status === 'error') this.stats.failed--;
            this.stats.total--;
            
            this.renderFileList();
            this.updateStats();
            this.callbacks.onRemove(file);
        }
    }

    clear() {
        this.files = [];
        this.stats = { uploaded: 0, failed: 0, total: 0 };
        this.renderFileList();
        this.updateStats();
    }

    formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    showError(message) {
        console.error('FileUploadWidget:', message);
        // Could show toast notification here
    }

    // Public API
    getFiles() {
        return [...this.files];
    }

    getStats() {
        return { ...this.stats };
    }

    destroy() {
        this.container.innerHTML = '';
        const styles = document.getElementById('fuw-styles');
        if (styles) styles.remove();
    }
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FileUploadWidget;
} else if (typeof define === 'function' && define.amd) {
    define(() => FileUploadWidget);
} else {
    window.FileUploadWidget = FileUploadWidget;
}
