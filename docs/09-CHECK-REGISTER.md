# Check register

Generated from `acceptance/spec.json` by `scripts/verify.py --render-register`. Do not edit by hand; verify.py fails if this file is out of date.

Kinds: **test** = named automated tests must exist and pass. **live** = a script that uses the real network, models or speakers. **human** = David judges and signs in `acceptance/signoffs.md`.

## Phase 0: Workshop

### P0-L1 (live) Python 3.11+ runs from .venv and every installed dependency imports
- Command: `-c import sys, httpx, rich, dotenv, numpy, sounddevice, comtypes, faster_whisper; assert sys.version_info >= (3, 11); print('LIVE deps: PASS')` must print `LIVE deps: PASS`

## Phase 1: Text brain

### P1-01 (test) Jarvis keeps the conversation in mind: system prompt, then recent history, then the new message; only the last N turns are sent; /reset forgets; a reply cut short is still remembered
- Test: `tests/test_brain.py::test_streams_reply_and_remembers_it`
- Test: `tests/test_brain.py::test_sends_system_prompt_then_history_then_new_message`
- Test: `tests/test_brain.py::test_only_recent_turns_are_sent`
- Test: `tests/test_brain.py::test_reset_forgets_history`
- Test: `tests/test_brain.py::test_stopping_early_still_remembers_what_was_said`
- Tests must touch: `Brain`

### P1-02 (test) If a brain fails before answering Jarvis tries the next one; an empty reply counts as a failure; a failure mid-reply never splices two models together; all failing gives a clear error
- Test: `tests/test_brain.py::test_falls_back_to_next_provider_before_any_text`
- Test: `tests/test_brain.py::test_empty_reply_counts_as_failure`
- Test: `tests/test_brain.py::test_raises_when_every_provider_fails`
- Test: `tests/test_brain.py::test_mid_reply_failure_keeps_partial_text_and_does_not_switch`
- Test: `tests/test_brain.py::test_needs_a_provider`
- Tests must touch: `Brain`

### P1-03 (test) The provider layer streams text from the OpenAI-style SSE format and turns HTTP and connection errors into plain-English reasons
- Test: `tests/test_providers.py::test_streams_text_from_sse_and_sends_model_and_key`
- Test: `tests/test_providers.py::test_http_errors_become_plain_reasons`
- Test: `tests/test_providers.py::test_other_errors_include_the_service_message`
- Test: `tests/test_providers.py::test_gemini_style_bad_key_reads_as_rejected_key`
- Test: `tests/test_providers.py::test_error_event_mid_stream_raises`
- Test: `tests/test_providers.py::test_connection_failure_mentions_ollama_when_local`
- Test: `tests/test_providers.py::test_list_models_strips_gemini_prefix`

### P1-04 (test) Settings come from .env with sensible defaults, skip brains without keys, keep the configured order, and give clear errors for bad values
- Test: `tests/test_config.py::test_defaults_skip_cloud_providers_without_keys`
- Test: `tests/test_config.py::test_keys_enable_providers_in_configured_order`
- Test: `tests/test_config.py::test_blank_values_fall_back_to_defaults`
- Test: `tests/test_config.py::test_unknown_provider_is_a_clear_error`
- Test: `tests/test_config.py::test_bad_history_setting_is_a_clear_error`
- Tests must touch: `settings_from_env`

### P1-05 (test) The system prompt tells Jarvis the user's name and the current time
- Test: `tests/test_config.py::test_system_prompt_includes_name_and_time`
- Tests must touch: `system_prompt`

### P1-06 (test) setup.bat recognises Gemini and Groq key shapes (including the newer AQ. Gemini keys), hides keys when showing them, edits .env without losing comments, rejects bad keys and can add a backup key
- Test: `tests/test_setup.py::test_detects_provider_from_key_shape`
- Test: `tests/test_setup.py::test_mask_hides_the_middle`
- Test: `tests/test_setup.py::test_updates_existing_lines_and_keeps_comments`
- Test: `tests/test_setup.py::test_replaces_old_value_and_appends_missing_settings`
- Test: `tests/test_setup.py::test_ignores_commented_out_settings`
- Test: `tests/test_setup_flow.py::test_enter_reads_key_from_clipboard_and_saves`
- Test: `tests/test_setup_flow.py::test_rejected_key_is_not_saved_and_asks_again`
- Test: `tests/test_setup_flow.py::test_can_add_backup_key`
- Test: `tests/test_setup_flow.py::test_clipboard_without_a_key_asks_again`

