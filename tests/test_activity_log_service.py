import json
from uuid import uuid4

from api.core.logging import configure_logging
from api.services.activity_log_service import write_event


async def test_write_event_emits_structured_log(capsys):
    configure_logging()
    actor = uuid4()
    proj = uuid4()
    target = uuid4()

    await write_event(
        db=None,
        actor_user_id=actor,
        project_id=proj,
        action_type="create",
        target_type="module",
        target_id=str(target),
        summary="创建了节点『登录流程』",
        metadata={"importance": "high"},
    )
    captured = capsys.readouterr().out.strip().splitlines()
    payload = json.loads(captured[-1])
    assert payload["event"] == "activity.event"
    assert payload["actor_user_id"] == str(actor)
    assert payload["project_id"] == str(proj)
    assert payload["action_type"] == "create"
    assert payload["target_type"] == "module"
    assert payload["target_id"] == str(target)
    assert payload["summary"] == "创建了节点『登录流程』"
    assert payload["metadata"] == {"importance": "high"}
    assert payload["impl"] == "stub"


async def test_write_event_metadata_optional(capsys):
    configure_logging()
    await write_event(
        db=None,
        actor_user_id=uuid4(),
        project_id=uuid4(),
        action_type="delete",
        target_type="project",
        target_id=str(uuid4()),
        summary="x",
    )
    captured = capsys.readouterr().out.strip().splitlines()
    payload = json.loads(captured[-1])
    assert payload["metadata"] is None
