const assert = require("node:assert/strict");
const path = require("node:path");

let now = 1000;
let intervalCallback = null;
const messages = [];
const mediaSession = {
  metadata: { title: "Track", artist: "Artist" },
  playbackState: "playing",
  setPositionState(state) {
    this.lastNativeState = state;
  }
};

Object.defineProperty(globalThis, "navigator", {
  configurable: true,
  value: { mediaSession }
});
globalThis.performance = { now: () => now };
globalThis.document = {
  addEventListener() {},
  querySelectorAll() {
    return [];
  }
};
globalThis.window = {
  location: { origin: "https://music.yandex.ru" },
  postMessage(payload) {
    messages.push(payload);
  },
  setInterval(callback) {
    intervalCallback = callback;
  }
};

require(path.join(__dirname, "..", "page-player.js"));
mediaSession.setPositionState({
  position: 42,
  duration: 180,
  playbackRate: 1
});

assert.equal(messages.at(-1).position, 42);
assert.equal(messages.at(-1).duration, 180);
assert.equal(messages.at(-1).positionKnown, true);

now += 1500;
intervalCallback();

assert.equal(messages.at(-1).position, 43.5);
assert.equal(messages.at(-1).duration, 180);
