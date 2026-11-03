from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
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

# Dicionário dinâmico de opções
ydl_opts = {}

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


def download_link(link: str) -> Exception | None:
    print(f"\n🚀 Processando: {link}")
    try:
        with yt_dlp.YoutubeDL(params=ydl_opts) as ydl:  # type: ignore
            ydl.download([link])
        return None
    except Exception as e:
        print(f"❌ Erro ao baixar o link {link}: {e}")
        return e


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
