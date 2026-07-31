from music_bio.media import WindowsMediaMonitor


def test_official_yandex_music_app_is_allowed():
    monitor = WindowsMediaMonitor()

    assert monitor._matches_app_id("YandexMusic.exe")
    assert monitor._matches_app_id("ru.yandex.music.Desktop")


def test_generic_browsers_are_always_rejected():
    monitor = WindowsMediaMonitor(["chrome", "yandexmusic"])

    assert not monitor._matches_app_id("chrome.exe")
    assert not monitor._matches_app_id("msedge.exe")
    assert not monitor._matches_app_id("firefox.exe")


def test_unrelated_media_apps_are_rejected():
    monitor = WindowsMediaMonitor()

    assert not monitor._matches_app_id("vlc.exe")
    assert not monitor._matches_app_id("spotify.exe")
    assert not monitor._matches_app_id("youtube.exe")
