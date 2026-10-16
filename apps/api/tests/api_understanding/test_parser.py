import json
import pytest

from app.api_understanding.normalizer import normalize_operations
from app.api_understanding.parser import SpecParseError, parse_spec


MINIMAL_VALID = json.dumps({
    "openapi": "3.0.0",
    "info": {"title": "X", "version": "1.0"},
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "responses": {"200": {"description": "ok"}},
            }
        }
    },
}).encode("utf-8")


def test_parse_minimal_ok():
    doc = parse_spec(MINIMAL_VALID)
    ops = normalize_operations(doc)
    assert len(ops) == 1
    assert ops[0]["method"] == "GET"
    assert ops[0]["path"] == "/pets"


def test_swagger2_rejected():
    with pytest.raises(SpecParseError):
        parse_spec(json.dumps({"swagger": "2.0", "info": {"title": "X", "version": "1"}, "paths": {}}).encode())


def test_remote_ref_rejected():
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "X", "version": "1"},
        "paths": {},
        "components": {"schemas": {"X": {"$ref": "https://evil.example/schema.yaml"}}},
    }
    with pytest.raises(SpecParseError):
        parse_spec(json.dumps(doc).encode())


def test_oversize_rejected():
    big = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "X", "version": "1"},
        "paths": {"/x": {"get": {"description": "a" * 10_000_000, "responses": {"200": {"description": "ok"}}}}},
    }).encode()
    with pytest.raises(SpecParseError):
        parse_spec(big)


def test_deterministic_ops():
    doc = parse_spec(MINIMAL_VALID)
    ops1 = normalize_operations(doc)
    ops2 = normalize_operations(doc)
    assert [o["operation_id"] for o in ops1] == [o["operation_id"] for o in ops2]
