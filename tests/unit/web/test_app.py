"""AppTest-based tests for src/web/app.py.

NOTE on file-upload simulation:
  Streamlit 1.57.0's `streamlit.testing.v1.ChatInput` only supports
  `set_value(str)` — it does NOT expose an API to attach files.
  Therefore, tests that involve file attachments seed `session_state.messages`
  directly and verify the render/display path only.
  Handler unit logic (validate_file_types, extract_file_metadata) is covered
  exhaustively in test_handlers.py, which carries the bulk of the 80% coverage.

NOTE on AppTest patching strategy:
  We patch `src.web.handlers.stream_reply` using side_effect (not return_value) so a
  fresh iterator is produced for each call. This avoids iterator exhaustion when
  AppTest re-runs the script.
  `monkeypatch.setenv("MEALMATE_NVIDIA_API_KEY", "test-key")` ensures the cached
  container constructs without raising on an empty API key.
  AppTest.from_file requires at.run() before at.chat_input[0] is accessible.
"""

from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage
from streamlit.testing.v1 import AppTest

APP_PATH = "C:/Users/dis19/source/ai-prototype/src/web/app.py"


def _make_stream(*chunks):
    """Return a side_effect function that yields fresh chunks on each call."""

    def _side_effect(chat_model, messages):
        yield from chunks

    return _side_effect


# ---------------------------------------------------------------------------
# Task 4.1 — Fresh-start state
# ---------------------------------------------------------------------------


def test_app_fresh_start_messages_empty(monkeypatch):
    # Arrange
    monkeypatch.setenv("MEALMATE_NVIDIA_API_KEY", "test-key")
    at = AppTest.from_file(APP_PATH)

    # Act
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream()):
        at.run()

    # Assert
    assert at.session_state.messages == []


# ---------------------------------------------------------------------------
# WLI-08 — streamed assistant reply replaces echo
# ---------------------------------------------------------------------------


def test_app_submit_produces_streamed_assistant_reply(monkeypatch):
    # Arrange
    monkeypatch.setenv("MEALMATE_NVIDIA_API_KEY", "test-key")
    at = AppTest.from_file(APP_PATH)
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream()):
        at.run()

    # Act
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream("Try ", "carbonara")):
        at.chat_input[0].set_value("What should I eat?").run()

    # Assert
    messages = at.session_state.messages
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"] == "Try carbonara"
    assert "Echo" not in messages[-1]["content"]


def test_app_submit_persists_both_turns(monkeypatch):
    # Arrange
    monkeypatch.setenv("MEALMATE_NVIDIA_API_KEY", "test-key")
    at = AppTest.from_file(APP_PATH)
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream()):
        at.run()

    # Act
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream("Try ", "carbonara")):
        at.chat_input[0].set_value("What should I eat?").run()

    # Assert
    messages = at.session_state.messages
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"]  # non-empty


# ---------------------------------------------------------------------------
# WLI-09 — snapshot ordering: user turn is last human message before LLM call
# ---------------------------------------------------------------------------


def test_app_user_message_is_last_human_message_before_llm_call(monkeypatch):
    # Arrange
    monkeypatch.setenv("MEALMATE_NVIDIA_API_KEY", "test-key")
    at = AppTest.from_file(APP_PATH)
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream()):
        at.run()

    captured_messages = []

    def fake_stream_reply(chat_model, messages):
        captured_messages.extend(messages)
        yield "ok"

    # Act
    with patch("src.web.handlers.stream_reply", side_effect=fake_stream_reply):
        at.chat_input[0].set_value("pasta please").run()

    # Assert — last message passed to stream_reply is the user's HumanMessage
    assert len(captured_messages) >= 2
    last_msg = captured_messages[-1]
    assert isinstance(last_msg, HumanMessage)
    assert last_msg.content == "pasta please"
    # No AIMessage for a pending (un-generated) assistant reply
    assert not any(isinstance(m, AIMessage) for m in captured_messages)


# ---------------------------------------------------------------------------
# Message schema includes files key
# ---------------------------------------------------------------------------


