"""Runtime fixes for the Finance Bot Hermes container.

Hermes 0.17 ships both:
- top-level `cron` package with scheduler/jobs modules
- `plugins/cron` Hermes plugin package

The dashboard plugin loader can put `site-packages/plugins` on sys.path, which makes
`import cron` resolve to `plugins/cron` and breaks `/api/cron/jobs?profile=default`.
Import the real top-level package early so later imports reuse sys.modules['cron'].
"""

try:
    import cron  # noqa: F401
except Exception:
    # Do not block Python startup if Hermes changes this package later.
    pass
