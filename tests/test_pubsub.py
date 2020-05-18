import pytest
import pydantic
import asyncio

pytestmark = pytest.mark.asyncio


async def test_consume_message(app):
    consumed = []

    @app.schema("Foo", streams=["foo.bar"])
    class Foo(pydantic.BaseModel):
        bar: str

    @app.subscribe("foo.bar")
    async def consume(data: Foo):
        consumed.append(data)

    async with app:
        await app.publish("foo.bar", Foo(bar="1"))
        await app.flush()
        await app.consume_for(1, seconds=2)

    assert len(consumed) == 1


async def test_consume_many_messages(app):
    consumed = []

    @app.schema("Foo", streams=["foo.bar"])
    class Foo(pydantic.BaseModel):
        bar: str

    @app.subscribe("foo.bar")
    async def consume(data: Foo):
        consumed.append(data)

    async with app:
        fut = asyncio.create_task(app.consume_for(1000, seconds=3))
        await asyncio.sleep(0.1)
        for idx in range(1000):
            await app.publish("foo.bar", Foo(bar=str(idx)))
        await app.flush()
        await fut

    assert len(consumed) == 1000


async def test_not_consume_message_that_does_not_match(app):
    consumed = []

    @app.schema("Foo", streams=["foo.bar"])
    class Foo(pydantic.BaseModel):
        bar: str

    @app.subscribe("foo.bar")
    async def consume(data: Foo):
        consumed.append(data)

    async with app:
        await app.publish("foo.bar1", Foo(bar="1"))
        await app.flush()
        await app.consume_for(1, seconds=1)

    assert len(consumed) == 0


async def test_multiple_subscribers_different_models(app):
    consumed1 = []
    consumed2 = []

    @app.schema("Foo", version=1, streams=["foo.bar"])
    class Foo1(pydantic.BaseModel):
        bar: str

    @app.schema("Foo", version=2)
    class Foo2(pydantic.BaseModel):
        foo: str
        bar: str

    @app.subscribe("foo.bar")
    async def consume1(data: Foo1):
        consumed1.append(data)

    @app.subscribe("foo.bar")
    async def consume2(data: Foo2):
        consumed2.append(data)

    async with app:
        fut = asyncio.create_task(app.consume_for(1, seconds=2))
        await asyncio.sleep(0.2)

        await app.publish("foo.bar", Foo1(bar="1"))
        await app.publish("foo.bar", Foo2(foo="1", bar="1"))
        await app.flush()
        await fut

    assert len(consumed1) == 1
    assert len(consumed2) == 1
    assert isinstance(consumed1[0], Foo1)
    assert isinstance(consumed2[0], Foo2)