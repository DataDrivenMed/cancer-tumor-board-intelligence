from __future__ import annotations

import json

from services.production_evidence_config import bool_env, load_channel_payload


def test_unconfigured_channel_is_fail_closed(monkeypatch):
    monkeypatch.delenv("GUIDELINE_EVIDENCE_JSON", raising=False)
    monkeypatch.delenv("GUIDELINE_EVIDENCE_PATH", raising=False)
    payload, status = load_channel_payload("guideline")
    assert payload is None
    assert status.configured is False
    assert status.loaded is False
    assert status.error is None


def test_inline_json_is_loaded_without_exposing_secret(monkeypatch):
    monkeypatch.setenv("MOLECULAR_EVIDENCE_JSON", json.dumps({"records": []}))
    monkeypatch.delenv("MOLECULAR_EVIDENCE_PATH", raising=False)
    payload, status = load_channel_payload("molecular")
    assert payload == {"records": []}
    assert status.configured is True
    assert status.loaded is False
    assert status.configuration_origin == "env:MOLECULAR_EVIDENCE_JSON"


def test_invalid_inline_json_fails_closed(monkeypatch):
    monkeypatch.setenv("SAFETY_EVIDENCE_JSON", "{not-json")
    monkeypatch.delenv("SAFETY_EVIDENCE_PATH", raising=False)
    payload, status = load_channel_payload("safety")
    assert payload is None
    assert status.configured is True
    assert status.loaded is False
    assert status.error and "JSONDecodeError" in status.error


def test_missing_path_fails_closed(monkeypatch, tmp_path):
    monkeypatch.delenv("TRANSLATIONAL_EVIDENCE_JSON", raising=False)
    monkeypatch.setenv("TRANSLATIONAL_EVIDENCE_PATH", str(tmp_path / "missing.json"))
    payload, status = load_channel_payload("translational")
    assert payload is None
    assert status.configured is True
    assert status.loaded is False
    assert status.error


def test_bool_env(monkeypatch):
    monkeypatch.setenv("FEATURE_X", "true")
    assert bool_env("FEATURE_X") is True
    monkeypatch.setenv("FEATURE_X", "0")
    assert bool_env("FEATURE_X", default=True) is False
    monkeypatch.delenv("FEATURE_X", raising=False)
    assert bool_env("FEATURE_X", default=True) is True
