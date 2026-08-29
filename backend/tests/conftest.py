from __future__ import annotations

import pytest

from gateway.modules.m6_telegram.db import LogDB


@pytest.fixture
def db(tmp_path):
    d = LogDB(tmp_path / "pilot.sqlite")
    yield d
    d.close()