# GalleryCleaner

Lightweight keyboard-first desktop application to review image folders quickly and move unwanted files to your system trash with minimal interactions.

## Table of Contents

- [About](#about)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Tech Stack](#tech-stack)
- [License](#license)

## About

Cleaning large photo folders with a normal file manager is slow: too many clicks, too many dialogs, and too much context switching.

GalleryCleaner provides a focused full-screen workflow where you can preview, navigate, rotate, and trash images rapidly using keyboard shortcuts, enabling rapid curation of large image collections with minimal friction.

## Features

- **Keyboard-First Navigation:** Primary navigation via keyboard (`A`/`D` or arrow keys) for speed
- **One-Key Trash Action:** Delete unwanted images instantly with single key press
- **Safe Deletion:** Uses system trash (`send2trash`) - deleted files are recoverable
- **Image Rotation:** Visual preview rotation plus persistent file rotation
- **Recursive Scanning:** Optional recursive directory scanning for batch processing
- **Rapid Refresh:** Quick iteration with refresh and navigation shortcuts
- **Modern UI:** Built with CustomTkinter for clean, native-looking interface
- **Cross-Platform:** Works on Windows, macOS, and Linux

## Project Structure

```text
GalleryCleaner/
├── src/
│   └── main.py                    # Main desktop application
├── scripts/
│   ├── setup.bat                  # Windows setup script
│   ├── setup.sh                   # Unix/macOS setup script
│   ├── run.bat                    # Windows run script
│   └── run.sh                     # Unix/macOS run script
├── resources/
│   └── images/                    # Application icons and assets
├── docs/
│   └── images/
│       └── screenshot.png         # UI screenshot
├── requirements.txt               # Python dependencies
├── LICENSE
└── README.md
```

Project organization:
- **src/**: Main application source code
- **scripts/**: Setup and runtime automation scripts
- **resources/**: Application assets (icons, images)
- **docs/**: Documentation and screenshots

## Installation

### Prerequisites

- Python 3.7 or newer
- Windows, macOS, or Linux

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LorenBll/GalleryCleaner.git
   cd GalleryCleaner
   ```

2. **Run the setup script:**
   - **Windows:**
     ```bash
     scripts\setup.bat
     ```
   - **macOS/Linux:**
     ```bash
     chmod +x scripts/setup.sh scripts/run.sh
     ./scripts/setup.sh
     ```

3. **Run the application:**
   - **Windows:**
     ```bash
     scripts\run.bat
     ```
   - **macOS/Linux:**
     ```bash
     ./scripts/run.sh
     ```

The setup script creates a virtual environment (`.venv`) and installs dependencies from `requirements.txt`.

### Manual Execution

1. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   ```
   - **Windows:**
     ```bash
     .venv\Scripts\activate
     ```
   - **macOS/Linux:**
     ```bash
     source .venv/bin/activate
     ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the application:**
   ```bash
   python src/main.py
   ```

## Usage

1. Launch the application
2. Enter path to an image directory
3. Optionally enable recursive mode to scan subdirectories
4. Navigate through images and trash unwanted files
5. Use keyboard shortcuts for rapid navigation and deletion

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `A` / `Left Arrow` | Navigate to previous image |
| `D` / `Right Arrow` | Navigate to next image |
| `S` / `Down Arrow` | Move current image to trash |
| `Ctrl+Q` | Rotate image left |
| `Ctrl+E` | Rotate image right |
| `Ctrl+R` | Refresh folder contents |
| `Esc` / `Ctrl+B` | Return to folder path input |
| `Enter` | Submit folder path |

## Tech Stack

- **Language:** Python 3.7+
- **GUI Framework:** CustomTkinter
- **Image Processing:** Pillow
- **File Handling:** Send2Trash (safe deletion to system trash)

## License

This project is licensed under the terms specified in [LICENSE](LICENSE).
