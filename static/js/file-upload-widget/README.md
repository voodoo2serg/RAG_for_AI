# Universal File Upload Component

Reusable drag-and-drop file upload widget with progress tracking, error handling, and batch support.

## Features
- 📁 Drag & drop multiple files
- 📊 Real-time progress bars
- 🔄 Auto-retry on failure
- 📱 Mobile-friendly
- 🎨 Customizable styling
- 🔌 Framework-agnostic (vanilla JS)

## Quick Start

```html
<div id="upload-widget"></div>

<script src="/static/js/file-upload-widget.js"></script>
<script>
const uploader = new FileUploadWidget({
    container: '#upload-widget',
    uploadUrl: '/api/upload',
    onComplete: (files) => console.log('Done:', files)
});
</script>
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `container` | string/Element | required | Target DOM element |
| `uploadUrl` | string | required | API endpoint URL |
| `accept` | string | "*" | Accepted file types |
| `maxFileSize` | number | 100MB | Max file size in bytes |
| `maxFiles` | number | null | Max files per batch |
| `parallel` | number | 3 | Parallel upload count |
| `autoUpload` | boolean | true | Start immediately |
| `headers` | object | {} | Custom HTTP headers |
| `formData` | object | {} | Additional form fields |

## Events

- `onSelect(files)` — files selected
- `onProgress(file, percent)` — upload progress
- `onComplete(files)` — all uploads done
- `onError(file, error)` — upload failed
- `onRetry(file, attempt)` — retrying upload
