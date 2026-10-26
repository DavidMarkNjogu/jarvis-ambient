from jarvis.speech import SentenceBuffer, clean_for_speech


def feed_all(buffer, pieces):
    out = []
    for piece in pieces:
        out += buffer.feed(piece)
    return out + buffer.flush()


def test_releases_sentences_as_soon_as_they_end():
    buffer = SentenceBuffer()
    assert buffer.feed("Good evening. The weather ") == ["Good evening."]
    assert buffer.feed("looks grim, I'm afraid! Shall I") == ["The weather looks grim, I'm afraid!"]
    assert buffer.flush() == ["Shall I"]


def test_handles_tokens_split_mid_word():
    pieces = ["Right away, s", "ir", ". Open", "ing it ", "now."]
    assert feed_all(SentenceBuffer(), pieces) == ["Right away, sir.", "Opening it now."]


def test_short_fragments_join_the_next_sentence():
    assert feed_all(SentenceBuffer(), ["Yes. That is correct, sir. "]) == ["Yes. That is correct, sir."]


def test_does_not_split_on_abbreviations_or_decimals():
    text = "Dr. Banner says version 3.5 is ready. Mr. Stark disagrees."
    assert feed_all(SentenceBuffer(), [text]) == ["Dr. Banner says version 3.5 is ready.", "Mr. Stark disagrees."]


def test_newlines_end_a_sentence():
    assert feed_all(SentenceBuffer(), ["First line of the reply\nSecond line here"]) == [
        "First line of the reply",
        "Second line here",
    ]


def test_cleans_markdown_and_links():
    assert clean_for_speech("**Done.** See https://example.com/x for `details`") == (
        "Done. See the link on screen for details"
    )


def test_nothing_to_say_yields_nothing():
    assert feed_all(SentenceBuffer(), ["", "  ", "**"]) == []
