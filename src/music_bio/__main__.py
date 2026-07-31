import sys


def main() -> int | None:
    cli_flags = {
        "--cli",
        "--debug",
        "--dry-run",
        "--interval",
        "--list-sessions",
        "--min-bio-interval",
        "--no-lyrics",
        "--no-restore",
        "--source",
        "--template",
    }
    if any(argument in cli_flags for argument in sys.argv[1:]):
        if "--cli" in sys.argv:
            sys.argv.remove("--cli")
        from music_bio.app import main as cli_main

        cli_main()
        return None

    from music_bio.gui_main import main as gui_main

    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
