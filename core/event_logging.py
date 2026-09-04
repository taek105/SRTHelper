import json
import logging
import os
import re
from contextvars import ContextVar, Token
from datetime import date, datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


LOG_RETENTION_DAYS = 28
SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")
_ROTATED_LOG_PATTERN = re.compile(
    r"^(?:events\.jsonl|error\.log)\.(\d{4}-\d{2}-\d{2})$"
)

_request_id: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)
_run_id: ContextVar[str | None] = ContextVar("run_id", default=None)

event_logger = logging.getLogger("ktx_helper.events")
error_logger = logging.getLogger("ktx_helper.errors")
event_logger.addHandler(logging.NullHandler())
error_logger.addHandler(logging.NullHandler())
event_logger.propagate = False
error_logger.propagate = False


def get_request_id() -> str | None:
    return _request_id.get()


def set_request_id(value: str) -> Token:
    return _request_id.set(value)


def reset_request_id(token: Token) -> None:
    _request_id.reset(token)


def get_run_id() -> str | None:
    return _run_id.get()


def set_run_id(value: str) -> Token:
    return _run_id.set(value)


def reset_run_id(token: Token) -> None:
    _run_id.reset(token)


def _timestamp() -> str:
    return datetime.now(SEOUL_TIMEZONE).isoformat(timespec="milliseconds")


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event_data = dict(getattr(record, "event_data", {}))
        payload = {
            "time": _timestamp(),
            **event_data,
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )


class ErrorFormatter(logging.Formatter):
    @staticmethod
    def _exception_summary(record: logging.LogRecord) -> str | None:
        if not record.exc_info:
            return None

        exception_type, exception, _traceback = record.exc_info
        message = " ".join(str(exception).splitlines()).strip()
        # Selenium exceptions may embed their own native stack trace in the
        # exception message. Keep only the useful description.
        message = message.split("Stacktrace:", 1)[0].strip()
        if message:
            return f"{exception_type.__name__}: {message}"
        return exception_type.__name__

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None) or "-"
        run_id = getattr(record, "run_id", None) or "-"
        record.correlation = f"request_id={request_id} run_id={run_id}"
        exception_summary = self._exception_summary(record)

        # The default logging formatter appends the complete traceback. It is
        # mostly framework plumbing for HTTP errors, so log a compact summary
        # instead without mutating the record for any other handlers.
        original_exc_info = record.exc_info
        original_exc_text = record.exc_text
        record.exc_info = None
        record.exc_text = None
        try:
            formatted = super().format(record)
        finally:
            record.exc_info = original_exc_info
            record.exc_text = original_exc_text

        if exception_summary:
            return f"{formatted} exception={exception_summary}"
        return formatted


def _remove_expired_logs(log_dir: Path, today: date | None = None) -> None:
    cutoff = (today or datetime.now(SEOUL_TIMEZONE).date()) - timedelta(
        days=LOG_RETENTION_DAYS
    )
    for path in log_dir.iterdir():
        match = _ROTATED_LOG_PATTERN.fullmatch(path.name)
        if match is None or not path.is_file():
            continue
        try:
            log_date = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if log_date <= cutoff:
            try:
                path.unlink()
            except OSError:
                # A cleanup failure must not prevent the application from starting.
                continue


class RetentionTimedRotatingFileHandler(TimedRotatingFileHandler):
    def _open(self):
        stream = super()._open()
        try:
            Path(self.baseFilename).chmod(0o600)
        except OSError:
            pass
        return stream

    def doRollover(self) -> None:
        super().doRollover()
        _remove_expired_logs(Path(self.baseFilename).parent)


def _replace_handler(
    logger: logging.Logger,
    handler: logging.Handler,
) -> None:
    for existing in list(logger.handlers):
        if getattr(existing, "_ktx_helper_handler", False):
            logger.removeHandler(existing)
            existing.close()
    handler._ktx_helper_handler = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def configure_logging(log_dir: str | Path | None = None) -> Path:
    configured_dir = log_dir or os.getenv("KTX_LOG_DIR", "logs")
    destination = Path(configured_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    try:
        destination.chmod(0o700)
    except OSError:
        pass
    _remove_expired_logs(destination)

    event_handler = RetentionTimedRotatingFileHandler(
        destination / "events.jsonl",
        when="midnight",
        interval=1,
        backupCount=LOG_RETENTION_DAYS,
        encoding="utf-8",
    )
    event_handler.suffix = "%Y-%m-%d"
    event_handler.setFormatter(JsonLineFormatter())
    _replace_handler(event_logger, event_handler)

    error_handler = RetentionTimedRotatingFileHandler(
        destination / "error.log",
        when="midnight",
        interval=1,
        backupCount=LOG_RETENTION_DAYS,
        encoding="utf-8",
    )
    error_handler.suffix = "%Y-%m-%d"
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(
        ErrorFormatter(
            "%(asctime)s %(levelname)s %(correlation)s %(message)s"
        )
    )
    _replace_handler(error_logger, error_handler)
    return destination


def shutdown_logging() -> None:
    for logger in (event_logger, error_logger):
        for handler in list(logger.handlers):
            if getattr(handler, "_ktx_helper_handler", False):
                logger.removeHandler(handler)
                handler.close()


def log_event(event: str, **fields: Any) -> None:
    event_data = {"event": event}
    request_id = get_request_id()
    run_id = get_run_id()
    if request_id:
        event_data["request_id"] = request_id
    if run_id:
        event_data["run_id"] = run_id
    event_data.update(
        {
            key: value
            for key, value in fields.items()
            if value is not None
            and key not in {"time", "event", "request_id", "run_id"}
        }
    )
    event_logger.info("", extra={"event_data": event_data})


def log_error(
    message: str,
    *,
    exc_info: bool = False,
    **fields: Any,
) -> None:
    details = " ".join(
        f"{key}={value}"
        for key, value in fields.items()
        if value is not None
    )
    if details:
        message = f"{message} ({details})"
    error_logger.error(
        message,
        exc_info=exc_info,
        extra={
            "request_id": get_request_id(),
            "run_id": get_run_id(),
        },
    )