### P1-L1 (live) The real cloud brain answers a real question using the key in .env
- Command: `scripts/live_checks.py brain` must print `LIVE brain: PASS`

## Phase 2: Ears and voice

### P2-01 (test) Recording stops after a pause following speech, gives up if nobody speaks, ignores a single click, adapts to a noisy room, stops at the maximum length, and writes 16 kHz mono 16-bit WAV
- Test: `tests/test_listen.py::test_stops_after_a_pause_following_speech`
- Test: `tests/test_listen.py::test_gives_up_if_nobody_speaks`
- Test: `tests/test_listen.py::test_a_single_click_is_not_speech`
- Test: `tests/test_listen.py::test_noisy_room_raises_the_threshold`
- Test: `tests/test_listen.py::test_stops_at_max_length_even_mid_speech`
- Test: `tests/test_listen.py::test_wav_is_16khz_mono_16bit`
- Tests must touch: `Endpointer`, `to_wav_bytes`

### P2-02 (test) Streaming text is cut into sentences as soon as each ends, tolerates tokens split mid-word, does not split on abbreviations or decimals, and strips markdown and links before speaking
- Test: `tests/test_speech.py::test_releases_sentences_as_soon_as_they_end`
- Test: `tests/test_speech.py::test_handles_tokens_split_mid_word`
- Test: `tests/test_speech.py::test_short_fragments_join_the_next_sentence`
- Test: `tests/test_speech.py::test_does_not_split_on_abbreviations_or_decimals`
- Test: `tests/test_speech.py::test_newlines_end_a_sentence`
- Test: `tests/test_speech.py::test_cleans_markdown_and_links`
- Test: `tests/test_speech.py::test_nothing_to_say_yields_nothing`
- Tests must touch: `SentenceBuffer`, `clean_for_speech`

### P2-03 (test) Speech engines are chosen automatically (Groq ears if a key exists, Kokoro only if downloaded), explicit choices win, and bad choices give clear errors
- Test: `tests/test_voice_config.py::test_auto_prefers_groq_ears_when_key_present_and_windows_voice_without_kokoro`
- Test: `tests/test_voice_config.py::test_auto_goes_offline_without_groq_and_uses_kokoro_when_downloaded`
- Test: `tests/test_voice_config.py::test_explicit_choices_win`
- Test: `tests/test_voice_config.py::test_groq_ears_without_key_is_a_clear_error`
- Test: `tests/test_voice_config.py::test_unknown_engine_is_a_clear_error`
- Tests must touch: `voice_settings_from_env`

### P2-L1 (live) Spoken audio is transcribed correctly by the real local Whisper model (Windows speaks a sentence into a WAV, Whisper must hear 'Japan')
- Command: `scripts/live_checks.py stt` must print `LIVE stt: PASS`

### P2-L2 (live) The Windows voice speaks a sentence without error (the script cannot hear it; P2-H2 covers that)
- Command: `scripts/live_checks.py tts` must print `LIVE tts: PASS`

### P2-L3 (live) Speech in to answer out works end to end within the time limit set in scripts/live_checks.py (heard 'capital of Japan', answered Tokyo)
- Command: `scripts/live_checks.py e2e` must print `LIVE e2e: PASS`

### P2-H1 (human) With his own voice and real microphone, David asks 5 real questions through voice.bat and gets a spoken answer each time
- David does: Double-click voice.bat, press Enter, ask a question aloud, pause. Repeat 5 times with different questions.

### P2-H2 (human) The voice is clearly audible, British, and no sentence is cut off in the middle
- David does: During P2-H1 listen for volume, accent and clipped sentences.

