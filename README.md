# Music Bio

Music Bio показывает текущий трек Яндекс Музыки и синхронизированную строку
текста в Bio профиля Telegram.

## Возможности

- получение активного трека через Windows GSMTC;
- синхронизированный текст в формате LRC;
- лимит Bio 70 или 140 символов в зависимости от Telegram Premium;
- восстановление исходного Bio после остановки музыки или выхода;
- кэширование загруженных текстов;
- тестовый режим без подключения к Telegram;
- настройка формата Bio через командную строку.

## Требования

- Windows 10 или Windows 11;
- Python 3.11 или 3.12;
- Telegram API ID и API Hash с [my.telegram.org](https://my.telegram.org);
- токен Яндекс Музыки, если нужен синхронизированный текст.

Токен Яндекс Музыки не требуется при запуске с `--no-lyrics`.

## Установка

```powershell
git clone https://github.com/uns1d/music-bio.git
cd music-bio
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

Скопируйте пример настроек:

```powershell
Copy-Item .env.example .env
```

Откройте `.env` и укажите свои данные:

```dotenv
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=your_telegram_api_hash_here
YANDEX_MUSIC_TOKEN=your_yandex_music_token_here
```

Файлы `.env` и `*.session` содержат секретные данные и уже добавлены в
`.gitignore`.

## Подключение через MTProxy

Если Telegram доступен напрямую, оставьте переменные `TELEGRAM_PROXY_*`
пустыми.

Для ссылки вида:

```text
tg://proxy?server=proxy.example.com&port=443&secret=your_mtproxy_secret
```

настройки в `.env` будут выглядеть так:

```dotenv
TELEGRAM_PROXY_HOST=proxy.example.com
TELEGRAM_PROXY_PORT=443
TELEGRAM_PROXY_SECRET=your_mtproxy_secret
```

Не публикуйте настоящий адрес и секрет прокси. После изменения `.env`
перезапустите приложение.

## Запуск

Сначала проверьте, видит ли Windows медиасессию Яндекс Музыки:

```powershell
python -m music_bio --list-sessions
```

Затем запустите безопасную проверку без Telegram:

```powershell
python -m music_bio --dry-run --no-lyrics
```

Обычный запуск:

```powershell
python -m music_bio
```

При первом подключении Telethon запросит номер телефона и код подтверждения.
После авторизации рядом с проектом появится файл `music_session.session`.

## Параметры

- `--list-sessions` — показать доступные медиасессии Windows;
- `--dry-run` — не подключаться к Telegram;
- `--no-lyrics` — не обращаться к API Яндекс Музыки;
- `--no-restore` — не восстанавливать исходное Bio при выходе;
- `--debug` — включить подробные логи;
- `--interval SEC` — изменить интервал проверки медиасессии;
- `--min-bio-interval SEC` — изменить минимальный интервал обновления Bio;
- `--source-hint HINT` — добавить идентификатор медиаприложения;
- `--template TEMPLATE` — изменить шаблон Bio.

Пример собственного шаблона:

```powershell
python -m music_bio --template "🎵 {artist} — {title} | {lyric}"
```

## Веб-версия Яндекс Музыки

По умолчанию отслеживается официальное приложение Яндекс Музыки. Для
веб-плеера можно добавить браузер:

```powershell
python -m music_bio --source-hint chrome
```

Windows сообщает только идентификатор браузера, поэтому другое активное медиа
из Chrome, включая YouTube, тоже может быть принято за Яндекс Музыку.

## Восстановление Bio

Исходное Bio считывается после подключения к Telegram. Скрипт возвращает его,
когда воспроизведение останавливается и при обычном завершении программы.

Восстановление нельзя гарантировать при принудительном завершении через
диспетчер задач, сбое системы или отключении питания: в этих случаях код
завершения может не выполниться.

## Проверка проекта

```powershell
pip install -e ".[dev]"
python -m compileall src tests
ruff check .
ruff format --check .
pytest
```

## Лицензия

MIT. Подробности находятся в файле [LICENSE](LICENSE).
