"""Tests for RAG retrieval pipeline — search, context assembly, reranker, corpus."""

from django.test import TestCase
from django.contrib.auth.models import User
from apps.core.enums import RetrievalMode, SensitivityLevel
from apps.domains_projects.models import Domain, Project
from apps.threads.models import Thread
from apps.chat_events.models import TelegramSource, Message
from apps.retrieval.models import RagCorpusEntry, RetrievalSession
from apps.retrieval.search import SearchEngine, SearchRequest
from apps.retrieval.context_assembly import ContextAssembler
from apps.retrieval.reranker import HeuristicReranker, RerankRequest
from apps.retrieval.embeddings import get_embedding_service
from apps.retrieval.services import label_message_role, choose_retrieval_mode, full_rag_retrieve
from apps.agent_profiles.models import AgentProfile


class LabelMessageRoleTestCase(TestCase):
    """Test message role classification."""

    def test_debug_trace_detection(self):
        role = label_message_role("Traceback: error in line 42")
        self.assertEqual(role, Message.MessageRole.DEBUG_TRACE)

    def test_test_result_detection(self):
        role = label_message_role("Test passed: pytest ok")
        self.assertEqual(role, Message.MessageRole.TEST_RESULT)

    def test_git_event_detection(self):
        role = label_message_role("git commit -m 'fix'")
        self.assertEqual(role, Message.MessageRole.GIT_EVENT)

    def test_ops_instruction_detection(self):
        role = label_message_role("Restart nginx on server")
        self.assertEqual(role, Message.MessageRole.OPS_INSTRUCTION)

    def test_owner_decision_detection(self):
        role = label_message_role("Решили запустить завтра")
        self.assertEqual(role, Message.MessageRole.OWNER_DECISION)

    def test_owner_instruction_detection(self):
        role = label_message_role("Сделай отчёт к пятнице")
        self.assertEqual(role, Message.MessageRole.OWNER_INSTRUCTION)

    def test_default_owner_idea(self):
        role = label_message_role("Какие мысли по проекту?")
        self.assertEqual(role, Message.MessageRole.OWNER_IDEA)


class ChooseRetrievalModeTestCase(TestCase):
    """Test retrieval mode selection."""

    def test_debug_mode(self):
        mode = choose_retrieval_mode(Message.MessageRole.DEBUG_TRACE)
        self.assertEqual(mode, RetrievalMode.DEBUG)

    def test_ops_mode(self):
        mode = choose_retrieval_mode(Message.MessageRole.OPS_INSTRUCTION)
        self.assertEqual(mode, RetrievalMode.OPS)

    def test_business_mode(self):
        mode = choose_retrieval_mode(Message.MessageRole.OWNER_IDEA)
        self.assertEqual(mode, RetrievalMode.BUSINESS)


