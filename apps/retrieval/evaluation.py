from decimal import Decimal

from .models import RetrievalEvaluationCase, RetrievalEvaluationRun, RetrievalEvaluationResult
from .search import get_search_engine


def evaluate_cases(run_name: str = "manual") -> RetrievalEvaluationRun:
    engine = get_search_engine()
    run = RetrievalEvaluationRun.objects.create(name=run_name)
    cases = RetrievalEvaluationCase.objects.all()
    total_recall = Decimal("0")
    total_mrr = Decimal("0")
    count = 0
    for case in cases:
        results = engine.search_corpus(
            case.query_text,
            project_id=case.project_id,
            domain_id=case.domain_id,
            retrieval_mode=case.retrieval_mode,
            source_id=case.source_id,
            limit=5,
        )
        retrieved_ids = [r.obj.id for r in results]
        expected = list(case.expected_corpus_entry_ids or [])
        hits = [i for i, rid in enumerate(retrieved_ids, start=1) if rid in expected]
        recall = Decimal(len(set(retrieved_ids) & set(expected)) / max(len(expected), 1))
        mrr = Decimal(1 / hits[0]) if hits else Decimal("0")
        RetrievalEvaluationResult.objects.create(
            run=run,
            case=case,
            retrieved_entry_ids=retrieved_ids,
            recall_at_5=recall,
            mrr=mrr,
            diagnostics={"expected": expected},
        )
        total_recall += recall
        total_mrr += mrr
        count += 1
    run.query_count = count
    if count:
        run.average_recall_at_5 = total_recall / count
        run.average_mrr = total_mrr / count
    run.summary = {"query_count": count}
    run.save(update_fields=["query_count", "average_recall_at_5", "average_mrr", "summary", "updated_at"])
    return run
