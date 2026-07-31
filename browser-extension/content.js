const ALLOWED_HOSTS = new Set(["music.yandex.ru", "music.yandex.com"]);
const DEFAULT_PORT = 8765;
const SEND_INTERVAL = 500;
const PAGE_ID = globalThis.crypto?.randomUUID?.()
  || `${Date.now()}-${Math.random().toString(36).slice(2)}`;

let lastFingerprint = "";
let lastSuccessfulSend = 0;
let pageTimeline = null;

window.addEventListener("message", (event) => {
  const payload = event.data;
  if (
    event.source !== window
    || !payload
    || payload.channel !== "music-bio-yandex-player"
  ) {
    return;
  }
  pageTimeline = {
    title: String(payload.title || ""),
    playing: Boolean(payload.playing),
    position: nonNegativeNumber(payload.position),
    duration: nonNegativeNumber(payload.duration),
    positionKnown: Boolean(payload.positionKnown),
    receivedAt: Date.now()
  };
});

function nonNegativeNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : 0;
}

function normalize(value) {
  return String(value || "").trim().toLocaleLowerCase();
}

function findActiveMedia() {
  return Array.from(document.querySelectorAll("audio, video"))
    .filter((element) => Number.isFinite(element.currentTime))
    .sort((left, right) => {
      const score = (element) => (
        (!element.paused && !element.ended ? 10000 : 0)
        + (Number.isFinite(element.duration) && element.duration > 0 ? 1000 : 0)
        + nonNegativeNumber(element.currentTime)
      );
      return score(right) - score(left);
    })[0] || null;
}

function parseClocks(value) {
  const clocks = [];
  const pattern = /(?:^|\D)(?:(\d+):)?([0-5]?\d):([0-5]\d)(?!\d)/g;
  for (const match of String(value || "").matchAll(pattern)) {
    clocks.push(
      Number(match[1] || 0) * 3600
      + Number(match[2]) * 60
      + Number(match[3])
    );
  }
  return clocks;
}

function readProgressFromPage() {
  const selectors = [
    "[role='slider'][aria-valuetext]",
    "[data-test-id*='progress' i]",
    "[class*='progress' i]",
    "[class*='playerBar' i]"
  ];
  const elements = document.querySelectorAll(selectors.join(","));

  for (const element of Array.from(elements).slice(0, 80)) {
    const values = [
      element.getAttribute("aria-valuetext"),
      element.getAttribute("aria-label"),
      element.textContent
    ];
    for (const value of values) {
      const clocks = parseClocks(value);
      if (clocks.length >= 2 && clocks[1] > 0) {
        return {
          position: Math.min(clocks[0], clocks[1]),
          duration: clocks[1],
          known: true
        };
      }
    }

    const current = Number(element.getAttribute("aria-valuenow"));
    const maximum = Number(element.getAttribute("aria-valuemax"));
    if (
      Number.isFinite(current)
      && Number.isFinite(maximum)
      && maximum > 120
    ) {
      return {
        position: Math.max(0, current),
        duration: maximum,
        known: true
      };
    }
  }
  return null;
}

function readTimeline(metadata, media) {
  const pageStateIsCurrent = pageTimeline
    && Date.now() - pageTimeline.receivedAt < 3000
    && (!pageTimeline.title || normalize(pageTimeline.title) === normalize(metadata?.title));

  if (pageStateIsCurrent && pageTimeline.positionKnown) {
    return {
      position: pageTimeline.position,
      duration: pageTimeline.duration,
      known: true
    };
  }
  if (media && Number.isFinite(media.duration) && media.duration > 0) {
    return {
      position: nonNegativeNumber(media.currentTime),
      duration: nonNegativeNumber(media.duration),
      known: true
    };
  }
  return readProgressFromPage() || {
    position: 0,
    duration: 0,
    known: false
  };
}

function readPlayer() {
  if (!ALLOWED_HOSTS.has(window.location.hostname)) {
    return null;
  }

  const metadata = navigator.mediaSession?.metadata;
  const media = findActiveMedia();
  const playbackState = navigator.mediaSession?.playbackState;
  const playing = playbackState === "playing"
    || Boolean(pageTimeline?.playing)
    || Boolean(media && !media.paused && !media.ended);

  if (!metadata?.title) {
    return {
      page_id: PAGE_ID,
      url: window.location.href,
      active: true,
      playing: false,
      title: "",
      artist: "",
      position: 0,
      duration: 0,
      artwork_url: ""
    };
  }

  const artwork = Array.from(metadata.artwork || []).at(-1);
  const timeline = readTimeline(metadata, media);
  return {
    page_id: PAGE_ID,
    url: window.location.href,
    active: true,
    playing,
    title: metadata.title || "",
    artist: metadata.artist || "",
    position: timeline.position,
    duration: timeline.duration,
    position_known: timeline.known,
    artwork_url: artwork?.src || ""
  };
}

async function sendState(force = false) {
  const state = readPlayer();
  if (!state) {
    return;
  }

  const settings = await chrome.storage.local.get({
    bridgePort: DEFAULT_PORT,
    bridgeToken: ""
  });
  if (!settings.bridgeToken) {
    return;
  }

  const fingerprint = JSON.stringify([
    state.playing,
    state.artist,
    state.title,
    Math.floor(state.position * 2)
  ]);
  const now = Date.now();
  if (!force && fingerprint === lastFingerprint && now - lastSuccessfulSend < 4000) {
    return;
  }

  try {
    const response = await fetch(
      `http://127.0.0.1:${Number(settings.bridgePort)}/v1/track`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${settings.bridgeToken}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(state)
      }
    );
    if (response.ok) {
      lastFingerprint = fingerprint;
      lastSuccessfulSend = now;
    }
  } catch {
    // Локальное приложение может быть выключено.
  }
}

setInterval(() => sendState(), SEND_INTERVAL);
document.addEventListener("play", () => sendState(true), true);
document.addEventListener("pause", () => sendState(true), true);
window.addEventListener("beforeunload", () => {
  const payload = readPlayer();
  if (payload) {
    payload.active = false;
    payload.playing = false;
    chrome.storage.local.get(
      { bridgePort: DEFAULT_PORT, bridgeToken: "" },
      (settings) => {
        if (!settings.bridgeToken) {
          return;
        }
        fetch(`http://127.0.0.1:${Number(settings.bridgePort)}/v1/track`, {
          method: "POST",
          keepalive: true,
          headers: {
            "Authorization": `Bearer ${settings.bridgeToken}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        }).catch(() => {});
      }
    );
  }
});
sendState(true);
