import sys
import os
import pytest
import tempfile
from pathlib import Path
from services.repository import SqliteRepository
from services.db_models import Base

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def in_memory_repo():
    """
    Creates a repository backed by a temporary file.
    This mimics production exactly while keeping tests isolated.
    """
    # 1. Create temp file
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # 2. Initialize Repo
    repo = SqliteRepository(path)

    yield repo

    # 3. Cleanup: Close session/engine to release file lock
    repo.session.close()
    repo.engine.dispose()

    # 4. Delete file
    if os.path.exists(path):
        os.unlink(path)