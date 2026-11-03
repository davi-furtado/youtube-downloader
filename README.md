# 📥 YouTube Downloader with yt-dlp & Questionary

A simple and interactive Python script to download individual YouTube videos or
entire playlists with quality selection and support for reading links via a file
or terminal input.

## 🚀 Features

- 📄 **Automatic Link Detection**: Reads video and playlist links directly from
a `links.txt` file (if present).
- 💬 **Interactive Mode**: Prompts you to paste links via the terminal if
`links.txt` is not found.
- 📁 **Custom Directory**: Allows you to choose the save location (defaults to `downloads/`).
- 🎬 **Format & Quality Selection**: Choose between video (`.mp4`) or direct
audio (`.m4a`) downloads.
- 🖼️ **Audio Cover Art**: Embeds the video's thumbnail as the M4A cover.
- 🗂️ **Automatic Playlist Organization**: Saves playlists into dedicated
subfolders named after the playlist with track numbering.
- ⚡ **Concurrent Downloads**: Processes up to three links simultaneously.

## 🛠️ Prerequisites

### 1. Python 3.15+

Make sure you have Python installed on your system.

### 2. FFmpeg (Required)

`yt-dlp` requires **FFmpeg** to merge high-quality video and audio streams and
to embed thumbnails in audio files. Audio downloads use M4A directly and do not
convert to MP3.

- **Windows (via Winget):**
  ```powershell
  winget install FFmpeg
  ```
- **Linux (Ubuntu/Debian):**
  ```bash
  sudo apt update && sudo apt install ffmpeg
  ```
- **macOS (via Homebrew):**
  ```bash
  brew install ffmpeg
  ```

## 📦 Installation

1. Clone or download this repository:

```bash
git clone https://github.com/davi-furtado/youtube-downloader.git
cd youtube-downloader
```

1. Install the required Python dependencies:

```bash
uv sync
```

## 🖥️ Usage

### Option A: Using a `links.txt` File

1. Create a file named `links.txt` in the same directory as the script.
2. Add YouTube links (one per line):

```text
https://www.youtube.com/watch?v=EXAMPLE1
https://www.youtube.com/playlist?list=EXAMPLE2
```

1. Run the script:

```bash
uv run main.py
```

### Option B: Interactive Input

1. If no `links.txt` file is found, simply run the script:

```bash
uv run main.py
```

1. Paste your links one by one.
2. Press **Enter** on an empty input field to finish adding links.

## 📂 Output File Structure

Downloaded files will be organized as follows:

- **Single Videos:**
  `{chosen_directory}/{video_title}.{ext}`
- **Playlists:**
  `{chosen_directory}/{playlist_title}/{track_number}. {video_title}.{ext}`

Audio files use the `.m4a` format and include the video's thumbnail as cover art.

## 📜 License

This project is licensed under the _MIT License_. See the [LICENSE](LICENSE)
file for details.
