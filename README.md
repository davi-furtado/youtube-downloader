# YouTube Downloader

Interface gráfica para baixar vídeos individuais e playlists do YouTube com
`yt-dlp`. O projeto inclui uma interface web local em Tkinter/CustomTkinter e
pode ser empacotado como um único executável para Windows.

## 🚀 Features

- 🖥️ **Interface gráfica**: Cole vários links e acompanhe o progresso em uma
janela nativa no Windows.
- 📄 **Leitura automática**: Importa links de `links.txt`, quando presente.
- 📁 **Pasta de destino**: Escolha qualquer diretório por meio da interface.
- 🎬 **Seleção de formato**: Baixe vídeos em `.mp4` ou áudio direto em `.m4a`.
- 🖼️ **Audio Cover Art**: Embeds the video's thumbnail as the M4A cover.
- 🗂️ **Automatic Playlist Organization**: Saves playlists into dedicated
subfolders named after the playlist with track numbering.
- ⚡ **Downloads concorrentes**: Processa até três links simultaneamente.
- 📦 **Executável standalone**: Pode ser distribuído como um único `.exe`,
com FFmpeg incluído.

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

### Interface gráfica

Execute a interface durante o desenvolvimento:

```powershell
uv run interface.py
```

Adicione os links diretamente na caixa de texto, escolha o formato e a pasta de
destino e clique em **Iniciar downloads**.

### Usando um arquivo `links.txt`

1. Create a file named `links.txt` in the same directory as the script.
2. Add YouTube links (one per line):

```text
https://www.youtube.com/watch?v=EXAMPLE1
https://www.youtube.com/playlist?list=EXAMPLE2
```

1. Execute a interface:

```powershell
uv run interface.py
```

Os links também podem ser fornecidos ao script antigo `main.py`:

```powershell
uv run main.py
```

## Empacotar o executável

No Windows, execute:

```powershell
.venv\Scripts\pyinstaller.exe --noconsole --onefile --clean --collect-all customtkinter --add-binary "C:\caminho\para\ffmpeg.exe;." interface.py
```

O executável gerado fica em `dist\interface.exe`. As pastas `build\` e `dist\`
estão no `.gitignore`.

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