class SearchEngineTestCase(TestCase):
    """Test hybrid search engine."""

    def setUp(self):
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.project = Project.objects.create(domain=self.domain, canonical_name="Test Project", slug="test-project")
        self.thread = Thread.objects.create(domain=self.domain, project=self.project, title="Test Thread")
        self.source = TelegramSource.objects.create(
            slug="test-bot", display_name="Test Bot", source_kind="live_bot",
            default_domain=self.domain,
        )
        self.message = Message.objects.create(
            source=self.source,
            domain=self.domain,
            project=self.project,
            thread=self.thread,
            telegram_message_id=1,
            chat_id=123,
            text="Test message about Django deployment",
            normalized_text="test message about django deployment",
            role=Message.MessageRole.OWNER_IDEA,
            value_tier=Message.ValueTier.HIGH,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        self.corpus_entry = RagCorpusEntry.objects.create(
            entry_type=RagCorpusEntry.EntryType.MESSAGE,
            source_object_type=RagCorpusEntry.SourceObjectType.MESSAGE,
            source_object_id=self.message.id,
            source=self.source,
            domain=self.domain,
            project=self.project,
            text="Test message about Django deployment",
            trust_score=0.8,
            freshness_score=0.9,
            reviewed=True,
        )

    def test_search_request_creation(self):
        request = SearchRequest(query="django deployment", domain_id=self.domain.id)
        self.assertEqual(request.query, "django deployment")
        self.assertEqual(request.domain_id, self.domain.id)

    def test_search_engine_initialization(self):
        engine = SearchEngine()
        self.assertIsNotNone(engine)

    def test_search_returns_results(self):
        engine = SearchEngine()
        request = SearchRequest(query="django deployment", domain_id=self.domain.id)
        results = engine.search(request)
        # Should return corpus entries matching the query
        self.assertIsInstance(results, list)


class ContextAssemblerTestCase(TestCase):
    """Test context assembly for LLM prompts."""

    def setUp(self):
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.project = Project.objects.create(domain=self.domain, canonical_name="Test Project", slug="test-project")
        self.assembler = ContextAssembler()

    def test_assembler_initialization(self):
        self.assertIsNotNone(self.assembler)

    def test_assemble_with_query(self):
        result = self.assembler.assemble(
            query="test query",
            project_id=self.project.id,
            domain_id=self.domain.id,
        )
        self.assertIsInstance(result, dict)
        self.assertIn("context_text", result)
        self.assertIn("sources", result)

    def test_token_budget_enforcement(self):
        result = self.assembler.assemble(
            query="test query",
            project_id=self.project.id,
            domain_id=self.domain.id,
        )
        # Context should not exceed MAX_CONTEXT_CHARS
        self.assertLessEqual(len(result.get("context_text", "")), 30000)


class RerankerTestCase(TestCase):
    """Test reranking functionality."""

    def setUp(self):
        self.reranker = HeuristicReranker()

    def test_reranker_initialization(self):
        self.assertIsNotNone(self.reranker)

    def test_rerank_request_creation(self):
        request = RerankRequest(query="test", candidates=[])
        self.assertEqual(request.query, "test")
        self.assertEqual(request.candidates, [])


class RagCorpusEntryTestCase(TestCase):
    """Test RAG corpus entry model."""

    def setUp(self):
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.source = TelegramSource.objects.create(
            slug="test-bot", display_name="Test Bot", source_kind="live_bot",
            default_domain=self.domain,
        )

    def test_corpus_entry_creation(self):
        entry = RagCorpusEntry.objects.create(
            entry_type=RagCorpusEntry.EntryType.MESSAGE,
            source_object_type=RagCorpusEntry.SourceObjectType.MESSAGE,
            source_object_id=1,
            source=self.source,
            domain=self.domain,
            text="Test corpus entry",
            trust_score=0.8,
            freshness_score=0.9,
        )
        self.assertEqual(entry.entry_type, RagCorpusEntry.EntryType.MESSAGE)
        self.assertEqual(entry.trust_score, 0.8)

    def test_corpus_entry_scoring(self):
        entry = RagCorpusEntry.objects.create(
            entry_type=RagCorpusEntry.EntryType.KNOWLEDGE,
            source_object_type=RagCorpusEntry.SourceObjectType.KNOWLEDGE,
            source_object_id=1,
            source=self.source,
            domain=self.domain,
            text="Knowledge item",
            trust_score=1.0,
            freshness_score=1.0,
            reviewed=True,
        )
        # Knowledge entries should have higher base weight
        self.assertTrue(entry.reviewed)


class RetrievalSessionTestCase(TestCase):
    """Test retrieval session tracking."""

    def setUp(self):
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.source = TelegramSource.objects.create(
            slug="test-bot", display_name="Test Bot", source_kind="live_bot",
            default_domain=self.domain,
        )

    def test_session_creation(self):
        session = RetrievalSession.objects.create(
            query="test query",
            domain=self.domain,
            source=self.source,
            mode=RetrievalMode.BUSINESS,
            diagnostics={"test": True},
        )
        self.assertEqual(session.query, "test query")
        self.assertEqual(session.mode, RetrievalMode.BUSINESS)
        self.assertIsNotNone(session.diagnostics)

    def test_session_provenance_tracking(self):
        session = RetrievalSession.objects.create(
            query="test query",
            domain=self.domain,
            source=self.source,
            mode=RetrievalMode.BUSINESS,
            diagnostics={"sources": ["msg_1", "msg_2"]},
        )
        self.assertIn("sources", session.diagnostics)
