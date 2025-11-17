# FFmpeg Proxy Sandbox

FFmpeg Proxy Sandbox is a lightweight transcoding experiment tool designed for fast testing of encoding recipes using proxy-based video processing.  
The system provides quick clip extraction, batch transcoding, automated quality analysis, and a clean Tkinter GUI optimized for research and evaluation.

---

## Features

### 🔹 Proxy-Based Transcoding
- Generate multiple short proxy clips from a single input video.
- Supports multiple start points and custom duration.
- Extracts proxy clips without re-encoding for maximum speed.

### 🔹 Recipe-Based Encoding
- Uses `recipes.json` to define codec, CRF, preset, and encoder settings.
- Supports:
  - Single encoding
  - Multi-encoding (batch)
  - Apply-to-full-video operations

### 🔹 Quality Metrics (Automatic)
For every encoded output, the system automatically computes:
- **PSNR** (Peak Signal-to-Noise Ratio)
- **SSIM** (Structural Similarity Index)
- **Encode duration (seconds)**
- **File size comparison (original proxy vs encoded)**

All results are exported into a **summary.csv** file.

### 🔹 GUI Application (Tkinter)
The GUI provides:
- Multi-start time entry
- Duration control
- Recipe selection
- Input/output browser
- Real-time log viewer
- Status banner (success/error)
- "Open folder" shortcuts
- **Keep proxy files** checkbox (toggle deletion of temporary proxies)

### 🔹 Validation & Safety
- Recipe validator (checks codec/preset fields)
- FFmpeg path checker
- Error propagation from the engine to the GUI

---

## Installation

### Requirements
- Python 3.10+
- FFmpeg installed (and accessible through system PATH)
Download: [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)


---

## Running the Program (from source)

```
python gui_main.py
```

---

## Building a Standalone Executable (Windows)

### 1. Install PyInstaller

```
pip install pyinstaller
```

### 2. Build the executable

```
pyinstaller --onefile --noconsole gui_main.py
```

### 3. Place recipes.json next to the .exe

The folder should look like:

```
dist/
gui_main.exe 
recipes.json
```
The program loads recipes from the working directory (same folder as the executable).

---

## License

MIT License.

---

## Contributing

Contributions are welcome.
This project follows clean coding principles—including SOLID, DRY, and KISS.

