from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import questionary
import yt_dlp

links_file = Path("links.txt")
links: list[str] = []

# 1. Check for links.txt or collect links interactively
if links_file.exists():
    print("📁 Found 'links.txt'. Reading links...")
    with open(links_file) as f:
        links = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]
else:
    print("⚠️ 'links.txt' not found. Enter links interactively.")
    while True:
        link = questionary.text(
            "Enter a YouTube video or playlist link, or press Enter to finish:"
        ).ask()

        if not link or not link.strip():
            break
        links.append(link.strip())

if not links:
    print("❌ No links provided. Exiting.")
    exit(1)


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


unique_links: list[str] = []
seen_link_ids: set[str] = set()
for link in links:
    normalized = normalize_link(link)
    identity = link_identity(normalized)
    if identity not in seen_link_ids:
        seen_link_ids.add(identity)
        unique_links.append(normalized)

if len(unique_links) != len(links):
    print(f"ℹ️ Removed {len(links) - len(unique_links)} duplicate link(s).")
links = unique_links

# 2. Ask where files should be saved
output_dir_input = questionary.text(
    "Where should files be saved? (Press Enter to use the default 'downloads' directory):"
).ask()

# Set the directory (use 'downloads' when empty)
if output_dir_input and output_dir_input.strip():
    output_dir = Path(output_dir_input.strip())
else:
    output_dir = Path("downloads")

# Ensure the output directory exists
output_dir.mkdir(parents=True, exist_ok=True)

# 3. Ask for the desired download format
download_format = questionary.select(
    "Choose the download format:",
    choices=["Audio [M4A]", "Video [MP4]"],
).ask()

if not download_format:
    print("❌ No option selected. Exiting.")
    exit(1)

conflict_policy = questionary.select(
    "What should happen when the video or file already exists?",
    choices=[
        "Continue downloads and skip existing files",
        "Replace existing files",
        "Ask individually",
    ],
).ask()

if not conflict_policy:
    print("❌ No option selected. Exiting.")
    exit(1)

# Dynamic options dictionary
manual_cookies = Path("cookies.txt")
ydl_opts = {
    # A video failure does not interrupt the remaining playlist items.
    "ignoreerrors": True,
}

if manual_cookies.exists():
    ydl_opts["cookiefile"] = str(manual_cookies)
else:
    ydl_opts["cookiesfrombrowser"] = ("chrome",)

if download_format == "Video [MP4]":
    ydl_opts.update(
        {
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
        }
    )
else:  # Best audio quality without conversion
    ydl_opts.update(
        {
            "format": "bestaudio[ext=m4a]/bestaudio[ext=mp4]",
            "writethumbnail": True,
            "postprocessors": [
                {
                    "key": "EmbedThumbnail",
                }
            ],
        }
    )

# Directory and filename template using the dynamically selected directory
ydl_opts["outtmpl"] = {
    "default": (
        f"{output_dir}\\%(playlist_title|.)s\\"
        "%(playlist_index&{}. |)s%(title)s.%(ext)s"
    ),
    "pl_thumbnail": "",
}

MAX_CONCURRENT_DOWNLOADS = 3
archive_name = (
    ".yt-dlp-audio.txt"
    if download_format == "Audio [M4A]"
    else ".yt-dlp-video.txt"
)
DOWNLOAD_ARCHIVE = output_dir / archive_name


def read_download_archive() -> set[str]:
    if not DOWNLOAD_ARCHIVE.exists():
        return set()
    return {
        line.strip()
        for line in DOWNLOAD_ARCHIVE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def iter_video_entries(info: dict) -> list[dict]:
    if info.get("_type") != "playlist":
        return [info]
    return [entry for entry in (info.get("entries") or []) if entry]


def entry_has_existing_file(ydl: yt_dlp.YoutubeDL, entry: dict) -> bool:
    filename = Path(ydl.prepare_filename(entry))  # type: ignore
    if not filename.name:
        return False

    candidates = {filename}
    for extension in (".mp4", ".m4a", ".webm", ".mp3"):
        candidates.add(filename.with_suffix(extension))

    return any(candidate.exists() for candidate in candidates)


def link_has_conflict(link: str) -> bool:
    probe_opts = {
        **ydl_opts,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    archive = read_download_archive()

    with yt_dlp.YoutubeDL(params=probe_opts) as ydl:  # type: ignore
        info = ydl.extract_info(link, download=False)
        for entry in iter_video_entries(info):  # type: ignore
            archive_id = ydl._make_archive_id(entry)  # type: ignore
            if archive_id in archive or entry_has_existing_file(ydl, entry):
                return True
    return False


def prepare_link_decisions() -> dict[str, str]:
    if conflict_policy != "Ask individually":
        return {}

    decisions: dict[str, str] = {}
    for link in links:
        try:
            has_conflict = link_has_conflict(link)
        except Exception as error:
            print(f"⚠️ Could not check {link}: {error}")
            has_conflict = False

        if not has_conflict:
            decisions[link] = "continue"
            continue

        decision = questionary.select(
            f"Downloads already exist for this link:\n{link}",
            choices=[
                "Continue and skip existing files",
                "Replace existing files",
                "Skip this link",
            ],
        ).ask()
        if not decision:
            print("❌ No option selected. Exiting.")
            exit(1)
        decisions[link] = {
            "Continue and skip existing files": "continue",
            "Replace existing files": "replace",
            "Skip this link": "skip",
        }[decision]
    return decisions


def download_link(link: str) -> Exception | None:
    print(f"\n🚀 Processing: {link}")
    try:
        default_decision = (
            "replace"
            if conflict_policy == "Replace existing files"
            else "continue"
        )
        decision = link_decisions.get(link, default_decision)
        if decision == "skip":
            print(f"⏭️ Skipped: {link}")
            return None

        download_opts = ydl_opts.copy()
        download_opts["overwrites"] = decision == "replace"
        if decision == "continue":
            download_opts["download_archive"] = str(DOWNLOAD_ARCHIVE)
        else:
            download_opts.pop("download_archive", None)

        with yt_dlp.YoutubeDL(params=download_opts) as ydl:  # type: ignore
            ydl.download([link])
        return None
    except Exception as e:
        print(f"❌ Error downloading link {link}: {e}")
        return e


link_decisions = prepare_link_decisions()

# 4. Download in parallel while limiting concurrency
errors: list[tuple[str, Exception]] = []
worker_count = min(MAX_CONCURRENT_DOWNLOADS, len(links))

with ThreadPoolExecutor(max_workers=worker_count) as executor:
    futures = {executor.submit(download_link, link): link for link in links}
    for future in as_completed(futures):
        error = future.result()
        if error is not None:
            errors.append((futures[future], error))

if errors:
    print(f"\n❌ {len(errors)} download(s) failed.")
    exit(1)

print("\n✨ All downloads completed!")
