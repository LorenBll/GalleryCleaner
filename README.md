# GalleryCleaner

GalleryCleaner is a local keyboard-first image review application. It solves the problem of cleaning large image collections quickly by minimizing clicks, dialogs, and navigation friction during image triage.

## About

GalleryCleaner is scoped to rapid image-folder review and provides a focused desktop workflow for navigating, rotating, refreshing, and trashing images with minimal interaction overhead.

The application uses a fixed-size interface optimized for continuous keyboard-driven operation while preloading nearby images to improve browsing responsiveness.

Image deletion is performed through the operating system trash/recycle-bin mechanism so removed files remain recoverable outside the application.

## Setup

1. Install the Python dependencies with `pip install -r requirements.txt`.
2. Ensure the `resources/images/` directory remains in place so application icons can be loaded.
3. Optionally use the provided setup scripts to create a local virtual environment automatically.
4. Leave the project structure intact so the application can find `resources/` and `src/`.

## Run

1. Windows: run `scripts\run.bat`.
2. Unix-like systems: run `bash scripts/run.sh`.
3. Manual: run `python src/main.py` from the project root.

## Features

### Keyboard-First Workflow

Primary navigation and actions are designed around keyboard shortcuts for rapid image review.

### Safe File Removal

Images are moved to the system trash using `send2trash` instead of being permanently deleted.

### Recursive Directory Review

Optional recursive scanning allows images from nested subdirectories to be reviewed as a single navigation queue.

### Persistent or Visual Rotation

Image rotation supports two modes:

- visual-only rotation that affects preview state,
- persistent file-level rotation written directly to disk.

### Image Preloading

Nearby images are asynchronously preloaded into memory to improve navigation responsiveness while browsing large collections.

### File Metadata Preview

The viewer displays:

- filename,
- file type,
- file size,
- resolution,
- creation timestamp,
- modification timestamp.

### Cross-Platform Desktop Application

GalleryCleaner works on Windows, macOS, and Linux through a CustomTkinter-based desktop interface.

## Supported Image Formats

GalleryCleaner currently recognizes the following image extensions:

- `.jpg`
- `.jpeg`
- `.png`
- `.gif`
- `.bmp`
- `.tiff`
- `.webp`
- `.svg`
- `.ico`
- `.tga`
- `.psd`

## Usage

1. Launch the application.
2. Enter an absolute directory path containing images.
3. Optionally enable recursive scanning to include subdirectories.
4. Submit the directory path to begin browsing.
5. Navigate through images and move unwanted files to trash using keyboard shortcuts or UI controls.

If no supported images are found, the application returns to the directory-selection workflow.

## Keyboard Shortcuts

| Key                 | Action                         |
| ------------------- | ------------------------------ |
| `A` / `Left Arrow`  | Previous image                 |
| `D` / `Right Arrow` | Next image                     |
| `S` / `Down Arrow`  | Move current image to trash    |
| `Ctrl+Q`            | Rotate image counter-clockwise |
| `Ctrl+E`            | Rotate image clockwise         |
| `Ctrl+R`            | Refresh current directory      |
| `Esc`               | Return to directory selection  |
| `Enter`             | Submit directory path          |

## Project Structure

```text
GalleryCleaner/
├── src/
│   └── main.py
├── scripts/
│   ├── setup.bat
│   ├── setup.sh
│   ├── run.bat
│   └── run.sh
├── resources/
│   └── images/
├── docs/
│   └── images/
├── requirements.txt
├── LICENSE
└── README.md
```

## Error Handling

GalleryCleaner validates:

- directory existence,
- directory permissions,
- readable image availability.

Unreadable or unsupported images fail gracefully during loading without terminating the application.

## Tech Stack

- **Language:** Python
- **UI Framework:** CustomTkinter
- **Image Processing:** Pillow
- **File Removal:** Send2Trash

## Support
- Open an issue on [GitHub](https://github.com/LorenBll/GalleryCleaner/issues) for bug reports, feature requests, or help.

## License
- [LICENSE](LICENSE)

## Author
- [LorenBll](https://github.com/LorenBll)
