"""AppTest-based tests for src/web/app.py.

NOTE on file-upload simulation:
  Streamlit 1.57.0's `streamlit.testing.v1.ChatInput` only supports
  `set_value(str)` — it does NOT expose an API to attach files.
  Therefore, tests that involve file attachments seed `session_state.messages`
  directly and verify the render/display path only.
  Handler unit logic (validate_file_types, extract_file_metadata) is covered
  exhaustively in test_handlers.py, which carries the bulk of the 80% coverage.
"""

from streamlit.testing.v1 import AppTest

APP_PATH = "C:/Users/dis19/source/ai-prototype/src/web/app.py"


# ---------------------------------------------------------------------------
# Task 4.1 — Fresh-start state
# ---------------------------------------------------------------------------


def test_app_fresh_start_messages_empty():
    # Arrange
    at = AppTest.from_file(APP_PATH)

    # Act
    at.run()

    # Assert
    assert at.session_state.messages == []


# ---------------------------------------------------------------------------
# Task 4.2 — Text submit adds user + assistant turns
# ---------------------------------------------------------------------------


def test_app_text_submit_appends_user_and_assistant_turns():
    # Arrange
    at = AppTest.from_file(APP_PATH)
    at.run()

    # Act
    at.chat_input[0].set_value("hola").run()

    # Assert
    messages = at.session_state.messages
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hola"
    assert messages[1]["role"] == "assistant"
    assert "hola" in messages[1]["content"]


# ---------------------------------------------------------------------------
# Task 4.3 — Two submits accumulate four messages
# ---------------------------------------------------------------------------


def test_app_two_submits_accumulate_four_messages():
    # Arrange
    at = AppTest.from_file(APP_PATH)
    at.run()

    # Act
    at.chat_input[0].set_value("hola").run()
    at.chat_input[0].set_value("mundo").run()

    # Assert
    assert len(at.session_state.messages) == 4


# ---------------------------------------------------------------------------
# Task 4.4 — Message schema includes files key
# ---------------------------------------------------------------------------


def test_app_message_schema_includes_files_key():
    # Arrange
    at = AppTest.from_file(APP_PATH)
    at.run()

    # Act
    at.chat_input[0].set_value("test").run()

    # Assert
    messages = at.session_state.messages
    assert len(messages) >= 1
    assert "files" in messages[0]
    assert messages[0]["files"] == []
