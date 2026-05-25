from langchain_community.document_loaders import YoutubeLoader


def load_youtube(url: str) -> list:
    loader = YoutubeLoader.from_youtube_url(url, add_video_info=True)
    return loader.load()
