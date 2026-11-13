(function () {
  "use strict";

  const statusText = document.getElementById("statusText");
  const captionText = document.getElementById("captionText");
  const voiceSelect = document.getElementById("voiceSelect");
  const speedRange = document.getElementById("speedRange");
  const speedBadge = document.getElementById("speedBadge");
  const voiceSyncStatus = document.getElementById("voiceSyncStatus");
  const commandForm = document.getElementById("commandForm");
  const commandInput = document.getElementById("commandInput");
  const micBtn = document.getElementById("micBtn");
  const sendBtn = document.getElementById("sendBtn");
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

  function submitCommand(rawText) {
    if (!rawText || !rawText.trim()) return;
    const msg = rawText.trim();
    if (commandInput) {
      commandInput.value = "";
    }
    if (sendBtn) {
      sendBtn.disabled = true;
      sendBtn.textContent = "SENDING...";
    }
    updateState({ status: "thinking", text: "Processing: " + msg });

    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg })
    })
      .then(function (res) {
        if (!res.ok) throw new Error("Server error " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (data && data.reply) {
          updateState({ status: "speaking", text: data.reply });
        } else {
          updateState({ status: "idle", text: "Acknowledged." });
        }
      })
      .catch(function (err) {
        console.error("Command error:", err);
        updateState({ status: "error", text: "Command error: " + err.message });
      })
      .finally(function () {
        if (sendBtn) {
          sendBtn.disabled = false;
          sendBtn.textContent = "TRANSMIT";
        }
      });
  }

  if (commandForm) {
    commandForm.addEventListener("submit", function (e) {
      e.preventDefault();
      if (commandInput) {
        submitCommand(commandInput.value);
      }
    });
  }

  // Web Speech Recognition for VOX button
  let recognition = null;
  let isRecording = false;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = function () {
      isRecording = true;
      if (micBtn) {
        micBtn.classList.add("recording");
      }
      updateState({ status: "listening", text: "Listening via browser microphone..." });
    };

    recognition.onresult = function (event) {
      if (event.results && event.results[0] && event.results[0][0]) {
        const transcript = event.results[0][0].transcript;
        if (commandInput) {
          commandInput.value = transcript;
        }
        submitCommand(transcript);
      }
    };

    recognition.onerror = function (event) {
      isRecording = false;
      if (micBtn) {
        micBtn.classList.remove("recording");
      }
      updateState({ status: "error", text: "Voice capture notice: " + (event.error || "no speech detected") });
      setTimeout(function () {
        updateState({ status: "idle", text: "" });
      }, 3000);
    };

    recognition.onend = function () {
      isRecording = false;
      if (micBtn) {
        micBtn.classList.remove("recording");
      }
    };
  }

  if (micBtn) {
    micBtn.addEventListener("click", function () {
      if (!recognition) {
        if (captionText) {
          captionText.textContent = "Browser speech recognition unavailable. Type command directly.";
        }
        return;
      }
      if (isRecording) {
        recognition.stop();
      } else {
        try {
          recognition.start();
        } catch (err) {
          console.error("Speech recognition start failed:", err);
        }
      }
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
