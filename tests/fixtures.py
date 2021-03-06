import kafkaesk
import os
import pytest
import uuid


@pytest.fixture()
async def kafka():
    yield os.environ.get("KAFKA", "localhost:9092").split(":")


@pytest.fixture()
async def app(kafka):
    yield kafkaesk.Application(
        [f"{kafka[0]}:{kafka[1]}"],
        topic_prefix=uuid.uuid4().hex,
        kafka_settings={"metadata_max_age_ms": 500},
    )
