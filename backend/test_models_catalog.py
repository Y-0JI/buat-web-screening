"""Test katalog model AI (tanpa jaringan).

Jalan: ./.venv/bin/python test_models_catalog.py
"""

import sys

from app.routers.models import normalize_model, filter_tool_models


def test_normalize():
    raw = {
        "id": "openai/gpt-5",
        "owned_by": "openai",
        "capabilities": {"vision": True, "tools": True, "reasoning": True, "search": True,
                         "contextWindow": 400000},
    }
    m = normalize_model(raw)
    assert m["id"] == "openai/gpt-5"
    assert m["provider"] == "openai"
    assert m["provider_label"] == "OpenAI"
    assert m["capabilities"]["tools"] is True
    assert m["context_window"] == 400000


def test_normalize_unknown_provider():
    m = normalize_model({"id": "x", "owned_by": "weird", "capabilities": {}})
    assert m["provider_label"] == "Weird"
    assert m["capabilities"]["tools"] is False


def test_filter_tools_only():
    models = [
        normalize_model({"id": "a", "owned_by": "c", "capabilities": {"tools": True}}),
        normalize_model({"id": "b", "owned_by": "c", "capabilities": {"tools": False}}),
        normalize_model({"id": "d", "owned_by": "c", "capabilities": {}}),
    ]
    out = filter_tool_models(models)
    assert [m["id"] for m in out] == ["a"], out


def main():
    test_normalize()
    test_normalize_unknown_provider()
    test_filter_tools_only()
    print("OK: test_models_catalog lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