## Phase 3: Wake word and voice control

### P3-01 (test) The wake detector fires once when the score crosses the threshold, ignores a second spike inside the 2 second cooldown, and fires again after it
- Must prove: feed fake score frames; count of fires is exactly 1 for two spikes 1.0 s apart and exactly 2 for two spikes 2.5 s apart
- Test: `tests/test_wake.py::test_fires_once_when_score_crosses_threshold`
- Test: `tests/test_wake.py::test_cooldown_ignores_a_second_spike_within_two_seconds`
- Test: `tests/test_wake.py::test_fires_again_after_cooldown`
- Tests must touch: `WakeDetector`

### P3-02 (test) The wake detector never fires below the threshold, including a single noisy spike just under it
- Must prove: scores of 0.49 with threshold 0.5 produce zero fires, including one isolated 0.49 spike amid zeros
- Test: `tests/test_wake.py::test_never_fires_below_threshold`
- Test: `tests/test_wake.py::test_single_low_spike_does_not_fire`
- Tests must touch: `WakeDetector`

### P3-03 (test) While Jarvis is speaking the detector ignores scores, and when speech ends its buffer is cleared so Jarvis cannot wake on its own voice
- Must prove: a high score while paused gives zero fires; after resume the same high score from stale buffered audio gives zero fires; a fresh high score gives one
- Test: `tests/test_wake.py::test_scores_while_paused_are_ignored`
- Test: `tests/test_wake.py::test_resume_clears_the_buffer`
- Tests must touch: `WakeDetector`

### P3-04 (test) The wake chime is generated in code: 16 kHz, between 0.1 and 0.6 seconds, and not silent
- Must prove: length in samples within bounds and max absolute amplitude greater than 0.05
- Test: `tests/test_wake.py::test_make_chime_is_short_non_silent_16khz`
- Tests must touch: `make_chime`

### P3-05 (test) WAKE_THRESHOLD, JARVIS_WAKE and JARVIS_VOICE_SPEED have defaults and give clear errors for bad values such as 'high' or 1.7
- Must prove: defaults 0.5 / on / 1.1; ValueError messages name the setting and the bad value
- Test: `tests/test_voice_config.py::test_wake_defaults`
- Test: `tests/test_voice_config.py::test_bad_wake_threshold_is_a_clear_error`
- Test: `tests/test_voice_config.py::test_bad_voice_speed_is_a_clear_error`
- Tests must touch: `voice_settings_from_env`, `settings_from_env`

### P3-06 (test) One shared microphone stream feeds 1,280-sample frames, and the recorder makes the same stop decisions from stream frames as it does today
- Must prove: frames are exactly 1280 samples; the same synthetic speech+pause input yields the same stop index through the stream path and the existing path
- Test: `tests/test_listen.py::test_micstream_delivers_frames_of_1280_samples`
- Test: `tests/test_listen.py::test_endpointer_makes_same_decisions_from_stream_frames`
- Tests must touch: `MicStream`, `Endpointer`

### P3-07 (test) If the wake model cannot load, voice.bat falls back to press-Enter mode with a one-line explanation instead of crashing
- Must prove: force the loader to raise; the run function returns normally, selects enter mode, and the console output contains a reason
- Test: `tests/test_voice_loop.py::test_falls_back_to_enter_mode_when_wake_model_fails`

### P3-08 (test) Speech speed is adjustable: the Windows voice maps speed to SAPI Rate (-10 to +10, clamped) and the Kokoro voice passes the speed factor to synthesis
- Must prove: 1.0 maps to Rate 0, 1.5 maps to a positive Rate, out-of-range values are clamped; a fake Kokoro receives speed=1.25 in create()
- Test: `tests/test_tts.py::test_windows_rate_maps_to_sapi_bounds`
- Test: `tests/test_tts.py::test_kokoro_speed_reaches_synthesis`
- Tests must touch: `WindowsVoice`, `KokoroVoice`

