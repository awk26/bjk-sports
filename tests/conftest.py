import sys
from pathlib import Path

_src = str(Path(__file__).resolve().parent.parent.parent)
if _src not in sys.path:
    sys.path.insert(0, _src)

import pytest
from flask import Flask
from werkzeug.test import Client

from bjk_athletes.main import app as _app
from bjk_athletes.models import USERS, COACHES, ATHLETES, reset_tokens, init_default_users
import bjk_athletes.models as _models_module


@pytest.fixture()
def app() -> Flask:
    _reset_globals()
    _app.config.update(
        TESTING=True,
        SECRET_KEY="testing-secret-key",
        WTF_CSRF_ENABLED=False,
    )
    ctx = _app.app_context()
    ctx.push()
    yield _app
    ctx.pop()


@pytest.fixture()
def client(app: Flask) -> Client:
    return app.test_client()


@pytest.fixture()
def admin_client(client: Client) -> Client:
    with client.session_transaction() as sess:
        sess["user"] = {
            "username": "admin",
            "role": "admin",
            "name": "Admin User",
        }
    return client


@pytest.fixture()
def coach_client(client: Client) -> Client:
    with client.session_transaction() as sess:
        sess["user"] = {
            "username": "coach",
            "role": "coach",
            "name": "Coach User",
        }
    return client


def _reset_globals() -> None:
    init_default_users()
    ATHLETES.clear()
    reset_tokens.clear()
    _models_module._athlete_counter = 0
