from dataclasses import asdict

from .search import get_search_engine


def build_corpus_diagnostics(query: str, **kwargs):
    engine = get_search_engine()
    return engine.diagnostics(query=query, **kwargs)
