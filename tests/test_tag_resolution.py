import pytest
from services.db_models import DBTag


def test_tag_resolution_is_idempotent(in_memory_repo):
    """
    Kills Mutant: _resolve_tags logic errors (creating duplicates or failing to find).
    """
    # 1. Create Project with tag "urgent"
    p1 = in_memory_repo.create_project("P1")
    from models.entities import Task
    t1 = Task(name="T1", tags=["urgent"])
    p1.tasks.append(t1)
    in_memory_repo.sync_project(p1)

    # 2. Create Project with SAME tag "urgent"
    p2 = in_memory_repo.create_project("P2")
    t2 = Task(name="T2", tags=["urgent"])
    p2.tasks.append(t2)
    in_memory_repo.sync_project(p2)

    # 3. Verify DB has exactly 1 tag row
    tags = in_memory_repo.session.query(DBTag).all()
    assert len(tags) == 1
    assert tags[0].name == "urgent"