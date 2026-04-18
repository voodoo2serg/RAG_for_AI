
from dataclasses import dataclass
from typing import List

@dataclass
class RerankRequest:
    query: str
    retrieval_mode: str
    source_slug: str = ""

class BaseReranker:
    def rerank(self, request: RerankRequest, results: List):
        return results

class HeuristicReranker(BaseReranker):
    def rerank(self, request: RerankRequest, results: List):
        q = (request.query or "").lower()
        boosted = []
        for item in results:
            score = item.score
            text = f"{getattr(item.obj, 'title', '')} {getattr(item.obj, 'text', '')}".lower()
            if request.source_slug and getattr(getattr(item.obj, 'source', None), 'slug', '') == request.source_slug:
                score *= 1.03
            if q and q in text:
                score *= 1.05
            item.score = score
            boosted.append(item)
        return sorted(boosted, key=lambda x: x.score, reverse=True)

def get_reranker():
    return HeuristicReranker()
