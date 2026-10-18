# GalleryCleaner

GalleryCleaner is a local, keyboard-first image review application for cleaning large image collections with minimal clicks, dialogues, and navigation friction.

User documentation: [README.md](README.md).

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Endpoints](#endpoints)
- [Setup](#setup)
- [Run](#run)
- [Usage](#usage)
- [Logging](#logging)
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

## Project Structure

```text
GalleryCleaner/
├── src/
│   ├── main.py
│   └── models/
│       ├── __init__.py
│       ├── post_request.py
│       └── post_response.py
├── scripts/
│   ├── run.bat
│   ├── run.sh
│   ├── setup.bat
│   └── setup.sh
├── resources/
│   ├── images/
│   │   ├── arrow-28-64.ico
│   │   ├── arrow-92-64.ico
│   │   ├── check-mark-64.ico
│   │   ├── rotate-64.ico
│   │   ├── sinchronize-64.ico
│   │   ├── stop-64.ico
│   │   └── trash-10-64.ico
│   ├── configuration.json
│   ├── search_index.json
│   └── search_index_reverse.json
├── requirements.txt
├── .gitignore
├── LICENSE
├── README.md
└── README-DEV.md
```

- `src/main.py` — the whole application: the startup dependency check, configuration loading, the CustomTkinter `App` window, image listing and display, rotation, preloading, trashing, and the DiskIdentifier and ServiceHandler HTTP client calls. It is a single module of about 1,390 lines.
- `src/models/post_request.py` — the `PostRequest` dataclass (`url`, `body`, `timeout`, `headers`) used to build outgoing HTTP requests.
- `src/models/post_response.py` — the `PostResponse` dataclass (status code, reason, body, body size, headers, parsed JSON) used to read HTTP responses.
- `src/models/__init__.py` — re-exports `PostRequest` and `PostResponse`.
- `scripts/run.bat`, `scripts/run.sh` — activate `.venv` and start `src/main.py`.
- `scripts/setup.bat`, `scripts/setup.sh` — create `.venv` and install `requirements.txt`.
- `resources/configuration.json` — the configuration read at start-up (see [Configuration](#configuration)).
- `resources/images/` — the button icons. A missing icon falls back to a text label.
- `requirements.txt` — `customtkinter`, `pillow`, and `send2trash`.
- `.gitignore` — excludes `.venv/`, `__pycache__/`, and `*.py[cod]`.

The following paths are created at run time or by tooling and are not part of the source layout:

- `.venv/` — the virtual environment created by the setup scripts. It is git-ignored.
- `logs/` — the log directory created on every start. It is not git-ignored.
- `src/__pycache__/` and `src/models/__pycache__/` — bytecode caches. They are git-ignored.

`resources/search_index.json` and `resources/search_index_reverse.json` are present in the repository but are not referenced by any source file. `resources/images/check-mark-64.ico` is likewise present but not referenced by `src/main.py`.

## Endpoints

GalleryCleaner is a desktop application and exposes no HTTP endpoints. The only HTTP traffic is outbound: it consumes two services on `127.0.0.1` as a client. Both requests are built with `PostRequest` and sent by `_send_request` in `src/main.py`, and both use a 5-second timeout and the header `Content-Type: application/json`. These are client dependencies of GalleryCleaner, not endpoints that this project serves.

### DiskIdentifier service (client dependency)

- Method and path: `GET http://127.0.0.1:<diskidentifierPort>/api/disk/locate`.
- Request body: `{"disk_identifier": "<64-character hex hash>"}`.
- Success: `200` with a JSON object whose `path` field holds the resolved absolute path.
- Error: `404` means the disk identifier is not registered. It raises an error that is shown on the directory screen, and no further port is tried.
- Purpose: resolve a DiskIdentifier reference entered in the directory field to an absolute path.

### ServiceHandler service (client dependency)

- Method and path: `POST http://127.0.0.1:<servicehandlerPort>/api/question/service`.
- Request body: `{"name": "DiskIdentifier"}`.
- Success: `200` with a JSON object whose `port` field gives the DiskIdentifier service port, which is then queried as above.
- Error: any failure raises a warning, and the application reports that the DiskIdentifier service is unavailable.
- Purpose: discover the DiskIdentifier port when the configured port does not answer. This request is made only when `servicehandlerEnabled` is `true`.

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

## Logging

The application writes logs to the `logs/` directory at the project root, which it creates at start-up when it does not exist. Each run writes one file named `DD-MM-YYYY_HH.MM.SS.log` (for example `18-10-2026_14.07.32.log`) and mirrors every message to the console.

Log entries are plain text in the format `<timestamp> - <logger name> - <level> - <message>`, configured with `logging.basicConfig` at `level=logging.INFO`. The file is written as UTF-8. There is one file per run and no size-based rotation.

### Divergences from the Logging Standard

The implementation does not meet the Logging Standard:

- Log files are plain-text `.log` files, not JSON files containing a list of logged events.
- Events do not carry the required `timestamp`, `type`, `title`, `data`, and `hash` fields.
- `scripts/run.bat` and `scripts/run.sh` support no command-line options, including `--debug`, and the level is fixed at `INFO`, so `DEBUG` events are never written.
- No retention check is performed, so log files older than 14 days are not removed.

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
