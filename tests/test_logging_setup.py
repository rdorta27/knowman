import json
import logging

from knowman.logging_setup import _JsonFormatter


def test_json_formatter_produces_parseable_json_with_expected_keys():
    record = logging.LogRecord(
        name="knowman.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="something happened",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {"job_id": 42}

    line = _JsonFormatter().format(record)
    payload = json.loads(line)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "knowman.test"
    assert payload["message"] == "something happened"
    assert payload["job_id"] == 42
