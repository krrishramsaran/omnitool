# 🛠️ OmniTool
### The 100% Local, Offline Media & PDF Power Suite for Windows

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-success)](#)
[![GUI](https://img.shields.io/badge/GUI-CustomTkinter-blue)](#)

**A private, zero-subscription desktop toolbox uniting interactive PDF annotation, video timeline editing, and smart image processing into one lightweight native application.**

---

## 🌟 Why OmniTool?

- **🔒 100% Offline & Private:** No files are ever uploaded to cloud servers. All rendering, AI background cutouts, and video encoding happen locally on your computer's CPU and disk.
- **⚡ Lightning Fast:** Video cuts use direct stream copying (`-c copy`) for instant 1-second cuts without quality loss or re-encoding.
- **🎨 Modern UI:** Sleek, responsive dark/light mode interface built with CustomTkinter.
- **📦 Portable & Turnkey:** Includes an automated setup script that detects or installs Python and sets up an isolated environment in a single click.

---

## 🚀 Key Features

### 📄 1. PDF Visual Studio & Annotator
- **Visual Page Navigation:** Interactive page canvas with `◀ Prev` and `Next ▶` controls, zoom, and live page counter (`Page X of Y`).
- **✏️ Freehand Drawing / Pen:** Sign documents or make hand-drawn notes directly on the page with customizable colors (Black, Red, Blue, Green, Gold) and line widths.
- **📝 Click-to-Place Text:** Click anywhere on the rendered PDF page to place customized text annotations at exact coordinates.
- **🖋️ Signature & Stamp Placement:** Browse your signature image (PNG/JPG) and click to stamp it onto the document.
- **💾 Flatten & Save:** Export clean, professional annotated PDFs with all drawings, signatures, and texts embedded permanently.
- **⚡ Batch PDF Utilities:**
  - **Merge:** Reorder and combine multiple PDFs into a single document.
  - **Split / Extract:** Burst into individual pages or extract custom ranges (`e.g. 1-3, 5`).
  - **Rotate:** 90°, 180°, or 270° clockwise page rotation.
  - **Images ↔ PDF:** Convert photo collections into clean PDFs, or render PDF pages into high-res PNG/JPGs.
  - **PDF Compressor:** Downscale embedded high-res images and deflate streams for email upload limits.
  - **Encryption / Decryption:** AES-256 password protection and password removal.

---

### 🎬 2. Video Studio with Timeline Bar & Audio Tools
- **Real-Time Video Screen:** Low-latency frame rendering using high-speed FFmpeg pipes directly onto the screen.
- **Timeline Scrubber:** Smooth slider scrubbing through the entire video with live timestamp counters (`00:04.2 / 00:30.0`).
- **Playback Controls:** Play / Pause preview with synchronized frame updates.
- **Visual In/Out Cutting:**
  - Set Start (`[ In`) and Set End (`Out ]`) markers visually along the timeline.
  - Real-time cut duration calculation (`Cut: 00:02.5 ➔ 00:14.0 | Duration: 11.5s`).
  - Instant clip trimming without re-encoding (`-c copy`).
- **Multi-File Media Merging:**
  - **Merge Videos:** Concatenate multiple clips into a single video file.
  - **Merge Audios:** Stitch multiple voice or music tracks together.
  - **Replace / Add Audio:** Mux a new audio track into an existing video.
- **Extra Utilities:**
  - **Smooth GIF Maker:** 2-pass optimal palette generation (`palettegen` / `paletteuse`) with configurable FPS and resolution.
  - **Target File Size Compressor:** Automatically computes target bitrate for Discord (25MB), WhatsApp (16MB), or custom limits.
  - **Audio Extractor:** Extract MP3, WAV, or AAC audio tracks from video.
  - **Mute Video:** Strip audio streams without touching video frames.
  - **Speed Controller:** 0.5x, 0.75x, 1.25x, 1.5x, or 2.0x video retiming with audio pitch correction.

---

### 🎨 3. Smart Image Editor & Resizer
- **Current Dimension Indicator:** Displays original resolution and file size upon loading (`Current Size: 1920 × 1080 px  (1.8 MB)`).
- **Interactive Dimension Pre-fills:** Automatically populates `Width` and `Height` input boxes for quick adjustments.
- **Proportional Auto-Sync:** When **Lock Aspect Ratio** is active, editing the `Width` automatically updates the `Height` proportionally (and vice versa).
- **One-Click Platform Presets:**
  - Instagram Story / Reel (`1080x1920`)
  - Instagram Post Square (`1080x1080`)
  - YouTube Thumbnail (`1280x720`)
  - Passport Photo format (`600x600`)
  - Twitter / X Header (`1500x500`)
  - Email Attachment (`<10MB`)
- **Live Side-by-Side Preview:** Inspect original vs processed thumbnails side-by-side before exporting.
- **✨ AI Background Remover:** 1-click subject cutout to transparent PNG powered locally by `rembg`.
- **🛡️ Privacy EXIF Stripper:** Scrub embedded GPS coordinates, camera serials, and timestamps.
- **📦 Multi-Size Favicon Generator:** Generate multi-resolution `.ico` bundles (`16x16` up to `256x256`) and `apple-touch-icon.png` from a single image.
- **Fine Tuning Sliders:** Real-time adjustments for Brightness, Contrast, Sharpness, Saturation, and Monochrome/B&W.

---

## 📥 Quick Start

Double-click the launcher in the root folder:

```cmd
run_app.bat
```

> **Note:** The launcher automatically checks for Python. If missing, it installs it via Windows Package Manager (`winget`), creates a local `.venv` environment, installs dependencies, and boots the app.

---

## 💻 Installation Guide for Any Windows PC

### Option 1: Standalone Application (.exe) — No Python Needed!
1. Go to the [Releases Page](https://github.com/krrishramsaran/omnitool/releases/tag/v1.0.0).
2. Download **`OmniTool-v1.0.0-Windows.zip`**.
3. Extract the folder and directly double-click:
   ```cmd
   OmniTool.exe
   ```
   *No Python installation or terminal setup required.*

### Option 2: Run with Launcher Script
1. Download **`OmniTool-Windows.zip`** from [Releases](https://github.com/krrishramsaran/omnitool/releases).
2. Extract the folder and double-click:
   ```cmd
   run_app.bat
   ```

### Option 2: Clone with Git
```powershell
# Clone the repository
git clone https://github.com/krrishramsaran/omnitool.git

# Enter the project directory
cd omnitool

# Launch the application
run_app.bat
```

### Option 3: Manual Developer Setup
```powershell
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate the virtual environment
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the suite
python main.py
```

---

## 📂 Project Structure

```text
omnitool/
├── run_app.bat                 # One-click Windows runner & auto-installer
├── main.py                     # Primary desktop window & theme manager
├── requirements.txt            # Python dependencies
├── README.md                   # Comprehensive documentation
├── core/
│   ├── __init__.py
│   ├── ffmpeg_utils.py         # Portable FFmpeg runner & metadata parser
│   ├── pdf_tools.py            # PyMuPDF engine (annotations, merge, split, compress)
│   ├── image_tools.py          # Pillow engine (resize, presets, EXIF strip, favicons)
│   └── video_tools.py          # FFmpeg engine (timeline frames, merge, trim, GIFs)
├── gui/
│   ├── __init__.py
│   ├── pdf_tab.py              # Visual PDF canvas, freehand pen, signature stamp UI
│   ├── video_tab.py            # Video screen, timeline scrubber, cut & merge UI
│   └── image_tab.py            # Dimension sync, presets, live side-by-side preview UI
└── tests/
    ├── test_core.py            # Automated unit tests for core modules
    └── test_extended.py        # Extended tests for AI rembg, annotations, and merge
```

---

## 🧪 Running Automated Tests

To run the verification test suite:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

---

## 🔒 Privacy & Security

- **Zero Network Requests:** OmniTool performs no telemetry, analytics, or background internet requests.
- **Local Processing:** All documents, videos, and photos remain strictly on your local storage.
- **Privacy Stripping:** Built-in EXIF scrubber ensures photos shared online do not leak location or camera metadata.

---

## 📄 License

This project is licensed under the **MIT License**. Free for personal and commercial use.
