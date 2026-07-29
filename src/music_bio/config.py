import argparse
import os

from dotenv import load_dotenv

from music_bio.models import Settings


def parse_args(args: list[str] | None = None) -> tuple[argparse.Namespace, Settings]:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="music-bio",
        description="Текущий трек Яндекс Музыки и строка LRC в Telegram Bio.",
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="Показать активные медиасессии Windows и завершить работу.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Выводить Bio в консоль без подключения к Telegram.",
    )
    parser.add_argument(
        "--no-lyrics",
        action="store_true",
        help="Не загружать текст трека.",
    )
    parser.add_argument(
        "--no-restore",
        action="store_true",
        help="Не восстанавливать исходное Bio при завершении.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Включить подробные логи.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        metavar="SEC",
        help="Интервал проверки медиасессии (по умолчанию: 3 секунды).",
    )
    parser.add_argument(
        "--min-bio-interval",
        type=float,
        default=12.0,
        metavar="SEC",
        help="Минимальный интервал обновления Bio (по умолчанию: 12 секунд).",
    )
    parser.add_argument(
        "--source-hint",
        action="append",
        dest="source_hints",
        metavar="HINT",
        help="Дополнительная часть App ID медиаприложения.",
    )
    parser.add_argument(
        "--template",
        default="🎧 {artist} — {title} | {lyric}",
        metavar="TEMPLATE",
        help="Шаблон Bio с полями {artist}, {title} и {lyric}.",
    )

    parsed = parser.parse_args(args)

    raw_api_id = os.getenv("TELEGRAM_API_ID", "")
    api_id = int(raw_api_id) if raw_api_id.isdigit() else 0
    hints = ["yandexmusic", "yandex.music", "yandex_music"]

    if parsed.source_hints:
        hints.extend(hint.casefold() for hint in parsed.source_hints)

    settings = Settings(
        api_id=api_id,
        api_hash=os.getenv("TELEGRAM_API_HASH", ""),
        yandex_token=os.getenv("YANDEX_MUSIC_TOKEN"),
        min_bio_interval=max(1.0, parsed.min_bio_interval),
        check_interval=max(1.0, parsed.interval),
        template=parsed.template,
        dry_run=parsed.dry_run,
        no_lyrics=parsed.no_lyrics,
        no_restore=parsed.no_restore,
        source_hints=list(dict.fromkeys(hints)),
    )

    if not parsed.list_sessions:
        settings.validate()

    return parsed, settings
