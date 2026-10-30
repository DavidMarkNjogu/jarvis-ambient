# DONE CONTRACT: Phase 6 - Eyes (Screen and Camera) QA Loop
Mode: Continuous
StartedAt: 2026-10-30T17:15:00Z
Timeline: 120m

## Checks
- [x] Invariants 1 through 12 in `~/.gemini/user-invariants.md` verified and aligned
- [x] P6-01: The screen tool captures, downsizes and encodes a screenshot for the vision model (`tests/test_vision.py::test_screenshot_is_downscaled_and_encoded`)
- [x] P6-02: The camera opens only on an explicit request and is always released afterwards, even when capture fails (`tests/test_vision.py::test_camera_is_opened_only_for_an_explicit_request_and_closed_after`)
- [x] P6-03: Images are sent to the provider in the correct base64 message format (`tests/test_providers.py::test_image_is_sent_as_base64_data_url`)
- [x] P6-04: Images are never written to disk unless the user asked to save one (`tests/test_vision.py::test_images_are_not_written_to_disk_unless_asked`)
- [x] P6-L1: The real vision model reads text from an image (`scripts/live_checks.py vision`)
- [x] P6-Pitfalls: Camera released on failure, zero memory/file leakage, primary monitor coordinates verified
- [x] Mutation Gate: `scripts/verify.py --mutate jarvis/vision.py` passes (82% achieved, >= 60%)
- [x] Whole Verification Gate: `scripts/verify.py` passes with 0 test failures (165 passed)
- [x] Granular atomic git commit created (`type(scope): message`)
