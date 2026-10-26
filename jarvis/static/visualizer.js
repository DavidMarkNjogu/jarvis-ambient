(function () {
  "use strict";

  const statusText = document.getElementById("statusText");
  const captionText = document.getElementById("captionText");
  const body = document.body;

  const STATUS_LABELS = {
    idle: "SYSTEM IDLE",
    listening: "LISTENING",
    thinking: "SYNTHESIZING",
    speaking: "TRANSMITTING",
    error: "SYSTEM FAULT"
  };

  function updateState(data) {
    if (!data || !data.status) return;

    const status = data.status.toLowerCase();
    body.className = "state-" + status;

    if (statusText) {
      statusText.textContent = STATUS_LABELS[status] || status.toUpperCase();
    }

    if (captionText) {
      if (data.text) {
        captionText.textContent = data.text;
      } else if (status === "idle") {
        captionText.textContent = "Awaiting command input...";
      } else if (status === "listening") {
        captionText.textContent = "Capturing voice stream...";
      } else if (status === "thinking") {
        captionText.textContent = "Synthesizing response...";
      }
    }
  }

  function initSSE() {
    const es = new EventSource("/events");

    es.onmessage = function (event) {
      try {
        const payload = JSON.parse(event.data);
        updateState(payload);
      } catch (err) {
        console.error("Failed to parse event data:", err);
      }
    };

    es.onerror = function () {
      if (statusText) {
        statusText.textContent = "RECONNECTING...";
      }
      es.close();
      setTimeout(initSSE, 2000);
    };
  }

  // Also fetch initial state immediately via REST fallback
  fetch("/api/state")
    .then(function (res) { return res.json(); })
    .then(updateState)
    .catch(function () { /* Handled by SSE */ })
    .finally(initSSE);
})();
