import json

import structlog

from api.core.logging import configure_logging


def test_logging_emits_json(capsys):
    configure_logging()
    log = structlog.get_logger()
    log.info("test.event", foo="bar", n=1)
    captured = capsys.readouterr().out.strip().splitlines()
    assert captured, "expected at least one log line"
    payload = json.loads(captured[-1])
    assert payload["event"] == "test.event"
    assert payload["foo"] == "bar"
    assert payload["n"] == 1
    assert payload["level"] == "info"
    assert "timestamp" in payload
