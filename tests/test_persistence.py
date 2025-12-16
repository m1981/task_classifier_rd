import pytest
import tempfile
import os
from services.repository import SqliteRepository, TriageService


def test_data_survives_app_restart():
    """
    SCENARIO: User adds data, closes app, reopens app.
    This validates that we aren't accidentally relying on Python memory.
    """
    # 1. Create a physical temp file
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # --- SESSION 1: The "Morning" Session ---
        repo1 = SqliteRepository(path)
        service1 = TriageService(repo1)

        service1.add_to_inbox("Morning Idea")
        repo1.create_project("Morning Project")

        # SIMULATE APP CLOSURE
        # We delete the objects. Python garbage collector runs.
        # The SQLite connection closes.
        del service1
        del repo1

        # --- SESSION 2: The "Evening" Session ---
        repo2 = SqliteRepository(path)
        service2 = TriageService(repo2)

        # Verify Data
        inbox = service2.get_inbox_items()
        assert "Morning Idea" in inbox

        projects = repo2.data.projects
        assert any(p.name == "Morning Project" for p in projects)

        # Continue working
        service2.add_to_inbox("Evening Idea")

        # Verify both exist
        assert len(service2.get_inbox_items()) == 2

    finally:
        if os.path.exists(path):
            os.unlink(path)