"""Unit tests for src/web/handlers.py — pure logic, no Streamlit runtime needed."""

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.web import handlers
from src.web.handlers import (
    extract_file_metadata,
    stream_reply,
    to_langchain_messages,
    validate_file_types,
)
from tests.conftest import FakeUploadedFile

# ---------------------------------------------------------------------------
# SYSTEM_PROMPT content (WLI-04)
# ---------------------------------------------------------------------------


def test_system_prompt_contains_mealmate_identity():
    # Arrange / Act — module-level constant, just inspect it

    # Assert
    assert "MealMate" in handlers.SYSTEM_PROMPT


def test_system_prompt_contains_domain_keywords():
    # Arrange / Act

    # Assert
    assert any(w in handlers.SYSTEM_PROMPT for w in ["recipe", "recipes", "meal", "meals"])


# ---------------------------------------------------------------------------
# to_langchain_messages (WLI-05, WLI-06, WLI-10)
# ---------------------------------------------------------------------------


def test_to_langchain_messages_empty_history_returns_only_system_message():
    # Arrange
    history: list[dict] = []

    # Act
    result = to_langchain_messages(history)

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], SystemMessage)
    assert result[0].content == handlers.SYSTEM_PROMPT


def test_to_langchain_messages_single_user_turn_maps_to_human_message():
    # Arrange
    history = [{"role": "user", "content": "What can I cook?", "files": []}]

    # Act
    result = to_langchain_messages(history)

    # Assert
    assert len(result) == 2
    assert isinstance(result[0], SystemMessage)
    assert isinstance(result[1], HumanMessage)
    assert result[1].content == "What can I cook?"


def test_to_langchain_messages_alternating_turns_preserves_order():
    # Arrange
    history = [
        {"role": "user", "content": "Hello", "files": []},
        {"role": "assistant", "content": "Hi there!", "files": []},
        {"role": "user", "content": "What's for dinner?", "files": []},
    ]

    # Act
    result = to_langchain_messages(history)

    # Assert
    assert len(result) == 4
    assert isinstance(result[0], SystemMessage)
    assert isinstance(result[1], HumanMessage)
    assert result[1].content == "Hello"
    assert isinstance(result[2], AIMessage)
    assert result[2].content == "Hi there!"
    assert isinstance(result[3], HumanMessage)
    assert result[3].content == "What's for dinner?"


def test_to_langchain_messages_first_element_always_system_message():
    # Arrange
    history = [{"role": "assistant", "content": "Hello!", "files": []}]

    # Act
    result = to_langchain_messages(history)

    # Assert
    assert isinstance(result[0], SystemMessage)
    assert result[0].content == handlers.SYSTEM_PROMPT


def test_to_langchain_messages_ignores_files_key_in_message_dict():
    # Arrange
    history = [
        {
            "role": "user",
            "content": "What's this?",
            "files": [{"name": "img.png", "bytes": b"fake-image-data"}],
        }
    ]

    # Act
    result = to_langchain_messages(history)

    # Assert
    human_msg = result[1]
    assert isinstance(human_msg, HumanMessage)
    assert human_msg.content == "What's this?"
    # No file bytes or filename should appear in any message
    for msg in result:
        assert b"fake-image-data" not in str(msg.content).encode()
        assert "img.png" not in str(msg.content)


# ---------------------------------------------------------------------------
# stream_reply (WLI-07)
# ---------------------------------------------------------------------------


class FakeChunk:
    """Minimal chunk with a content attribute."""

    def __init__(self, content: str | None) -> None:
        self.content = content


class FakeChunkNoContent:
    """Chunk with no content attribute at all."""

    pass


def test_stream_reply_yields_ordered_text_chunks():
    # Arrange
    fake_model = MagicMock()
    messages = [SystemMessage(content="sys")]
    chunks = [FakeChunk("Here "), FakeChunk("is "), FakeChunk("pasta.")]
    fake_model.stream.return_value = iter(chunks)

    # Act
    result = list(stream_reply(fake_model, messages))

    # Assert
    assert result == ["Here ", "is ", "pasta."]
    fake_model.stream.assert_called_once_with(messages)


def test_stream_reply_skips_empty_content_chunks():
    # Arrange
    fake_model = MagicMock()
    chunks = [FakeChunk(""), FakeChunk("Hello"), FakeChunk(None), FakeChunk(" world")]
    fake_model.stream.return_value = iter(chunks)

    # Act
    result = list(stream_reply(fake_model, []))

    # Assert
    assert result == ["Hello", " world"]


def test_stream_reply_skips_missing_content_attribute():
    # Arrange
    fake_model = MagicMock()
    chunks = [FakeChunkNoContent(), FakeChunk("OK")]
    fake_model.stream.return_value = iter(chunks)

    # Act — must not raise AttributeError
    result = list(stream_reply(fake_model, []))

    # Assert
    assert result == ["OK"]


def test_stream_reply_calls_stream_once_with_messages():
    # Arrange
    fake_model = MagicMock()
    messages = [HumanMessage(content="test")]
    fake_model.stream.return_value = iter([FakeChunk("done")])

    # Act
    list(stream_reply(fake_model, messages))

    # Assert
    fake_model.stream.assert_called_once_with(messages)


# ---------------------------------------------------------------------------
# extract_file_metadata
# ---------------------------------------------------------------------------


def test_extract_file_metadata_image_returns_thumbnail(fake_png_file):
    # Arrange — fake_png_file provided by conftest fixture

    # Act
    result = extract_file_metadata(fake_png_file)

    # Assert
    assert result["name"] == "photo.png"
    assert result["type"] == "image/png"
    assert result["size"] == fake_png_file.size
    assert "thumbnail" in result
    assert isinstance(result["thumbnail"], str)
    assert result["thumbnail"].startswith("data:image/png;base64,")


def test_extract_file_metadata_pdf_returns_no_thumbnail(fake_pdf_file):
    # Arrange — fake_pdf_file provided by conftest fixture

    # Act
    result = extract_file_metadata(fake_pdf_file)

    # Assert
    assert result["name"] == "recipe.pdf"
    assert result["type"] == "application/pdf"
    assert result["size"] == fake_pdf_file.size
    assert result.get("thumbnail") is None


def test_extract_file_metadata_idempotent(fake_png_file):
    # Arrange — same fake file, called twice

    # Act
    result_a = extract_file_metadata(fake_png_file)
    result_b = extract_file_metadata(fake_png_file)

    # Assert
    assert result_a == result_b


# ---------------------------------------------------------------------------
# validate_file_types
# ---------------------------------------------------------------------------


def test_validate_file_types_allowed_types_pass():
    # Arrange
    allowed_mime_types = [
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "application/pdf",
    ]
    files = [
        FakeUploadedFile(f"file{i}", mime, b"data") for i, mime in enumerate(allowed_mime_types)
    ]

    # Act
    result = validate_file_types(files)

    # Assert
    assert len(result) == len(allowed_mime_types)


def test_validate_file_types_unsupported_type_excluded():
    # Arrange
    plain_text_file = FakeUploadedFile("readme.txt", "text/plain", b"hello")

    # Act
    result = validate_file_types([plain_text_file])

    # Assert — result-based, does NOT raise; unsupported type simply absent
    assert len(result) == 0
