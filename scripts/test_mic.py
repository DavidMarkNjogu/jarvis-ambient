"""Self-test for microphone input: records 2.5 seconds, computes RMS and peak, checks speech."""

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
DURATION = 2.5

print("--- Available Audio Input Devices ---")
for i, d in enumerate(sd.query_devices()):
    if d.get("max_input_channels", 0) > 0:
        default_mark = " (DEFAULT)" if i == sd.default.device[0] else ""
        name = d['name'].encode('ascii', 'replace').decode('ascii')
        print(f"[{i}] {name}{default_mark}")

default_dev = sd.query_devices(kind="input")
dev_name = default_dev['name'].encode('ascii', 'replace').decode('ascii')
print(f"\nRecording {DURATION}s from: {dev_name}")

audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
sd.wait()

mono = audio[:, 0]
peak = float(np.max(np.abs(mono)))
rms = float(np.sqrt(np.mean(mono**2)))

print(f"Recorded {len(mono)} samples.")
print(f"Peak amplitude: {peak:.6f}")
print(f"RMS energy:     {rms:.6f}")

if peak < 0.005:
    print("STATUS: ZERO/VERY LOW SIGNAL. Check Windows privacy settings or mic mute!")
elif rms > 0.01:
    print("STATUS: HEALTHY AUDIO SIGNAL DETECTED!")
else:
    print("STATUS: LOW NOISE FLOOR (quiet room, but mic is picking up sound).")

