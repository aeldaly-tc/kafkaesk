import asyncio
from aiokafka.structs import TopicPartition
from .exceptions import SchemaRegistrationConflictException
import orjson
from typing import Dict, Any, List, TYPE_CHECKING, Optional, Tuple
from aiokafka import AIOKafkaProducer
from .kafka import KafkaTopicManager
from kafka import KafkaConsumer
from .utils import run_async, deep_compare


if TYPE_CHECKING:
    from .app import SchemaRegistration
else:
    SchemaRegistration = None


def _get_schema(
    kafka_servers: List[str], topic_id: str, schema_version: int
) -> Optional[Dict[str, Any]]:
    """
    The async driver kind of sucks so for some more custom things
    we need to use the sync variant
    """
    consumer = KafkaConsumer(
        bootstrap_servers=kafka_servers, enable_auto_commit=False, group_id="default",
    )
    part = TopicPartition(topic_id, 0)
    consumer.assign([part])
    consumer.seek_to_beginning(part)
    end_offset = consumer.end_offsets([part])[part]
    if end_offset <= 0:
        return None

    next_offset = 0

    found = None
    while end_offset > next_offset:
        msg = next(consumer)  # type: ignore
        next_offset = msg.offset + 1
        entry_schema_version = int(msg.key.decode("ascii"))
        if schema_version == entry_schema_version:
            found = orjson.loads(msg.value)
    return found


class SchemaManager:
    def __init__(self, kafka_servers: List[str], topic_prefix: str = ""):
        self._kafka_servers = kafka_servers
        self._producer = None
        self._topic_manager = KafkaTopicManager(kafka_servers, prefix=topic_prefix)
        self._topic_prefix = topic_prefix
        self._cached_schemas: Dict[Tuple[str, int], Dict[str, Any]] = {}

    async def __aenter__(self) -> "SchemaManager":
        await self.initialize()
        return self

    async def initialize(self) -> None:
        ...

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self.finalize()

    async def finalize(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def get_schema(self, schema_id: str, schema_version: int) -> Dict[str, Any]:
        key = (schema_id, schema_version)
        if key in self._cached_schemas:
            return self._cached_schemas[key]

        result = await run_async(
            _get_schema,
            self._kafka_servers,
            self._topic_manager.get_schema_topic_id(schema_id),
            schema_version,
        )
        if result is not None:
            self._cached_schemas[key] = result
        return result

    async def set_schema(
        self, schema_id: str, schema_version: int, schema: Dict[str, Any]
    ) -> None:
        producer = await self._get_producer()
        topic_id = self._topic_manager.get_schema_topic_id(schema_id)
        await (
            await producer.send(
                topic_id,
                key=str(schema_version).encode("ascii"),
                value=orjson.dumps(schema),
            )
        )

    async def _get_producer(self) -> AIOKafkaProducer:
        if self._producer is None:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._kafka_servers, loop=asyncio.get_event_loop()
            )
            await self._producer.start()
        return self._producer

    async def register(self, registration) -> None:
        topic_id = self._topic_manager.get_schema_topic_id(registration.id)
        if not await self._topic_manager.topic_exists(topic_id):
            await self._topic_manager.create_topic(
                topic_id,
                partitions=1,
                replicas=1,
                retention_ms=None,
                cleanup_policy="compact",
            )
            existing = None
        else:
            existing = await self.get_schema(registration.id, registration.version)

        if existing is not None:
            # check if conflicts... NEEDS SMARTS HERE
            if not deep_compare(
                existing["properties"], registration.model.schema()["properties"]
            ):
                raise SchemaRegistrationConflictException(
                    existing, registration.model.schema()
                )
        else:
            await self.set_schema(
                registration.id, registration.version, registration.model.schema()
            )