### P3-09 (test) Jarvis can list installed voices and switch between them
- Must prove: list_voices() returns the names the fake engine reports; switching changes which voice speaks the next sentence
- Test: `tests/test_tts.py::test_list_voices_names_installed_voices`
- Test: `tests/test_tts.py::test_switching_voice_changes_the_active_voice`
- Tests must touch: `list_voices`

### P3-10 (test) In voice mode the system prompt tells Jarvis the real commands for changing voice and speed, so it never claims the feature does not exist
- Must prove: the voice-mode prompt contains /voice and /speed and the current voice name; text mode does not
- Test: `tests/test_config.py::test_voice_prompt_mentions_voice_commands`
- Tests must touch: `system_prompt`

### P3-L1 (live) The real wake model detects 'Hey Jarvis' spoken by Windows into a WAV, then the recorder and Whisper transcribe the question after it
- Command: `scripts/live_checks.py wake` must print `LIVE wake: PASS`

### P3-H1 (human) From about 2 metres in a quiet room, saying 'Hey Jarvis' wakes it at least 8 times out of 10
- David does: Stand 2 m from the laptop. Say 'Hey Jarvis' 10 times, 5 seconds apart. Write down how many woke it.

### P3-H2 (human) With a TV or music playing for one hour, it wakes by itself fewer than about once
- David does: Leave voice.bat running for an hour with normal TV or music. Count unprompted chimes.

### P3-H3 (human) Jarvis never wakes on its own voice while speaking a long answer
- David does: Ask for a long explanation (30+ seconds). No chime may sound while it speaks.

### P3-H4 (human) Speed and voice can be changed by command and the difference is audible; asking 'how do I change your voice?' gets a correct answer
- David does: Type /speed 1.4, /voices, /voice <name>. Then ask aloud how to change the voice.

## Phase 4: Hands (tools)

### P4-01 (test) Only registered tools can run, and their arguments are validated before anything executes
- Must prove: an unknown tool name raises ToolError and runs nothing; wrong argument types and out-of-range values are rejected with a message naming the argument
- Test: `tests/test_tools.py::test_unknown_tool_is_refused`
- Test: `tests/test_tools.py::test_arguments_are_validated_against_the_schema`
- Tests must touch: `ToolRegistry`

### P4-02 (test) Anything that deletes, sends or spends needs a spoken yes first; a tool with no declared risk level defaults to needing confirmation
- Must prove: a confirm-first tool called without a yes performs no side effect (checked on a fake); after a yes it runs once; an unlabeled tool behaves as confirm-first
- Test: `tests/test_tools.py::test_confirm_first_tools_do_nothing_without_a_yes`
- Test: `tests/test_tools.py::test_confirm_first_tools_run_after_a_yes`
- Test: `tests/test_tools.py::test_unlabeled_tools_default_to_confirm_first`
- Tests must touch: `ToolRegistry`

### P4-03 (test) Every tool call is logged with name, arguments and result to data/tool-log.jsonl, and secrets never appear in the log
- Must prove: after a call the log has one JSON line with the three fields; a key-shaped argument is replaced by a placeholder
- Test: `tests/test_tools.py::test_every_call_is_logged_with_name_args_and_result`
- Test: `tests/test_tools.py::test_secrets_are_not_written_to_the_log`
- Tests must touch: `ToolRegistry`

### P4-04 (test) Opening apps and folders is limited to an allowlist, never uses a shell, and refuses paths outside allowed folders
- Must prove: a non-allowlisted app name is refused; subprocess is called with an argument list; a path with .. or outside the allowed roots is refused
- Test: `tests/test_tools_apps.py::test_only_allowlisted_apps_open`
- Test: `tests/test_tools_apps.py::test_no_shell_is_used`
- Test: `tests/test_tools_apps.py::test_paths_outside_allowed_folders_are_refused`
- Tests must touch: `open_app`, `open_folder`

