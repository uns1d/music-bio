const portInput = document.querySelector("#port");
const tokenInput = document.querySelector("#token");
const status = document.querySelector("#status");

function showStatus(message, error = false) {
  status.textContent = message;
  status.classList.toggle("error", error);
}

async function loadSettings() {
  const values = await chrome.storage.local.get({
    bridgePort: 8765,
    bridgeToken: ""
  });
  portInput.value = values.bridgePort;
  tokenInput.value = values.bridgeToken;
}

async function saveSettings() {
  const port = Number(portInput.value);
  const token = tokenInput.value.trim();
  if (!Number.isInteger(port) || port < 1024 || port > 65535) {
    showStatus("Укажите порт от 1024 до 65535.", true);
    return false;
  }
  if (!token) {
    showStatus("Вставьте ключ из настроек Music Bio.", true);
    return false;
  }
  await chrome.storage.local.set({
    bridgePort: port,
    bridgeToken: token
  });
  showStatus("Настройки сохранены.");
  return true;
}

document.querySelector("#save").addEventListener("click", saveSettings);
document.querySelector("#test").addEventListener("click", async () => {
  if (!await saveSettings()) {
    return;
  }
  try {
    const response = await fetch(
      `http://127.0.0.1:${Number(portInput.value)}/v1/ping`,
      {
        headers: {
          "Authorization": `Bearer ${tokenInput.value.trim()}`
        }
      }
    );
    if (response.status === 401) {
      showStatus("Ключ не совпадает с ключом в Music Bio.", true);
      return;
    }
    if (response.status === 403) {
      showStatus("Music Bio отклонил источник запроса.", true);
      return;
    }
    if (!response.ok) {
      showStatus(`Music Bio ответил с ошибкой HTTP ${response.status}.`, true);
      return;
    }
    showStatus("Связь установлена. Откройте Яндекс Музыку.");
  } catch {
    showStatus(
      `Нет ответа на порту ${Number(portInput.value)}. `
      + "Запустите Music Bio или проверьте порт.",
      true
    );
  }
});

loadSettings();
