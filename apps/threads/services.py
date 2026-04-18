from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, List

from django.utils import timezone

from apps.chat_events.models import Message
from apps.threads.models import Thread


@dataclass
class ThreadCluster:
    messages: List[Message]


class ThreadReconstructionService:
    gap_minutes = 90

    def rebuild_for_project(self, project_id: int) -> int:
        messages = list(
            Message.objects.filter(project_id=project_id, is_deleted=False)
            .select_related('domain', 'project', 'source')
            .order_by('timestamp', 'id')
        )
        clusters = self._cluster(messages)
        created = 0
        for cluster in clusters:
            first = cluster.messages[0]
            title = (first.normalized_text or 'Thread')[:120]
            thread, _ = Thread.objects.get_or_create(
                project=first.project,
                domain=first.domain,
                title=title,
                defaults={'reconstruction_hint': 'p1-rebuild'},
            )
            ids = [m.id for m in cluster.messages]
            Message.objects.filter(id__in=ids).update(thread=thread)
            thread.message_count = len(ids)
            thread.last_activity_at = cluster.messages[-1].timestamp
            thread.reconstruction_hint = 'p1-rebuild'
            thread.save(update_fields=['message_count', 'last_activity_at', 'reconstruction_hint', 'updated_at'])
            created += 1
        return created

    def _cluster(self, messages: List[Message]) -> List[ThreadCluster]:
        if not messages:
            return []
        clusters: List[ThreadCluster] = []
        current: List[Message] = [messages[0]]
        for msg in messages[1:]:
            prev = current[-1]
            if self._should_split(prev, msg):
                clusters.append(ThreadCluster(messages=current))
                current = [msg]
            else:
                current.append(msg)
        if current:
            clusters.append(ThreadCluster(messages=current))
        return clusters

    def _should_split(self, prev: Message, current: Message) -> bool:
        if prev.reply_to_message_id and current.reply_to_message_id == prev.telegram_message_id:
            return False
        gap = current.timestamp - prev.timestamp
        if gap > timedelta(minutes=self.gap_minutes):
            return True
        if prev.message_role != current.message_role and len((current.normalized_text or '').split()) > 20:
            return True
        if prev.source_id != current.source_id and gap > timedelta(minutes=20):
            return True
        return False