### P4-05 (test) Time, weather and web search tools return correct structured data from fake responses, and search results are marked as untrusted data
- Must prove: time uses the Africa/Nairobi zone; weather parsing of a recorded Open-Meteo payload gives the expected numbers; search results are wrapped so the model is told they are data not instructions
- Test: `tests/test_tools_info.py::test_time_and_date_use_local_timezone`
- Test: `tests/test_tools_info.py::test_weather_parses_open_meteo_response`
- Test: `tests/test_tools_info.py::test_web_search_returns_titles_and_snippets`
- Test: `tests/test_tools_info.py::test_search_results_are_marked_as_untrusted_data`

### P4-06 (test) Timers fire after the right delay, and reminders survive a restart
- Must prove: with a fake clock a 60 s timer fires at 60 s and not before; a reminder written by one connection is read by a new one
- Test: `tests/test_tools_timers.py::test_timer_fires_after_delay`
- Test: `tests/test_tools_timers.py::test_reminder_survives_restart`

### P4-07 (test) Streamed tool calls from the model are assembled, executed, fed back, and the loop stops after a maximum number of steps
- Must prove: split tool_call deltas reassemble into one call; the result is sent back and the final answer streams; a model that always asks for a tool stops at the step limit with a clear message
- Test: `tests/test_providers.py::test_tool_call_deltas_are_assembled`
- Test: `tests/test_brain.py::test_brain_executes_tool_and_feeds_result_back`
- Test: `tests/test_brain.py::test_tool_loop_stops_after_max_steps`
- Tests must touch: `Brain`, `Provider`

### P4-08 (test) The 'Honesty' paragraph of the prompt lists exactly the tools that are registered, so Jarvis neither denies nor invents abilities
- Must prove: for every registered tool its name appears in the prompt, and abilities that are not registered are still described as not connected
- Test: `tests/test_config.py::test_prompt_lists_exactly_the_registered_tools`
- Tests must touch: `system_prompt`

### P4-L1 (live) The real brain, given the tools, answers 'what time is it' by calling the time tool and the answer contains the real current hour
- Command: `scripts/live_checks.py tools` must print `LIVE tools: PASS`

### P4-H1 (human) By voice: 'Open Chrome and search for flights to Mombasa' works
- David does: Say it. Chrome opens on a search page for the query.

### P4-H2 (human) By voice, asking Jarvis to delete a file makes it ask for confirmation out loud and nothing is deleted before the yes
- David does: Create a junk file. Ask Jarvis to delete it. Say no first (file must remain), then repeat and say yes.

## Phase 5: Memory

### P5-01 (test) A remembered fact survives closing and reopening the database
- Must prove: write with one Memory object, open a new one on the same file, the fact is returned
- Test: `tests/test_memory.py::test_remembered_fact_survives_a_new_connection`
- Tests must touch: `Memory`

### P5-02 (test) Recall finds the relevant fact by keyword and does not return unrelated ones
- Must prove: after storing three different facts, recall('sister') returns only the sister fact
- Test: `tests/test_memory.py::test_recall_finds_relevant_fact_by_keyword`
- Tests must touch: `Memory`

### P5-03 (test) Forgetting removes a fact and it is never recalled again
- Must prove: after forget, recall returns nothing for that fact, including after reopening the file
- Test: `tests/test_memory.py::test_forget_removes_the_fact_and_it_is_not_recalled`
- Tests must touch: `Memory`

### P5-04 (test) Profile facts are loaded into the system prompt at startup
- Must prove: a stored profile fact appears in the prompt text
- Test: `tests/test_config.py::test_prompt_includes_profile_facts`
- Tests must touch: `system_prompt`

### P5-05 (test) Memory refuses to store API keys, passwords and card numbers
- Must prove: strings shaped like AIza/AQ./gsk_ keys, 'my password is ...' and 16-digit card numbers are rejected and not written
- Test: `tests/test_memory.py::test_refuses_to_store_api_keys_and_passwords`
- Tests must touch: `Memory`

### P5-06 (test) A session summary is saved and can be retrieved in a later session
- Must prove: summary text stored at end of one session is returned by search in a new Memory object
- Test: `tests/test_memory.py::test_session_summary_is_saved_and_retrievable`
- Tests must touch: `Memory`

