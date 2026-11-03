from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import questionary
import yt_dlp

links_file = Path("links.txt")
links: list[str] = []

# 1. Verifica a existência do arquivo links.txt ou coleta interativamente
if links_file.exists():
    print("📁 Arquivo 'links.txt' encontrado. Lendo os links...")
    with open(links_file) as f:
        links = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]
else:
    print("⚠️ Arquivo 'links.txt' não encontrado. Insira os links interativamente.")
    while True:
        link = questionary.text(
            "Digite o link do YouTube (vídeo ou playlist) ou pressione Enter para finalizar:"
        ).ask()

        if not link or not link.strip():
            break
        links.append(link.strip())

if not links:
    print("❌ Nenhum link fornecido. Encerrando o programa.")
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
    print(f"ℹ️ {len(links) - len(unique_links)} link(s) duplicado(s) removido(s).")
links = unique_links

# 2. Pergunta onde os arquivos devem ser salvos
output_dir_input = questionary.text(
    "Onde deseja salvar os arquivos? (Pressione Enter para usar a pasta padrão 'downloads'):"
).ask()

# Define o diretório (padrão 'downloads' se vazio)
if output_dir_input and output_dir_input.strip():
    output_dir = Path(output_dir_input.strip())
else:
    output_dir = Path("downloads")

# Garante que o diretório de destino existe
output_dir.mkdir(parents=True, exist_ok=True)

# 3. Pergunta o formato desejado do download
formato = questionary.select(
    "Escolha o formato de download:",
    choices=["Áudio [M4A]", "Vídeo [MP4]"],
).ask()

if not formato:
    print("❌ Nenhuma opção selecionada. Encerrando.")
    exit(1)

conflict_policy = questionary.select(
    "O que fazer quando o vídeo ou arquivo já existir?",
    choices=[
        "Continuar downloads e ignorar existentes",
        "Substituir arquivos existentes",
        "Perguntar individualmente",
    ],
).ask()

if not conflict_policy:
    print("❌ Nenhuma opção selecionada. Encerrando.")
    exit(1)

# Dicionário dinâmico de opções
ydl_opts = {
    "cookiefile": "cookies.txt",
}

if formato == "Vídeo [MP4]":
    ydl_opts.update(
        {
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
        }
    )
else:  # Melhor qualidade de áudio sem conversão
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

# Template de diretórios e nomes utilizando o diretório escolhido dinamicamente
ydl_opts["outtmpl"] = {
    "default": (
        f"{output_dir}\\%(playlist_title|.)s\\"
        "%(playlist_index&{}. |)s%(title)s.%(ext)s"
    ),
    "pl_thumbnail": "",
}

MAX_CONCURRENT_DOWNLOADS = 3
archive_name = ".yt-dlp-audio.txt" if formato == "Áudio [M4A]" else ".yt-dlp-video.txt"
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
    if conflict_policy != "Perguntar individualmente":
        return {}

    decisions: dict[str, str] = {}
    for link in links:
        try:
            has_conflict = link_has_conflict(link)
        except Exception as error:
            print(f"⚠️ Não foi possível verificar {link}: {error}")
            has_conflict = False

        if not has_conflict:
            decisions[link] = "continue"
            continue

        decision = questionary.select(
            f"Já existem downloads para este link:\n{link}",
            choices=[
                "Continuar e ignorar existentes",
                "Substituir os existentes",
                "Pular este link",
            ],
        ).ask()
        if not decision:
            print("❌ Nenhuma opção selecionada. Encerrando.")
            exit(1)
        decisions[link] = {
            "Continuar e ignorar existentes": "continue",
            "Substituir os existentes": "replace",
            "Pular este link": "skip",
        }[decision]
    return decisions


def download_link(link: str) -> Exception | None:
    print(f"\n🚀 Processando: {link}")
    try:
        default_decision = (
            "replace"
            if conflict_policy == "Substituir arquivos existentes"
            else "continue"
        )
        decision = link_decisions.get(link, default_decision)
        if decision == "skip":
            print(f"⏭️ Ignorado: {link}")
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
        print(f"❌ Erro ao baixar o link {link}: {e}")
        return e


link_decisions = prepare_link_decisions()

# 4. Executa os downloads em paralelo, limitando a quantidade simultânea
errors: list[tuple[str, Exception]] = []
worker_count = min(MAX_CONCURRENT_DOWNLOADS, len(links))

with ThreadPoolExecutor(max_workers=worker_count) as executor:
    futures = {executor.submit(download_link, link): link for link in links}
    for future in as_completed(futures):
        error = future.result()
        if error is not None:
            errors.append((futures[future], error))

if errors:
    print(f"\n❌ {len(errors)} download(s) falharam.")
    exit(1)

print("\n✨ Todos os downloads foram concluídos!")
