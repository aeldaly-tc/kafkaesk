# kafkaesk

This project is meant to help facilitate easily publishing and subscribing to events with python and Kafka.

Guiding principal:
 - simple http, language agnostic contracts built on top of kafka.

Alternatives:
 - pure aiokafka: can be complex to scale correctly
 - guillotina_kafka: complex, tied to guillotina
 - faust: requires additional data layers, not language agnostic
 - confluent kafka + avro: close but ends up being like grpc. compilation for languages. No asyncio.

(consider this python project as syntatic sugar around these ideas)

## Publish

using pydantic but can be done with pure json

```python
import kafkaesk
from pydantic import BaseModel

app = kafkaesk.Application()

@app.schema("Content", version=1, retention=24 * 60 * 60)
class ContentMessage(BaseModel):
    foo: str


async def foobar():
    # ...
    # doing something in an async func
    await app.publish("content.edited.Resource", data=ContentMessage(foo="bar"))
```


## Subscribe


```python
import kafkaesk
from pydantic import BaseModel

app = kafkaesk.Application()

@app.schema("Content", version=1, retention=24 * 60 * 60)
class ContentMessage(BaseModel):
    foo: str


@app.subscribe('content.*')
async def get_messages(data: ContentMessage):
    print(f"{data.foo}")

```


## kafkaesk contract

This is just a library around using kafka.
Kafka itself does not enforce these concepts.

- every message must provide a json schema
- messages produced will be validated against json schema
- each topic will have only one schema
- a single schema can be used for multiple topics
- consumed message schema validation is up to the consumer


### schema storage

- json schemas are with topics prefixed with `__schema__`. So 'Content' schema will have `__schema__Content` topic.
- schemas are constant. You should never change a schema

### message format

```json
{
    "schema": "schema_name:1",
    "data": { ... }
}
```


# Worker

```bash
kafkaesk mymodule:app --kafka-servers=localhost:9092
```

Options:
 --kafka-servers: comma separated list of kafka servers
 --kafka-settings: json encoded options to be passed to https://aiokafka.readthedocs.io/en/stable/api.html#aiokafkaconsumer-class
 --topic-prefix: prefix to use for topics


## Application.publish

- stream_id: str: name of stream to send data to
- data: class that inherits from pydantic.BaseModel
- key: Optional[bytes]: key for message if it needs one

## Application.subscribe

- stream_id: str: fnmatch pattern of streams to subscribe to
- group: Optional[str]: consumer group id to use. Will use name of function if not provided
- max_partitions: Optional[int]: max number of 
- max_concurrency: Optional[int]: max number of 


## Application.schema

- id: str: id of the schema to store
- version: Optional[int]: version of schema to store
- streams: Optional[List[str]]: if streams are known ahead of time, we can pre-create them before we push data
- retention: Optional[int]: retention policy in seconds


## Dev

```bash
poetry install
```

Run tests:

```bash
docker run -p 2181:2181 -p 9092:9092 --env ADVERTISED_HOST=0.0.0.0 --env ADVERTISED_PORT=9092 spotify/kafka
KAFKA=localhost:9092 poetry run pytest tests
```

# Features

(or a todo here)

- [x] worker
- [ ] auto scaling/concurrency
    - automatically increase concurrency
    - automatically increase number of partitions
- [ ] service to inspect stats
- [ ] be able to handle manual commit use-case
- [ ] be able to reject commit/abort message handling
- [ ] prometheus
- [ ] automatic "connectors"