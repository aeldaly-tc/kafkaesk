from kafka.admin.client import KafkaAdminClient
from kafka import KafkaClient
from kafkaesk.utils import run_async
from kafka.admin import NewTopic
from typing import List, Optional, Dict, Any


class KafkaTopicManager:
    _admin_client: KafkaAdminClient
    _client: KafkaClient

    def __init__(self, bootstrap_servers: List[str], prefix: str = ""):
        self.prefix = prefix
        self._bootstrap_servers = bootstrap_servers

    def get_topic_id(self, topic: str) -> str:
        return f"{self.prefix}{topic}"

    def get_schema_topic_id(self, schema_name: str) -> str:
        return f"{self.prefix}__schema__{schema_name}"

    async def get_admin_client(self) -> KafkaAdminClient:
        if not hasattr(self, "_admin_client"):
            self._admin_client = await run_async(
                KafkaAdminClient, bootstrap_servers=self._bootstrap_servers
            )
        return self._admin_client

    async def topic_exists(self, topic: str) -> bool:
        if not hasattr(self, "_client"):
            self._client = await run_async(KafkaClient, self._bootstrap_servers)
        return topic in self._client.topic_partitions

    async def create_topic(
        self,
        topic: str,
        partitions: int = 1,
        replicas: int = 1,
        retention_ms: Optional[int] = None,
        cleanup_policy: Optional[str] = None,
    ) -> None:
        topic_configs: Dict[str, Any] = {}
        if retention_ms is not None:
            topic_configs["retention.ms"] = retention_ms
        if cleanup_policy is not None:
            topic_configs["cleanup.policy"] = cleanup_policy
        new_topic = NewTopic(topic, partitions, replicas, topic_configs=topic_configs)
        client = await self.get_admin_client()
        client.create_topics([new_topic])
        if self._client is not None:
            self._client.topic_partitions[topic] = [i for i in range(partitions)]
        return None