# Proxy-Sanbox-FFMPEG
FFmpeg Proxy Sandbox is a lightweight tool for rapid transcoding tests using FFmpeg.
It allows creators, editors, and developers to test multiple encoding recipes on short proxy clips before applying them to full videos.

The project is built with a modular Python engine and a Tkinter GUI.

---

## Features

### Proxy-Based Testing

* Generate multiple proxy clips from a source video
* Apply multiple encoding recipes in one batch
* Compare quality, size, and behavior instantly

### Recipe System (`recipes.json`)

* Editable JSON configuration file
* Supports `libx264`, `libx265`, and `libvpx-vp9`
* Parameters: CRF, preset, bitrate, VP9 deadline
* Recipes can be reloaded from the GUI

### Full-Video Apply

* Apply a selected recipe to one or many input videos
* Output names generated automatically

### Real-Time FFmpeg Logging

* Live FFmpeg logs inside the GUI
* Auto scroll and “Clear Log” features included

### Robust Engine

* Proxy generation (single & batch)
* Encoding pipelines
* Recipe validation
* FFmpeg availability checks

---

## Installation

### 1. Install Python

Python 3.9+ recommended.

### 2. Install FFmpeg

Must be available in system PATH.
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

