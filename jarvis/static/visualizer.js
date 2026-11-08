(function () {
  "use strict";

  const statusText = document.getElementById("statusText");
  const captionText = document.getElementById("captionText");
  const voiceSelect = document.getElementById("voiceSelect");
  const speedRange = document.getElementById("speedRange");
  const speedBadge = document.getElementById("speedBadge");
  const voiceSyncStatus = document.getElementById("voiceSyncStatus");
  const body = document.body;

  const STATUS_LABELS = {
    idle: "SYSTEM IDLE",
    listening: "LISTENING",
    thinking: "SYNTHESIZING",
    speaking: "TRANSMITTING",
    error: "SYSTEM FAULT"
  };

  function setSyncStatus(text, isError) {
    if (!voiceSyncStatus) return;
    voiceSyncStatus.textContent = text;
    voiceSyncStatus.style.color = isError ? "var(--color-error)" : "var(--accent-glow)";
    setTimeout(function () {
      voiceSyncStatus.textContent = "SYNCHRONIZED";
      voiceSyncStatus.style.color = "var(--dim)";
    }, 1500);
  }

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

  function loadVoiceSettings() {
    fetch("/api/voice/settings")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (!data) return;
        if (voiceSelect && Array.isArray(data.voices)) {
          voiceSelect.innerHTML = "";
          data.voices.forEach(function (v) {
            const opt = document.createElement("option");
            opt.value = v;
            opt.textContent = v;
            if (data.active_voice && (data.active_voice === v || data.active_voice.includes(v) || v.includes(data.active_voice))) {
              opt.selected = true;
            }
            voiceSelect.appendChild(opt);
          });
        }
        if (speedRange && typeof data.speed === "number") {
          speedRange.value = data.speed;
          if (speedBadge) {
            speedBadge.textContent = Number(data.speed).toFixed(2) + "x";
          }
        }
      })
      .catch(function (err) {
        console.error("Failed to load voice settings:", err);
      });
  }

  if (voiceSelect) {
    voiceSelect.addEventListener("change", function () {
      const selected = voiceSelect.value;
      if (!selected) return;
      setSyncStatus("COMMITTING...", false);
      fetch("/api/voice/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice: selected })
      })
        .then(function (res) {
          if (!res.ok) throw new Error("Server rejected voice update");
          return res.json();
        })
        .then(function () {
          setSyncStatus("UPDATED", false);
        })
        .catch(function (err) {
          console.error("Voice update failed:", err);
          setSyncStatus("FAILED", true);
        });
    });
  }

  let speedDebounce = null;
  if (speedRange) {
    speedRange.addEventListener("input", function () {
      const val = parseFloat(speedRange.value);
      if (speedBadge) {
        speedBadge.textContent = val.toFixed(2) + "x";
      }
      clearTimeout(speedDebounce);
      speedDebounce = setTimeout(function () {
        setSyncStatus("COMMITTING...", false);
        fetch("/api/voice/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ speed: val })
        })
          .then(function (res) {
            if (!res.ok) throw new Error("Server rejected speed update");
            return res.json();
          })
          .then(function () {
            setSyncStatus("UPDATED", false);
          })
          .catch(function (err) {
            console.error("Speed update failed:", err);
            setSyncStatus("FAILED", true);
          });
      }, 300);
    });
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

  // Fetch initial state & settings immediately via REST fallback
  fetch("/api/state")
    .then(function (res) { return res.json(); })
    .then(updateState)
    .catch(function () { /* Handled by SSE */ })
    .finally(function () {
      initSSE();
      loadVoiceSettings();
    });
})();
