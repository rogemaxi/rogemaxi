"""Structured JSONL job/activity logging with secret redaction (milestone A)."""
import json, re, threading, traceback
from pathlib import Path
from engine import workspace, utcnow

_SECRET_PATTERNS = [
    re.compile(r'sk-[A-Za-z0-9_\-]{8,}'),                      # OpenAI-style keys
    re.compile(r'(?i)(api[_-]?key|authorization|bearer|password|secret|token)(["\'\s:=]+)([^\s"\',}]{6,})'),
]
_lock = threading.Lock()


def redact(value):
    """Remove anything that looks like a credential from text or nested data."""
    if isinstance(value, str):
        s = _SECRET_PATTERNS[0].sub('[REDACTED_KEY]', value)
        s = _SECRET_PATTERNS[1].sub(lambda m: m.group(1) + m.group(2) + '[REDACTED]', s)
        return s
    if isinstance(value, dict):
        return {k: ('[REDACTED]' if re.search(r'(?i)key|secret|token|password', str(k))
                    and isinstance(v, str) and v else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


class JobLog:
    """Append-only structured log for one job, mirrored to the activity log."""

    def __init__(self, root, job_id):
        self.root = workspace(root)
        self.job_id = job_id
        self.path = self.root / 'logs' / f'job_{job_id}.jsonl'
        self.activity = self.root / 'logs' / 'activity.jsonl'

    def event(self, level, role, message, **data):
        rec = {'ts': utcnow(), 'job': self.job_id, 'level': level, 'role': role,
               'message': redact(str(message)), 'data': redact(data)}
        line = json.dumps(rec, default=str) + '\n'
        with _lock:
            for p in (self.path, self.activity):
                with open(p, 'a', encoding='utf-8') as f:
                    f.write(line)
        return rec

    def info(self, role, message, **data):
        return self.event('INFO', role, message, **data)

    def warn(self, role, message, **data):
        return self.event('WARN', role, message, **data)

    def error(self, role, message, exc=None, **data):
        if exc is not None:
            data['exception'] = f'{type(exc).__name__}: {exc}'
            data['traceback'] = traceback.format_exc(limit=6)
        return self.event('ERROR', role, message, **data)

    def read(self):
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding='utf-8').splitlines() if l.strip()]


def activity(root, role, message, level='INFO', **data):
    return JobLog(root, 'activity').event(level, role, message, **data)


def read_activity(root, limit=500):
    p = workspace(root) / 'logs' / 'activity.jsonl'
    if not p.exists():
        return []
    lines = p.read_text(encoding='utf-8').splitlines()[-limit:]
    out = []
    for l in lines:
        try:
            out.append(json.loads(l))
        except ValueError:
            continue
    return out
