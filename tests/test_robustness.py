from hypothesis import given, strategies as st
from services.repository import SqliteRepository, TriageService
import tempfile
import os

@given(st.text())
def test_inbox_accepts_any_text(random_text):
    """
    Fuzz testing the Inbox.
    Can it handle Chinese characters? Emojis? SQL Injection strings? Empty strings?
    """
    # Setup isolated DB per run
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    repo = None

    try:
        repo = SqliteRepository(path)
        service = TriageService(repo)

        # Action
        service.add_to_inbox(random_text)

        # Assert
        items = service.get_inbox_items()
        assert items[-1] == random_text

    finally:
        # CRITICAL FIX: Close connections before deleting file
        if repo:
            repo.session.close()
            repo.engine.dispose()

        if os.path.exists(path):
            try:
                os.unlink(path)
            except PermissionError:
                pass