# GalleryCleaner

GalleryCleaner is a local keyboard-first image review application. It solves the problem of cleaning large image collections quickly by minimizing clicks, dialogs, and navigation friction during image triage.

## About

GalleryCleaner is scoped to rapid image-folder review and provides a focused desktop workflow for navigating, rotating, refreshing, and trashing images with minimal interaction overhead.

**Features:**

- **Keyboard-First Workflow** — primary navigation and actions are designed around keyboard shortcuts for rapid image review.
- **Safe File Removal** — images are moved to the system trash using `send2trash` instead of being permanently deleted.
- **Recursive Directory Review** — optional recursive scanning allows images from nested subdirectories to be reviewed as a single navigation queue.
- **Persistent or Visual Rotation** — image rotation supports two modes: visual-only rotation that affects preview state, and persistent file-level rotation written directly to disk.
- **Image Preloading** — nearby images are asynchronously preloaded into memory to improve navigation responsiveness while browsing large collections.
- **File Metadata Preview** — the viewer displays file name (without extension), file type, file size, resolution, creation timestamp, and modification timestamp.
- **Cross-Platform Desktop Application** — GalleryCleaner works on Windows, macOS, and Linux through a CustomTkinter-based desktop interface.

## Setup

1. Install the Python dependencies with `pip install -r requirements.txt`.
2. Keep the `resources/images/` directory in place so application icons can be loaded (button text fallbacks are used if icons are missing).
3. Optionally use the provided setup scripts to create a local virtual environment automatically (the run scripts require this virtual environment).
4. Leave the project structure intact so the application can find `resources/` and `src/`.

## Run

1. Windows: run `scripts\run.bat`.
2. Unix-like: run `bash scripts/run.sh`.
3. Manual: run `python src/main.py` from the project root.

## Usage

1. Launch the application.
2. Enter an absolute directory path containing images.
3. Optionally enable recursive scanning to include subdirectories.
4. Submit the directory path to begin browsing.
5. Navigate through images and move unwanted files to trash using keyboard shortcuts or UI controls.

If no supported images are found, an error message is displayed on the directory-selection screen.

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `A` / `Left Arrow` | Previous image |
| `D` / `Right Arrow` | Next image |
| `S` / `Down Arrow` | Move current image to trash |
| `Ctrl+Q` | Rotate image counter-clockwise |
| `Ctrl+E` | Rotate image clockwise |
| `Ctrl+R` | Refresh current directory |
| `Esc` | Return to directory selection |
| `Enter` | Submit directory path |

## Notes

### Supported Image Formats

GalleryCleaner currently recognizes the following image extensions:

- `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`, `.svg`, `.ico`, `.tga`, `.psd`

### Error Handling

GalleryCleaner validates:

- directory existence,
- directory read, write, and execute permissions,
- readable image availability.

Unreadable or unsupported images fail gracefully during loading without terminating the application.

### DiskIdentifier Integration

The directory field also accepts DiskIdentifier references in the form `<64-character hex hash>::<relative path>`. GalleryCleaner resolves them by querying the DiskIdentifier service over HTTP, falling back to ServiceHandler port discovery when the configured port does not respond.

### Configuration

`resources/configuration.json` keys:

- `diskidentifierPort` — DiskIdentifier service port (default: `49157`).
- `servicehandlerEnabled` — ServiceHandler port-discovery fallback (default: `true`).
- `servicehandlerPort` — ServiceHandler service port (default: `49155`).

### Logging

Each run writes a log file to `logs/` named `DD-MM-YYYY_HH.MM.SS.log` and mirrors the same messages to the console.

### Tech Stack

- **Language:** Python
- **UI Framework:** CustomTkinter
- **Image Processing:** Pillow
- **File Removal:** Send2Trash

### Project Structure

```text
GalleryCleaner/
├── src/
│   ├── main.py
│   └── models/
│       ├── __init__.py
│       ├── post_request.py
│       └── post_response.py
├── scripts/
│   ├── setup.bat
│   ├── setup.sh
│   ├── run.bat
│   └── run.sh
├── resources/
│   ├── images/
│   ├── configuration.json
│   ├── search_index.json
│   └── search_index_reverse.json
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## Support

- Open an issue on [GitHub](https://github.com/LorenBll/GalleryCleaner/issues) for bug reports, feature requests, or help.

## License

- [LICENSE](LICENSE)

## Author

- [LorenBll](https://github.com/LorenBll)
