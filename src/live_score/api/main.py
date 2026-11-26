"""ASGI entrypoint: `uvicorn live_score.api.main:app --reload`."""

from live_score.api.app import create_app

app = create_app()
