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

    repo1 = None
    repo2 = None

    try:
        # --- SESSION 1: The "Morning" Session ---
        repo1 = SqliteRepository(path)
        service1 = TriageService(repo1)

        service1.add_to_inbox("Morning Idea")
        repo1.create_project("Morning Project")

        # SIMULATE APP CLOSURE
        # Critical: Explicitly close connections before "quitting"
        repo1.session.close()
        repo1.engine.dispose()
        del service1
        del repo1
        repo1 = None  # Ensure we don't try to close it again in finally

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
        # Cleanup Session 2 if it exists
        if repo2:
            repo2.session.close()
            repo2.engine.dispose()

        # Cleanup Session 1 (safety check if test failed early)
        if repo1:
            repo1.session.close()
            repo1.engine.dispose()

        if os.path.exists(path):
            try:
                os.unlink(path)
            except PermissionError:
                pass