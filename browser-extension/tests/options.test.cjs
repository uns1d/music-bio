const assert = require("node:assert/strict");
const path = require("node:path");

const listeners = {};
const elements = {};

function makeElement(id) {
  return {
    value: "",
    textContent: "",
    hasError: false,
    classList: {
      toggle(_name, enabled) {
        elements[id].hasError = enabled;
      }
    },
    addEventListener(event, callback) {
      listeners[`${id}:${event}`] = callback;
    }
  };
}

for (const id of ["port", "token", "status", "save", "test"]) {
  elements[id] = makeElement(id);
}

globalThis.document = {
  querySelector(selector) {
    return elements[selector.slice(1)];
  }
};

globalThis.chrome = {
  storage: {
    local: {
      async get() {
        return { bridgePort: 8767, bridgeToken: "bridge-secret" };
      },
      async set(values) {
        this.saved = values;
      }
    }
  }
};

let nextResponse = { ok: true, status: 200 };
globalThis.fetch = async () => {
  if (nextResponse instanceof Error) {
    throw nextResponse;
  }
  return nextResponse;
};

require(path.join(__dirname, "..", "options.js"));

setImmediate(async () => {
  assert.equal(elements.port.value, 8767);
  assert.equal(elements.token.value, "bridge-secret");

  nextResponse = { ok: false, status: 401 };
  await listeners["test:click"]();
  assert.match(elements.status.textContent, /Ключ не совпадает/);
  assert.equal(elements.status.hasError, true);

  nextResponse = new TypeError("Failed to fetch");
  await listeners["test:click"]();
  assert.match(elements.status.textContent, /Нет ответа на порту 8767/);

  nextResponse = { ok: true, status: 200 };
  await listeners["test:click"]();
  assert.match(elements.status.textContent, /Связь установлена/);
  assert.equal(elements.status.hasError, false);
});
