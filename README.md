# GalleryCleaner

GalleryCleaner is a local, keyboard-first image review application for cleaning large image collections with minimal clicks, dialogues, and navigation friction.

Developer documentation: [README-DEV.md](README-DEV.md).

## Table of Contents

- [Features](#features)
- [Setup](#setup)
- [Run](#run)
- [Usage](#usage)
- [Configuration](#configuration)
- [Support](#support)
- [Licence](#licence)
- [Author](#author)

## Features

- **Keyboard-first workflow** — navigate and act on images with single-key shortcuts so a large collection can be triaged without leaving the keyboard; press `A` and `D` to move between images, `S` to trash the current image, and `Ctrl+Q` and `Ctrl+E` to rotate.
- **Safe file removal** — move the current image to the operating system trash with `send2trash` instead of deleting it permanently, so a mistaken removal can be undone; press `S`, use the Down Arrow, or click the trash button.
- **Recursive directory review** — review images from nested subdirectories as a single navigation queue; tick "Operate Recursively" on the directory screen before submitting so nested images are included.
- **Two rotation modes** — rotate an image 90° clockwise or counter-clockwise either in the preview only or on disk, so a rotation can be previewed before it is made permanent; tick "Replicate Rotation On File" (on by default) to write the rotation to the file, or clear it to keep the rotation in the preview only.
- **Image preloading** — preload images around the current position in a background thread to keep navigation responsive in large collections; preloading runs automatically as images are displayed.
- **File metadata preview** — show the file name without extension, format, size, resolution, creation timestamp, and modification timestamp beneath the image, so the current file can be judged without leaving the viewer.
- **Progress indication** — show the current image index, a progress bar, and a percentage so the position in the queue is always visible.
- **Refresh** — rescan the current directory with `Ctrl+R` after files change outside the application, keeping the current image selected when it still exists.
- **DiskIdentifier references** — accept `<64-character hex hash>::<relative path>` references in the directory field and resolve them to absolute paths by querying the DiskIdentifier service, so images can be addressed independently of drive letters.
- **Cross-platform desktop application** — run on Windows, macOS, and Linux through a CustomTkinter desktop interface.

## Setup

1. Install Python 3.10 or higher. `src/main.py` uses `X | None` union annotations that are evaluated at run time, and these require Python 3.10.
2. Clone the repository.
3. Create a virtual environment and activate it, or run the provided setup script (`scripts\setup.bat` on Windows, `bash scripts/setup.sh` on Unix-like systems), which creates `.venv` and installs the dependencies.
4. Install the dependencies with `pip install -r requirements.txt` (`customtkinter`, `pillow`, and `send2trash`).
5. Keep the repository layout intact. The application loads `resources/configuration.json` and the icons in `resources/images/` relative to the project root, and imports its modules from `src/`.
6. Keep `resources/images/` populated so the button icons load. When an icon is missing, the corresponding button falls back to a text label and the application still runs.

## Run

1. Windows: run `scripts\run.bat`.
2. Unix-like: run `bash scripts/run.sh`.
3. Manual: run `python src/main.py` from the project root.

The run scripts activate `.venv` and start `src/main.py`. They accept no command-line options, and they stop with an error when `.venv` does not exist, so run the setup script first.

## Usage

1. Launch the application.
2. Enter an absolute directory path that contains images, or a DiskIdentifier reference.
3. Optionally tick "Operate Recursively" to include images from subdirectories.
4. Submit the path with the Submit button or the Enter key.
5. Navigate the images and move unwanted files to the trash with the keyboard shortcuts or the on-screen buttons.

If no supported images are found, the directory screen displays an error message.

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

### Supported Image Formats

GalleryCleaner recognises the extensions `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`, `.svg`, `.ico`, `.tga`, and `.psd`. Directory listings ignore any file whose name contains `desktop.ini`.

### Error Handling

Before browsing, GalleryCleaner checks that the path exists, that it is a directory, and that it is readable, writable, and executable. Unreadable or unsupported images fail gracefully during loading without terminating the application.

### DiskIdentifier References

The directory field also accepts DiskIdentifier references of the form `<64-character hex hash>::<relative path>`. GalleryCleaner resolves them by querying the DiskIdentifier service over HTTP and, when the configured port does not answer, by discovering the service port through ServiceHandler. The request details are documented in [README-DEV.md](README-DEV.md).

## Configuration

GalleryCleaner reads `resources/configuration.json`. If the file is missing, unreadable, or invalid JSON, every key falls back to its default. A missing key also falls back to its default.

| Key | Default | Effect |
|---|---|---|
| `diskidentifierPort` | `49157` | Port of the DiskIdentifier service on `127.0.0.1` used to resolve DiskIdentifier references. A value that is not an integer falls back to `49157`. |
| `servicehandlerEnabled` | `true` | Whether ServiceHandler port discovery is attempted when the configured DiskIdentifier port does not answer. Set it to `false` to disable the fallback; the strings `true`, `1`, and `yes` (case-insensitive) count as enabled. |
| `servicehandlerPort` | `49155` | Port of the ServiceHandler service on `127.0.0.1` used for port discovery. A value that is not an integer falls back to `49155`. |

## Support

- Open an issue on [GitHub](https://github.com/LorenBll/GalleryCleaner/issues) for bug reports, feature requests, or help.

## Licence

- [LICENSE](LICENSE)

## Author

- [LorenBll](https://github.com/LorenBll)
