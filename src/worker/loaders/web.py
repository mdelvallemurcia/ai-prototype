from langchain_community.document_loaders import WebBaseLoader


def load_web(url: str) -> list:
    loader = WebBaseLoader(url)
    return loader.load()
