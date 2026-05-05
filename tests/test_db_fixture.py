"""B9 fixture 自检：证明 NESTED savepoint per test 真正隔离。

跨 test 数据可见性 → 隔离失败。
"""

from sqlalchemy import select

from tests._dummy_model import Note


async def test_can_insert_and_query_within_session(db_session):
    db_session.add(Note(content="hello-from-test-A"))
    await db_session.flush()
    rows = (await db_session.execute(select(Note))).scalars().all()
    contents = [r.content for r in rows]
    assert "hello-from-test-A" in contents


async def test_other_test_inserts_not_visible(db_session):
    """test_can_insert_and_query_within_session 写的数据应已 rollback。"""
    rows = (await db_session.execute(select(Note))).scalars().all()
    contents = [r.content for r in rows]
    assert "hello-from-test-A" not in contents
    assert contents == []


async def test_session_commit_does_not_leak_across_tests(db_session):
    db_session.add(Note(content="leaky-commit"))
    await db_session.commit()
    rows = (await db_session.execute(select(Note))).scalars().all()
    assert any(r.content == "leaky-commit" for r in rows)


async def test_after_commit_other_test_still_clean(db_session):
    rows = (await db_session.execute(select(Note))).scalars().all()
    contents = [r.content for r in rows]
    assert "leaky-commit" not in contents
