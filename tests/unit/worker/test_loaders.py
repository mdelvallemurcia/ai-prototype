"""Unit tests for src/worker/loaders/ — YouTube, PDF, and web document loaders."""

from unittest.mock import MagicMock, patch

from src.worker.loaders.pdf import load_pdf
from src.worker.loaders.web import load_web
from src.worker.loaders.youtube import load_youtube

# ---------------------------------------------------------------------------
# load_youtube
# ---------------------------------------------------------------------------


def test_load_youtube_calls_loader_with_correct_args():
    # Arrange
    url = "https://youtube.com/watch?v=abc"
    fake_docs = [MagicMock()]
    mock_loader = MagicMock()
    mock_loader.load.return_value = fake_docs

    # Act
    with patch(
        "src.worker.loaders.youtube.YoutubeLoader.from_youtube_url",
        return_value=mock_loader,
    ) as mock_from_url:
        result = load_youtube(url)

    # Assert
    mock_from_url.assert_called_once_with(url, add_video_info=True)
    mock_loader.load.assert_called_once()
    assert result is fake_docs


# ---------------------------------------------------------------------------
# load_pdf
# ---------------------------------------------------------------------------


def test_load_pdf_calls_loader_with_correct_path():
    # Arrange
    path = "/tmp/recipe.pdf"
    fake_docs = [MagicMock(), MagicMock()]
    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = fake_docs

    # Act
    with patch(
        "src.worker.loaders.pdf.PyPDFLoader",
        return_value=mock_loader_instance,
    ) as mock_loader_cls:
        result = load_pdf(path)

    # Assert
    mock_loader_cls.assert_called_once_with(path)
    mock_loader_instance.load.assert_called_once()
    assert result is fake_docs


# ---------------------------------------------------------------------------
# load_web
# ---------------------------------------------------------------------------


def test_load_web_calls_loader_with_correct_url():
    # Arrange
    url = "https://example.com/recipe"
    fake_docs = [MagicMock()]
    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = fake_docs

    # Act
    with patch(
        "src.worker.loaders.web.WebBaseLoader",
        return_value=mock_loader_instance,
    ) as mock_loader_cls:
        result = load_web(url)

    # Assert
    mock_loader_cls.assert_called_once_with(url)
    mock_loader_instance.load.assert_called_once()
    assert result is fake_docs
