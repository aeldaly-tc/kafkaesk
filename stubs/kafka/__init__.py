from typing import Dict, List, Optional

from kafka.structs import TopicPartition


class KafkaConsumer:
    def __init__(
        self,
        bootstrap_servers: List[str],
        enable_auto_commit: Optional[bool] = True,
        group_id: Optional[str] = None,
    ):
        ...

    def assign(self, parts: List[TopicPartition]) -> None:
        ...

    def seek_to_beginning(self, partition: TopicPartition) -> None:
        ...

    def end_offsets(self, parts: List[TopicPartition]) -> Dict[TopicPartition, int]:
        ...


class KafkaClient:
    topic_partitions: Dict[str, List[int]]