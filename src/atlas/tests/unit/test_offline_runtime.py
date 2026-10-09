"""Runtime guard for Atlas's offline-first startup path."""

import socket
import sys
from types import SimpleNamespace
from typing import Any, List, Tuple
from unittest.mock import patch

import pytest

from atlas import main


def test_startup_does_not_attempt_network_access(
    monkeypatch: Any,
) -> None:
    """Fail if the normal startup path invokes Python networking APIs."""
    attempts: List[Tuple[Tuple[Any, ...], dict]] = []

    def block_network(*args: Any, **kwargs: Any) -> None:
        attempts.append((args, kwargs))
        raise AssertionError("Atlas attempted network access during startup")

    monkeypatch.setattr(socket, "socket", block_network)
    monkeypatch.setattr(socket, "create_connection", block_network)
    monkeypatch.setattr(socket, "getaddrinfo", block_network)
    from atlas import gui

    monkeypatch.setattr(gui.permissions, "is_elevated", lambda: False)

    original_application = gui.QtWidgets.QApplication

    def start_and_quit(arguments: Any) -> Any:
        """Create the real application and stop its event loop immediately."""
        application = original_application.instance()
        if application is None:
            application = original_application(arguments)
        gui.QtCore.QTimer.singleShot(0, application.quit)
        return application

    monkeypatch.setattr(
        gui,
        "QtWidgets",
        SimpleNamespace(QApplication=start_and_quit),
    )

    with patch.object(sys, "argv", ["atlas"]):
        with pytest.raises(SystemExit) as exit_info:
            main.main()

    assert attempts == []
    assert exit_info.value.code == 0