### P5-L1 (live) Memory persists across two separate Python processes using a real database file
- Command: `scripts/live_checks.py memory` must print `LIVE memory: PASS`

### P5-H1 (human) After quitting and restarting Jarvis it still knows David's name, a stated preference and yesterday's reminder
- David does: Tell Jarvis a fact. Quit. Start it again. Ask about the fact.

## Phase 6: Eyes (screen and camera)

### P6-01 (test) The screen tool captures, downsizes and encodes a screenshot for the vision model
- Must prove: with a fake capture, the output is a base64 data URL whose decoded image is no wider than the configured maximum
- Test: `tests/test_vision.py::test_screenshot_is_downscaled_and_encoded`
- Tests must touch: `look_at_screen`

### P6-02 (test) The camera opens only on an explicit request and is always released afterwards, even when capture fails
- Must prove: no camera is opened at import or startup; after a successful and after a failing capture release() was called
- Test: `tests/test_vision.py::test_camera_is_opened_only_for_an_explicit_request_and_closed_after`
- Tests must touch: `look_through_camera`

### P6-03 (test) Images are sent to the provider in the correct base64 message format
- Must prove: the request body contains an image_url part whose url starts with data:image/
- Test: `tests/test_providers.py::test_image_is_sent_as_base64_data_url`
- Tests must touch: `Provider`

### P6-04 (test) Images are never written to disk unless the user asked to save one
- Must prove: a temp directory is empty after a normal look; a file exists only after an explicit save request
- Test: `tests/test_vision.py::test_images_are_not_written_to_disk_unless_asked`
- Tests must touch: `look_at_screen`, `look_through_camera`

### P6-L1 (live) The real vision model reads text from an image (a generated image containing ERROR 4417 must be read back as 4417)
- Command: `scripts/live_checks.py vision` must print `LIVE vision: PASS`

### P6-H1 (human) Asked 'what is this error on my screen?' with a real error visible, Jarvis describes it correctly and suggests a fix
- David does: Open a real error message, ask aloud, judge the answer.

## Phase 7: Reach (phone)

### P7-01 (test) Only David's chat id is answered; everyone else is ignored silently
- Must prove: an update from another chat id produces no brain call and no reply
- Test: `tests/test_telegram.py::test_messages_from_unknown_chat_ids_are_ignored`
- Tests must touch: `TelegramBridge`

### P7-02 (test) A text message reaches the brain and the reply is sent back
- Must prove: with a fake API, one text update leads to exactly one sendMessage carrying the brain's reply
- Test: `tests/test_telegram.py::test_text_message_goes_to_brain_and_reply_is_sent`
- Tests must touch: `TelegramBridge`

### P7-03 (test) A voice note is transcribed before it is asked
- Must prove: the audio is passed to the transcriber and its text, not the audio, reaches the brain
- Test: `tests/test_telegram.py::test_voice_note_is_transcribed_before_asking`
- Tests must touch: `TelegramBridge`

### P7-04 (test) The bot token never appears in logs or error messages
- Must prove: force a network error; the captured log and exception text do not contain the token
- Test: `tests/test_telegram.py::test_bot_token_is_never_logged_or_in_errors`
- Tests must touch: `TelegramBridge`

### P7-05 (test) The polling loop survives network errors with backoff instead of crashing or spinning
- Must prove: three consecutive failures lead to increasing waits and then a normal update is still processed
- Test: `tests/test_telegram.py::test_poll_loop_survives_network_errors_with_backoff`
- Tests must touch: `TelegramBridge`

### P7-H1 (human) From his phone, David texts 'what's on my reminders?' and gets the right answer while the PC is on
- David does: Send the message from Telegram on the phone.

## Phase 8: Face (HUD)

### P8-01 (test) The visualizer's event bus holds the current state, delivers changes to subscribers and drops dead ones
- Test: `tests/test_visual.py::test_broadcaster_initial_state`
- Test: `tests/test_visual.py::test_broadcaster_set_state_and_delivery`
- Test: `tests/test_visual.py::test_broadcaster_drops_dead_subscribers`
- Tests must touch: `VisualBroadcaster`

