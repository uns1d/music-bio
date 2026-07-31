const assert = require("node:assert/strict");
const path = require("node:path");

const requests = [];
const listeners = {};
const media = {
  currentTime: 73.25,
  duration: 210,
  paused: false,
  ended: false
};

Object.defineProperty(globalThis, "navigator", {
  configurable: true,
  value: {
    mediaSession: {
      metadata: {
        title: "Track",
        artist: "Artist",
        artwork: []
      },
      playbackState: "playing"
    }
  }
});
globalThis.window = {
  location: {
    hostname: "music.yandex.ru",
    href: "https://music.yandex.ru/home"
  },
  addEventListener() {}
};
globalThis.document = {
  addEventListener(event, listener) {
    listeners[event] = listener;
  },
  querySelectorAll(selector) {
    return selector === "audio, video" ? [media] : [];
  }
};
globalThis.chrome = {
  storage: {
    local: {
      async get() {
        return {
          bridgePort: 8765,
          bridgeToken: "bridge-secret"
        };
      }
    }
  }
};
globalThis.fetch = async (url, options) => {
  requests.push({ url, options });
  return { ok: true };
};
globalThis.setInterval = () => {};

require(path.join(__dirname, "..", "content.js"));

setImmediate(async () => {
  assert.equal(requests.length, 1);
  const payload = JSON.parse(requests[0].options.body);
  assert.ok(payload.page_id);
  assert.equal(payload.active, true);
  assert.equal(payload.position, 73.25);
  assert.equal(payload.duration, 210);
  assert.equal(payload.position_known, true);

  media.paused = true;
  navigator.mediaSession.playbackState = "paused";
  listeners.pause();
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(requests.length, 2);
  const pausedPayload = JSON.parse(requests[1].options.body);
  assert.equal(pausedPayload.active, true);
  assert.equal(pausedPayload.playing, false);
  assert.equal(pausedPayload.title, "Track");
  assert.equal(pausedPayload.position, 73.25);
});
