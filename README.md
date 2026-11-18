# YouTube Downloader

A graphical interface for downloading individual YouTube videos and playlists
with `yt-dlp`. The project includes a local desktop interface built with
Tkinter/CustomTkinter and can be packaged as a single Windows executable.

## 🚀 Features

- 🖥️ **Graphical interface**: Paste multiple links and track progress in a
native Windows window.
- 📄 **Automatic link loading**: Imports links from `links.txt`, when present.
- 📁 **Output directory**: Choose any directory through the interface.
- 🎬 **Format selection**: Download videos as `.mp4` or audio directly as
`.m4a`.
- 🖼️ **Audio Cover Art**: Embeds the video's thumbnail as the M4A cover.
- 🗂️ **Automatic Playlist Organization**: Saves playlists into dedicated
subfolders named after the playlist with track numbering.
- ⚡ **Concurrent downloads**: Processes up to three links simultaneously.
- 📦 **Standalone executable**: Can be distributed as a single `.exe` with
FFmpeg included.

## 🛠️ Prerequisites

### 1. Python 3.15+

Make sure you have Python installed on your system.

### 2. FFmpeg (Required)

`yt-dlp` requires **FFmpeg** to merge high-quality video and audio streams and
to embed thumbnails in audio files. Audio downloads use M4A directly and do not
convert to MP3.

For authenticated downloads, the script uses `cookies.txt` in the Netscape
cookie format when that file exists. Otherwise, it reads cookies from the
default Chrome profile. Chrome may need to be closed so `yt-dlp` can copy its
cookie database.

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

### Graphical interface

Run the interface during development:

```powershell
uv run interface.py
```

Add links directly to the text box, choose the format and output directory, and
click **Start downloads**.

### Using a `links.txt` file

1. Create a file named `links.txt` in the same directory as the script.
2. Add YouTube links (one per line):

```text
https://www.youtube.com/watch?v=EXAMPLE1
https://www.youtube.com/playlist?list=EXAMPLE2
```

1. Run the interface:

```powershell
uv run interface.py
```

Links can also be provided to the legacy `main.py` script:

```powershell
uv run main.py
```

## Packaging the executable

On Windows, run:

```powershell
uv run pyinstaller --noconsole --onefile --clean --collect-all customtkinter --add-binary "C:\path\to\ffmpeg.exe;." interface.py
```

The generated executable is placed at `dist\interface.exe`. The `build\` and
`dist\` directories are listed in `.gitignore`.

### Authentication Cookies

You can export your YouTube cookies as a Netscape-format `cookies.txt` and put
it in the same directory as `main.py`. The file must contain the complete
cookie export, not just the value of `LOGIN_INFO`. If `cookies.txt` is absent,
the downloader uses the default Chrome profile automatically through `yt-dlp`.
If Chrome is open and its cookie database is locked, close Chrome before
running the downloader.

If a video cannot be downloaded, `yt-dlp` reports the error and continues with
the next video.

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