def test_app_message_schema_includes_files_key(monkeypatch):
    # Arrange
    monkeypatch.setenv("MEALMATE_NVIDIA_API_KEY", "test-key")
    at = AppTest.from_file(APP_PATH)
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream()):
        at.run()

    # Act
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream("ok")):
        at.chat_input[0].set_value("test").run()

    # Assert
    messages = at.session_state.messages
    assert len(messages) >= 1
    assert "files" in messages[0]
    assert messages[0]["files"] == []


# ---------------------------------------------------------------------------
# Two submits accumulate four messages
# ---------------------------------------------------------------------------


def test_app_two_submits_accumulate_four_messages(monkeypatch):
    # Arrange
    monkeypatch.setenv("MEALMATE_NVIDIA_API_KEY", "test-key")
    at = AppTest.from_file(APP_PATH)
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream()):
        at.run()

    # Act
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream("reply1")):
        at.chat_input[0].set_value("hola").run()
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream("reply2")):
        at.chat_input[0].set_value("mundo").run()

    # Assert
    assert len(at.session_state.messages) == 4


# ---------------------------------------------------------------------------
# W-01 / S-01 — exception fallback returns friendly error message
# ---------------------------------------------------------------------------


def test_app_submit_exception_returns_friendly_error(monkeypatch):
    # Arrange
    monkeypatch.setenv("MEALMATE_NVIDIA_API_KEY", "test-key")
    at = AppTest.from_file(APP_PATH)
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream()):
        at.run()

    # Act — stream_reply raises, triggering the except block in app.py
    with patch("src.web.handlers.stream_reply", side_effect=Exception("boom")):
        at.chat_input[0].set_value("What should I cook?").run()

    # Assert — the friendly error string is persisted as the last assistant message
    messages = at.session_state.messages
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"] == (
        "Sorry, I could not reach the AI service. Check your API key and try again."
    )


# ---------------------------------------------------------------------------
# S-02 — empty submission does not append any message (st.stop() guard)
# ---------------------------------------------------------------------------


def test_app_empty_submission_does_not_append_message(monkeypatch):
    # Arrange
    monkeypatch.setenv("MEALMATE_NVIDIA_API_KEY", "test-key")
    at = AppTest.from_file(APP_PATH)
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream()):
        at.run()

    # Act — submit empty text (no files can be attached via AppTest API)
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream()):
        at.chat_input[0].set_value("").run()

    # Assert — st.stop() fires before any message is appended
    assert at.session_state.messages == []


# ---------------------------------------------------------------------------
# Regression: user message must be rendered inline (without st.rerun)
# ---------------------------------------------------------------------------


def test_app_submit_renders_user_message_in_same_run(monkeypatch):
    """After submit, the user turn must appear as a rendered chat_message in
    the SAME script run — not only in session_state.

    The bug: history-render loop runs at top-of-script before the new user turn
    is appended, and no st.rerun() is called, so the user message was invisible
    until the next interaction.

    Assertion strategy: after one submit we expect at least two chat_message
    blocks on the page. The first rendered chat_message with role 'user' must
    contain the submitted text in its markdown children.
    """
    # Arrange
    monkeypatch.setenv("MEALMATE_NVIDIA_API_KEY", "test-key")
    at = AppTest.from_file(APP_PATH)
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream()):
        at.run()

    # Act — submit a text message
    with patch("src.web.handlers.stream_reply", side_effect=_make_stream("Nice choice!")):
        at.chat_input[0].set_value("I want pasta").run()

    # Assert — a rendered user chat_message with the submitted text must exist
    user_blocks = [cm for cm in at.chat_message if cm.name == "user"]
    assert user_blocks, "No rendered user chat_message block found in this run"
    user_markdowns = [md.value for cm in user_blocks for md in cm.markdown]
    assert any("I want pasta" in md for md in user_markdowns), (
        f"Submitted user text not found in rendered user chat_message markdown. "
        f"Rendered user markdown: {user_markdowns}"
    )
