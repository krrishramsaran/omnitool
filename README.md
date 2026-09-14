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
- **🖱️ Smooth Viewport Scrolling & Panning (No More Zoom Cutoff!):**
  - Full two-dimensional scrolling with horizontal & vertical scrollbars (`CTkScrollbar`).
  - Vertical mousewheel (`<MouseWheel>`) and horizontal scroll (`Shift + MouseWheel`).
  - Middle-click and right-click drag-to-pan (`scan_mark` / `scan_dragto`).
  - **1-Click Fit Modes:** `Fit Width` and `Fit Page` zoom presets.
  - **Pixel-Accurate Mapping:** Window coordinates translate accurately via `canvasx`/`canvasy` so drawings, signatures, texts, and highlights land precisely where intended at any zoom level or scroll position.
- **🖼️ Page Thumbnail Sidebar & Visual Reordering:** Collapsible page thumbnail sidebar with instant 1-click jump, move pages up (`▲ Up`), move pages down (`▼ Down`), and page deletion (`🗑️ Delete Page`).
- **🔍 In-Viewer Search & Highlighting:** Real-time text search across the document with yellow highlight overlays and step-through navigation (`◀ Prev` / `Next ▶`).
- **🔤 Searchable PDF OCR:** Built-in detection for Tesseract OCR engine to convert scanned, image-only PDFs into fully searchable, selectable, and annotatable text PDFs.
- **↩️ Undo / Redo Annotation History:** Multi-level undo and redo stack (`Ctrl+Z` / `Ctrl+Y`) with dedicated buttons, allowing non-destructive annotation edits.
- **✏️ Freehand Drawing & Pen:** Sign documents or make hand-drawn notes directly on the page with customizable colors, line widths, and custom hex color chooser.
- **🖍️ Text Markup Tools (Highlight, Underline, Strikeout):** Mark text sections and document blocks with yellow highlights, blue underlines, or red strikethroughs.
- **⬛ True Visual & Search Redaction:** Permanently redact sensitive information:
  - **Visual Redactor:** Draw black-out boxes over any region of the document.
  - **Keyword Search & Redact:** Automatically search for terms (e.g. SSNs, confidential names) across all pages and scrub both text streams and rasterized image pixels (`PDF_REDACT_IMAGE_PIXELS`).
- **📋 Copy Page Text & Batch Export:** Instant 1-click extraction of the current page's text to the clipboard, or export full document text across all pages into a `.txt` file.
- **📑 AcroForm Detection & Interactive Form Filling:** Inspects documents for interactive fillable PDF forms, opens an organized form modal to enter values, and burns them directly into form fields.
- **📝 Click-to-Place Text:** Click anywhere on the rendered PDF page to place customized text annotations at exact coordinates with font size controls.
- **🖋️ Signature & Stamp Placement:** Browse your signature image (PNG/JPG) and click to stamp it onto the document with auto-scaling.
- **💾 Flatten & Save:** Export clean, professional annotated PDFs with all drawings, signatures, markups, and texts embedded permanently.
- **⚡ Batch PDF Utilities:**
  - **Merge:** Reorder and combine multiple PDFs into a single document.
  - **Split / Extract:** Burst into individual pages or extract custom ranges (`e.g. 1-3, 5`).
  - **Rotate:** 90°, 180°, or 270° clockwise page rotation.
  - **Images ↔ PDF:** Convert photo collections into clean PDFs, or render PDF pages into high-res PNG/JPGs.
  - **PDF Compressor:** Downscale embedded high-res images and deflate streams for email upload limits.
  - **Encryption / Decryption:** AES-256 password protection and password removal.

---

### 🎬 2. Video Studio with Timeline, Waveform & Audio Tools
- **⚡ Hardware Acceleration:** Automatically probes for NVIDIA NVENC (`h264_nvenc`), Intel QuickSync (`h264_qsv`), and AMD AMF (`h264_amf`) hardware encoders with a live UI status badge, falling back safely to CPU `libx264`.
- **🎬 Multi-Clip Timeline Sequence Builder:**
  - Queue multiple trimmed segments from different video files with `+ Add Cut to Sequence`.
  - Reorder clips with `▲ Up` / `▼ Down` and clear the sequence queue.
  - Stitch the sequence into a unified MP4 (`🎬 Stitch Sequence`) with automatic resolution & aspect ratio normalization (`1280x720` letterboxing/pillarboxing) and synchronized 44.1kHz stereo audio.
- **🎨 Cinematic LUT & Color Grading Presets:** One-click studio grading filters:
  - *Cinematic Teal & Orange* (Blockbuster color grade)
  - *70s Vintage Film* (Warm faded nostalgic aesthetic)
  - *B&W Noir High-Contrast* (Dramatic silver screen look)
  - *Vibrant Pop / Saturation Boost* (Social media vividness)
  - *Cyberpunk Neon Blue & Magenta* (Futuristic synthwave tint)
