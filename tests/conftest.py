import sys
import pytest
from pathlib import Path
from services.repository import SqliteRepository
from services.db_models import Base

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def in_memory_repo():
    repo = SqliteRepository(":memory:")
    yield repo
    # Cleanup
    repo.session.close()
    repo.engine.dispose()