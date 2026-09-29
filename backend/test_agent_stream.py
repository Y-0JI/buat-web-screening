"""Test agen streaming dengan klien OpenAI palsu (tanpa jaringan).

Jalan: ./.venv/bin/python test_agent_stream.py
"""

import asyncio
import sys
from types import SimpleNamespace as NS

import app.ai.agent as agent


def _chunk(content=None, reasoning=None, tool_calls=None, finish=None):
    delta = NS(content=content, reasoning_content=reasoning, tool_calls=tool_calls)
    return NS(choices=[NS(delta=delta, finish_reason=finish)])


class _FakeStream:
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        async def gen():
            for c in self._chunks:
                yield c
        return gen()


class _FakeCompletions:
    def __init__(self, streams):
        self._streams = list(streams)

    async def create(self, **kwargs):
        return _FakeStream(self._streams.pop(0))


class _FakeClient:
    def __init__(self, streams):
        self.chat = NS(completions=_FakeCompletions(streams))


def _tc(index, id=None, name=None, args=None):
    return NS(index=index, id=id, function=NS(name=name, arguments=args))


async def _test_simple_tokens():
    streams = [[_chunk(content="Halo"), _chunk(content=" dunia"), _chunk(finish="stop")]]
    agent.get_async_client = lambda: _FakeClient(streams)
    events = [e async for e in agent.stream_agent([{"role": "user", "content": "hai"}], "m")]
    assert events[-1]["type"] == "done", events
    assert events[-1]["content"] == "Halo dunia", events[-1]
    assert [e["type"] for e in events].count("token") == 2


async def _test_reasoning_streamed():
    streams = [[_chunk(reasoning="mikir"), _chunk(content="ok"), _chunk(finish="stop")]]
    agent.get_async_client = lambda: _FakeClient(streams)
    events = [e async for e in agent.stream_agent([{"role": "user", "content": "hai"}], "m")]
    assert any(e["type"] == "reasoning" and e["delta"] == "mikir" for e in events)
    assert events[-1]["reasoning"] == "mikir"


async def _test_tool_round():
    streams = [
        [_chunk(tool_calls=[_tc(0, id="c1", name="search_stocks", args='{"q":"BCA"}')], finish="tool_calls")],
        [_chunk(content="Hasilnya BBCA"), _chunk(finish="stop")],
    ]
    agent.get_async_client = lambda: _FakeClient(streams)

    async def fake_run(name, args):
        return {"query": args.get("q"), "results": [{"stock_code": "BBCA"}]}

    orig = agent.run_tool
    agent.run_tool = fake_run
    try:
        events = [e async for e in agent.stream_agent([{"role": "user", "content": "cari BCA"}], "m")]
    finally:
        agent.run_tool = orig
    types = [e["type"] for e in events]
    assert "tool_start" in types and "tool_result" in types, types
    assert events[-1]["content"] == "Hasilnya BBCA", events[-1]
    assert events[-1]["tool_calls"][0]["name"] == "search_stocks"


def main():
    asyncio.run(_test_simple_tokens())
    asyncio.run(_test_reasoning_streamed())
    asyncio.run(_test_tool_round())
    print("OK: test_agent_stream lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
