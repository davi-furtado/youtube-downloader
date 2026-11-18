import queue
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import filedialog
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import customtkinter as ctk
import yt_dlp


def app_directory() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def ffmpeg_location() -> str | None:
    candidates = [
        app_directory() / "ffmpeg.exe",
        app_directory() / "bin" / "ffmpeg.exe",
    ]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys._MEIPASS) / "ffmpeg.exe")

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    executable = shutil.which("ffmpeg")
    return executable


def normalize_link(link: str) -> str:
    parsed = urlsplit(link.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in {"feature", "pp", "si"}
    ]
    query.sort()
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            urlencode(query),
            "",
        )
    )


def link_identity(link: str) -> str:
    parsed = urlsplit(link)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    host = parsed.netloc.lower().removeprefix("www.")
    path_parts = [part for part in parsed.path.split("/") if part]

    if query.get("v"):
        return f"youtube:{query['v']}"
    if host == "youtu.be" and path_parts:
        return f"youtube:{path_parts[0]}"
    if path_parts and path_parts[0] in {"embed", "shorts"} and len(path_parts) > 1:
        return f"youtube:{path_parts[1]}"
    return normalize_link(link)


class DownloaderApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("YouTube Downloader")
        self.geometry("820x680")
        self.minsize(720, 600)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        self.stop_requested = threading.Event()
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()

        ctk.CTkLabel(
            self,
            text="YouTube Downloader",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 12), sticky="w")

        ctk.CTkLabel(self, text="Links (one per line):").grid(
            row=1, column=0, padx=24, sticky="w"
        )
        mono_font = ctk.CTkFont(family="Consolas", size=13)
        self.links_box = ctk.CTkTextbox(self, height=150, font=mono_font)
        self.links_box.grid(row=2, column=0, padx=24, pady=(6, 14), sticky="nsew")

        options = ctk.CTkFrame(self)
        options.grid(row=3, column=0, padx=24, pady=(0, 14), sticky="ew")
        options.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(options, text="Format").grid(row=0, column=0, padx=12, pady=10, sticky="w")
        self.format_var = ctk.StringVar(value="Video MP4")
        ctk.CTkSegmentedButton(
            options,
            values=["Video MP4", "Audio M4A"],
            variable=self.format_var,
        ).grid(row=0, column=1, padx=12, pady=10, sticky="ew")

        ctk.CTkLabel(options, text="Existing files").grid(
            row=1, column=0, padx=12, pady=(0, 10), sticky="w"
        )
        self.conflict_var = ctk.StringVar(value="Continue and skip")
        ctk.CTkSegmentedButton(
            options,
            values=["Continue and skip", "Replace"],
            variable=self.conflict_var,
        ).grid(row=1, column=1, padx=12, pady=(0, 10), sticky="ew")

        destination = ctk.CTkFrame(self)
        destination.grid(row=4, column=0, padx=24, pady=(0, 14), sticky="ew")
        destination.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(destination, text="Save to").grid(row=0, column=0, padx=12, pady=10)
        default_output = Path.home() / "Downloads" / "YouTube Downloader"
        self.output_var = ctk.StringVar(value=str(default_output))
        ctk.CTkEntry(destination, textvariable=self.output_var).grid(
            row=0, column=1, padx=(0, 8), pady=10, sticky="ew"
        )
        ctk.CTkButton(destination, text="Choose", width=90, command=self.choose_directory).grid(
            row=0, column=2, padx=(0, 12), pady=10
        )

        actions = ctk.CTkFrame(self)
        actions.grid(row=5, column=0, padx=24, pady=(0, 10), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)

        self.download_button = ctk.CTkButton(
            actions,
            text="Start downloads",
            height=42,
            command=self.start_download,
        )
        self.download_button.grid(row=0, column=0, padx=12, pady=12, sticky="ew")

        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=6, column=0, padx=24, pady=(0, 6), sticky="ew")
        self.progress.set(0)

        self.status = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status.grid(row=7, column=0, padx=24, pady=(0, 6), sticky="ew")

        self.log_box = ctk.CTkTextbox(self, height=170)
        self.log_box.grid(row=8, column=0, padx=24, pady=(0, 20), sticky="nsew")
        self.log_box.configure(state="disabled")

        self.load_links_file()
        self.poll_events()

    def choose_directory(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_var.get())
        if selected:
            self.output_var.set(selected)

    def load_links_file(self) -> None:
        links_file = app_directory() / "links.txt"
        if not links_file.exists():
            links_file = Path.cwd() / "links.txt"
        if links_file.exists():
            links = [
                line.strip()
                for line in links_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            ]
            self.links_box.insert("1.0", "\n".join(links))

    def append_log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message.rstrip() + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def poll_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "log":
                    self.append_log(value)
                elif event == "status":
                    self.status.configure(text=value)
                elif event == "progress":
                    self.progress.set(float(value))
        except queue.Empty:
            pass
        self.after(100, self.poll_events)

    def set_busy(self, busy: bool) -> None:
        self.download_button.configure(
            state="disabled" if busy else "normal",
            text="Downloads in progress..." if busy else "Start downloads",
        )

    def start_download(self) -> None:
        raw_links = self.links_box.get("1.0", "end").splitlines()

        unique_links: list[str] = []
        seen: set[str] = set()
        for raw_link in raw_links:
            normalized = normalize_link(raw_link)
            if not normalized:
                continue
            identity = link_identity(normalized)
            if identity not in seen:
                seen.add(identity)
                unique_links.append(normalized)

        if not unique_links:
            self.append_log("Enter at least one link.")
            return

        output_dir = Path(self.output_var.get().strip()).expanduser()
        if not str(output_dir):
            output_dir = Path.home() / "Downloads" / "YouTube Downloader"

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.append_log(f"Could not create the output directory: {error}")
            return

        self.stop_requested.clear()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.progress.set(0)
        self.set_busy(True)

        threading.Thread(
            target=self.run_downloads,
            args=(unique_links, output_dir),
            daemon=True,
        ).start()

    def run_downloads(self, links: list[str], output_dir: Path) -> None:
        is_audio = self.format_var.get() == "Audio M4A"
        replace = self.conflict_var.get() == "Replace"

        cookies_file = app_directory() / "cookies.txt"
        if not cookies_file.exists():
            cookies_file = Path.cwd() / "cookies.txt"

        ydl_opts: dict[str, object] = {
            "ignoreerrors": True,
            "continuedl": not replace,
            "overwrites": replace,
        }

        if cookies_file.exists():
            ydl_opts["cookiefile"] = str(cookies_file)
        else:
            ydl_opts["cookiesfrombrowser"] = ("chrome",)

        ffmpeg = ffmpeg_location()
        if ffmpeg:
            ydl_opts["ffmpeg_location"] = ffmpeg

        if is_audio:
            ydl_opts.update(
                {
                    "format": "bestaudio[ext=m4a]/bestaudio[ext=mp4]",
                    "writethumbnail": True,
                    "postprocessors": [{"key": "EmbedThumbnail"}],
                }
            )
        else:
            ydl_opts.update(
                {
                    "format": "bestvideo+bestaudio/best",
                    "merge_output_format": "mp4",
                }
            )

        ydl_opts["outtmpl"] = {
            "default": str(output_dir / "%(playlist_title|.)s" / "%(playlist_index&{}. |)s%(title)s.%(ext)s"),
            "pl_thumbnail": "",
        }

        archive_name = ".yt-dlp-audio.txt" if is_audio else ".yt-dlp-video.txt"
        if not replace:
            ydl_opts["download_archive"] = str(output_dir / archive_name)

        class GuiLogger:
            def debug(self, message: str) -> None:
                if "[download]" in message or "[Merger]" in message:
                    self_send(message)

            def info(self, message: str) -> None:
                self_send(message)

            def warning(self, message: str) -> None:
                self_send(f"Warning: {message}")

            def error(self, message: str) -> None:
                self_send(f"Error: {message}")

        def self_send(message: str) -> None:
            self.events.put(("log", message))

        ydl_opts["logger"] = GuiLogger()
        ydl_opts["progress_hooks"] = [self.progress_hook]

        errors: list[str] = []
        completed = 0
        worker_count = min(3, len(links))

        def download(link: str) -> str | None:
            if self.stop_requested.is_set():
                return None
            self.events.put(("log", f"\nProcessing: {link}"))
            try:
                with yt_dlp.YoutubeDL(params=ydl_opts.copy()) as ydl:
                    ydl.download([link])
                return None
            except Exception as error:
                return f"{link}: {error}"

        self.events.put(("status", f"Downloading {len(links)} item(s)..."))

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {executor.submit(download, link): link for link in links}
            for future in as_completed(futures):
                error = future.result()
                completed += 1
                if error:
                    errors.append(error)
                    self.events.put(("log", f"Failed: {error}"))
                self.events.put(("progress", str(completed / len(links))))
                self.events.put(("status", f"Completed: {completed}/{len(links)}"))

        if errors:
            self.events.put(("status", f"{len(errors)} download(s) failed"))
            self.events.put(("log", "Check the errors above and try again."))
        else:
            self.events.put(("status", "All downloads completed"))
            self.events.put(("log", "Downloads completed successfully."))

        self.after(0, lambda: self.set_busy(False))

    def progress_hook(self, data: dict[str, object]) -> None:
        status = data.get("status")
        if status == "downloading":
            filename = data.get("filename")
            downloaded = data.get("_percent_str")
            if filename and downloaded:
                self.events.put(("status", f"Downloading {Path(str(filename)).name}: {downloaded}"))
        elif status == "finished":
            self.events.put(("log", "Download complete; finalizing file..."))


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