- **📊 Interactive Audio Waveform Display:** FFmpeg mono 16-bit PCM amplitude decoding rendered as an interactive timeline waveform canvas with click-to-seek navigation.
- **Real-Time Video Screen:** Low-latency frame rendering using high-speed FFmpeg pipes directly onto the screen.
- **Timeline Scrubber:** Smooth slider scrubbing through the entire video with live timestamp counters (`00:04.2 / 00:30.0`).
- **Visual In/Out Range Highlight:** Set In (`[ In`) and Out (`Out ]`) markers with accent-colored highlighted cut regions and duration calculation (`Cut: 00:02.5 ➔ 00:14.0 | Duration: 11.5s`).
- **⌨️ Pro Keyboard Shortcuts:**
  - `Space`: Play / Pause toggle
  - `Left` / `Right`: Frame step (0.5s)
  - `Shift + Left` / `Shift + Right`: Fast seek (2.0s)
  - `I`: Set In cut marker at playhead
  - `O`: Set Out cut marker at playhead
  - `Home` / `End`: Jump to start / end of video
- **💬 Subtitle Burning (.srt / .ass):** Burn subtitles permanently into video frames with configurable font size, text color, outline width, and vertical position.
- **🌅 Fade Transitions:** Smooth video fade-in from black and fade-out to black with synchronized audio volume fading.
- **✨ Crossfade Dissolve:** Seamlessly merge clips using `xfade=transition=dissolve` with synchronized `acrossfade` audio crossfading.
- **Instant Lossless Cut:** Instant clip trimming without re-encoding using direct stream copy (`-c copy`).
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
- **🔍 Smart Super-Resolution Upscaling:** Multi-pass progressive Lanczos magnification with edge-directed unsharp masking and adaptive local contrast enhancement for crisp 2x enlargements without blur or artifacts.
- **📐 Fixed Aspect Ratio Crop Presets:** Interactive crop tool with one-click aspect ratio locking (`Free`, `1:1`, `16:9`, `9:16`, `4:3`, `3:2`) and dynamic box re-centering.
- **Current Dimension Indicator:** Displays original resolution and file size upon loading (`Current Size: 1920 × 1080 px (1.8 MB)`).
- **Interactive Dimension Pre-fills:** Automatically populates `Width` and `Height` input boxes for quick adjustments.
- **Proportional Auto-Sync:** When **Lock Aspect Ratio** is active, editing the `Width` automatically updates the `Height` proportionally (and vice versa).
- **🖼️ Canvas Padding & Border:** Expand canvas area with uniform borders and custom color chooser for social media mockups and frames.
- **🔘 Rounded Corners & Soft Drop Shadow:** Add custom corner radiuses with alpha transparency and soft Gaussian blurred drop shadows.
- **⚡ Squoosh-Style Live Size Estimator:** Instant file size readout that updates live as you drag the quality slider or change formats.
- **🎨 Dominant Color Palette Extraction:** Automatically detects dominant hex color swatches with 1-click copy-to-clipboard functionality.
- **🏷️ Batch Rename with Tokens:** Format bulk output filenames using pattern tokens (`{name}_{index:03d}_{width}x{height}`) with live pattern preview.
- **🌡️ Color Temperature Tuning:** Adjust image warmth (-100 cool/blue to +100 warm/amber) via vectorized NumPy channel scaling.
- **📥 Drag & Drop Support:** Drag and drop image files directly onto the app window.
- **One-Click Platform Presets:**
  - Instagram Story / Reel (`1080x1920`)
  - Instagram Post Square (`1080x1080`)
  - YouTube Thumbnail (`1280x720`)
  - Passport Photo (`600x600`)
  - Twitter / X Header (`1500x500`)
  - LinkedIn Profile Banner (`1584x396`) & Post (`1200x627`)
  - Pinterest Pin (`1000x1500`)
  - Facebook Cover (`820x312`)
  - OpenGraph / Twitter Card (`1200x630`)
  - Discord Avatar (`128x128`) & Banner (`600x240`)
  - TikTok Video Cover (`1080x1920`)
  - iOS App Store Icon (`1024x1024`)
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
1. Go to the [Releases Page](https://github.com/krrishramsaran/omnitool/releases/latest).
2. Download **`OmniTool-v1.1.0-Windows.zip`**.
3. Extract the folder and directly double-click:
   ```cmd
   OmniTool.exe
   ```
   *No Python installation or terminal setup required.*

### Option 2: Run with Launcher Script
1. Download **`OmniTool-Windows.zip`** from [Latest Releases](https://github.com/krrishramsaran/omnitool/releases/latest).
2. Extract the folder and double-click:
   ```cmd
   run_app.bat
   ```

### Option 3: Clone with Git
```powershell
# Clone the repository
git clone https://github.com/krrishramsaran/omnitool.git

# Enter the project directory
cd omnitool

# Launch the application
run_app.bat
```

### Option 4: Manual Developer Setup
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
