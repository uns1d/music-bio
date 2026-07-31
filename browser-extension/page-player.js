(() => {
  const channel = "music-bio-yandex-player";
  const mediaSession = navigator.mediaSession;
  let capturedTimeline = null;

  function numberOrZero(value) {
    const number = Number(value);
    return Number.isFinite(number) && number >= 0 ? number : 0;
  }

  function activeMedia() {
    const elements = Array.from(document.querySelectorAll("audio, video"));
    return elements
      .filter((element) => Number.isFinite(element.currentTime))
      .sort((left, right) => {
        const score = (element) => (
          (!element.paused && !element.ended ? 10000 : 0)
          + (Number.isFinite(element.duration) && element.duration > 0 ? 1000 : 0)
          + numberOrZero(element.currentTime)
        );
        return score(right) - score(left);
      })[0] || null;
  }

  function capturePosition(state) {
    if (!state) {
      capturedTimeline = null;
      return;
    }
    capturedTimeline = {
      position: numberOrZero(state.position),
      duration: numberOrZero(state.duration),
      playbackRate: numberOrZero(state.playbackRate) || 1,
      capturedAt: performance.now()
    };
  }

  function currentTimeline() {
    const media = activeMedia();
    if (media && Number.isFinite(media.duration) && media.duration > 0) {
      return {
        position: numberOrZero(media.currentTime),
        duration: numberOrZero(media.duration)
      };
    }
    if (!capturedTimeline) {
      return null;
    }

    const elapsed = mediaSession?.playbackState === "playing"
      ? Math.max(0, performance.now() - capturedTimeline.capturedAt) / 1000
      : 0;
    return {
      position: Math.min(
        capturedTimeline.duration,
        capturedTimeline.position + elapsed * capturedTimeline.playbackRate
      ),
      duration: capturedTimeline.duration
    };
  }

  function publish() {
    const metadata = mediaSession?.metadata;
    const timeline = currentTimeline();
    window.postMessage(
      {
        channel,
        title: metadata?.title || "",
        artist: metadata?.artist || "",
        playing: mediaSession?.playbackState === "playing",
        position: timeline?.position || 0,
        duration: timeline?.duration || 0,
        positionKnown: Boolean(timeline),
        sentAt: Date.now()
      },
      window.location.origin
    );
  }

  if (mediaSession && typeof mediaSession.setPositionState === "function") {
    const originalSetPositionState = mediaSession.setPositionState.bind(mediaSession);
    try {
      mediaSession.setPositionState = (state) => {
        capturePosition(state);
        const result = originalSetPositionState(state);
        publish();
        return result;
      };
    } catch {
      capturedTimeline = null;
    }
  }

  document.addEventListener("play", publish, true);
  document.addEventListener("pause", publish, true);
  document.addEventListener("seeked", publish, true);
  window.setInterval(publish, 500);
  publish();
})();