### P8-02 (test) The local visualizer server serves its page, streams states over SSE, finds a free port and survives clients disconnecting abruptly
- Test: `tests/test_visual.py::test_find_free_port`
- Test: `tests/test_visual.py::test_visual_server_http_and_api`
- Test: `tests/test_visual.py::test_visual_server_sse_stream`
- Test: `tests/test_visual.py::test_abrupt_client_disconnect`
- Tests must touch: `VisualServer`, `find_free_port`

### P8-03 (test) The voice loop reports idle, listening, thinking, speaking and error states to the visualizer
- Test: `tests/test_visual.py::test_greet_with_visual`
- Test: `tests/test_visual.py::test_respond_with_visual`
- Tests must touch: `greet`, `respond`

### P8-04 (test) The full HUD shows a transcript of what David said and what Jarvis answered
- Must prove: set_state or a new publish_transcript call produces an SSE message with role and text
- Test: `tests/test_visual.py::test_events_include_transcript_entries_for_user_and_jarvis`
- Tests must touch: `VisualBroadcaster`

### P8-05 (test) Tool calls appear live in the HUD tool log
- Must prove: running a fake tool publishes an event with the tool name, arguments and outcome
- Test: `tests/test_visual.py::test_tool_calls_are_broadcast_to_the_hud`
- Tests must touch: `VisualBroadcaster`

### P8-06 (test) The HUD shows CPU, memory and which brain is in use
- Must prove: a stats snapshot has numeric cpu and ram fields within 0 to 100 and the name of the active brain
- Test: `tests/test_sysstats.py::test_stats_snapshot_has_cpu_ram_and_brain`
- Tests must touch: `system_stats`

### P8-07 (test) Jarvis can be set to start with Windows and the setting can be removed cleanly
- Must prove: in a temp Startup folder a shortcut is created and then removed, and nothing outside the folder changes
- Test: `tests/test_autostart.py::test_startup_shortcut_is_created_and_removed`
- Tests must touch: `autostart`

### P8-H1 (human) During a real conversation the orb visibly changes with listening, thinking and speaking
- David does: Run voice.bat, hold a conversation, watch the browser window.

### P8-H2 (human) David has reviewed screenshots of the finished HUD at 1440x900 and 390x844 and approves the look
- David does: Open the screenshots the agent saved under docs/images and decide.

## Phase 9: Initiative

### P9-01 (test) A scheduled job fires at its time and not before
- Must prove: with a fake clock a 07:00 job has not run at 06:59 and has run once by 07:01
- Test: `tests/test_scheduler.py::test_job_fires_at_its_time`
- Tests must touch: `Scheduler`

### P9-02 (test) Nothing is spoken during quiet hours
- Must prove: a job due at 02:00 is held until quiet hours end and not spoken at 02:00
- Test: `tests/test_scheduler.py::test_nothing_is_spoken_during_quiet_hours`
- Tests must touch: `Scheduler`

### P9-03 (test) The morning briefing is built from the weather and reminders tools, not made up
- Must prove: with fake tools returning known values, those values appear in the briefing text
- Test: `tests/test_scheduler.py::test_morning_brief_includes_weather_and_reminders`
- Tests must touch: `morning_brief`

### P9-04 (test) Jarvis never talks over David: it waits until the microphone and speaker are idle
- Must prove: while the fake mouth reports speaking or the mic reports activity the announcement is held, and released after idle
- Test: `tests/test_scheduler.py::test_waits_until_mouth_and_mic_are_idle`
- Tests must touch: `Scheduler`

### P9-05 (test) Nudges (such as 'you have been coding for 3 hours') are off by default and rate-limited when on
- Must prove: default config schedules no nudges; when enabled, two triggers within the minimum gap produce one announcement
- Test: `tests/test_scheduler.py::test_nudges_are_off_by_default_and_rate_limited`
- Tests must touch: `Scheduler`

### P9-H1 (human) At 7 am Jarvis greets David with the day's weather and reminders without being asked
- David does: Leave Jarvis running overnight with the briefing enabled.
