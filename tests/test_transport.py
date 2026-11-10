import asyncio
import json
from unittest.mock import MagicMock

import flet as ft
import msgpack
import pytest
from flet.controls.base_control import BaseControl
from flet.messaging.protocol import configure_encode_object_for_msgpack
from flet.messaging.session import Session
from flet.pubsub.pubsub_hub import PubSubHub

from backend.experiments import ExperimentStore
from backend.transport import HttpExperimentSender, configured_sender, send_experiment
from main import main


@pytest.mark.asyncio
async def test_http_sender_posts_saved_experiment_as_json(tmp_path, monkeypatch):
    experiment = ExperimentStore(tmp_path / "experiments.json").experiments[0]
    response = MagicMock()
    response.__enter__.return_value.status = 202
    post = MagicMock(return_value=response)
    monkeypatch.setattr("backend.transport.urlopen", post)
    monkeypatch.setenv("MODEL_WORKBENCH_API_URL", "https://example.test/experiments")

    assert await send_experiment(configured_sender(), experiment) == "저장된 실험 설정을 전송했습니다."
    request, = post.call_args.args
    assert request.get_method() == "POST"
    assert request.full_url == "https://example.test/experiments"
    assert request.get_header("Content-type") == "application/json; charset=utf-8"
    assert post.call_args.kwargs["timeout"] == 10
    payload = json.loads(request.data)
    assert payload["id"] == experiment.id
    assert payload["datasets"] == experiment.datasets
    assert payload["models"] == experiment.models
    assert payload["parameters"] == experiment.parameters

    monkeypatch.delenv("MODEL_WORKBENCH_API_URL")
    assert "주소를 설정" in await send_experiment(configured_sender(), experiment)
    assert "전송 실패" in await send_experiment(HttpExperimentSender("ftp://example.test"), experiment)
    assert post.call_count == 1


class RecordingWire:
    encode = staticmethod(configure_encode_object_for_msgpack(BaseControl))

    def __init__(self):
        self.pubsubhub = PubSubHub()
        self.patches = []
        self.errors = []

    def send_message(self, message):
        msgpack.packb(message, default=self.encode)
        if message.action.name == "PATCH_CONTROL":
            self.patches.append(message.body.id)
        if message.action.name == "SESSION_CRASHED":
            self.errors.append(message.body)


async def settle():
    for _ in range(4):
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_automation_sends_selected_snapshot_once_and_keeps_queue_local(tmp_path):
    class Sender:
        def __init__(self):
            self.calls = []
            self.started = asyncio.Event()
            self.finish = asyncio.Event()

        async def send(self, experiment):
            self.calls.append(experiment)
            self.started.set()
            await self.finish.wait()

    store = ExperimentStore(tmp_path / "experiments.json")
    sender = Sender()
    wire = RecordingWire()
    session = Session(wire)
    session.attach_connection(wire)
    msgpack.packb(session.get_page_patch(), default=wire.encode)
    task = None

    def layout():
        root = ft.unwrap_component(session.page.controls)
        root = root[0] if isinstance(root, list) else root
        return [ft.unwrap_component(control) for control in root.controls]

    def automation():
        return ft.unwrap_component(layout()[1].content)

    def buttons():
        return automation().controls[1].content.controls[1].controls

    async def click(control):
        await session.dispatch_event(control._i, "click", None)
        await settle()

    try:
        main(session.page, store, sender=sender)
        await click(layout()[0].content.controls[4])
        picker, enqueue, start, send = buttons()
        experiment = store.experiments[1]
        session.apply_patch(picker._i, {"value": experiment.id})
        await session.dispatch_event(picker._i, "select", None)
        await settle()

        wire.patches.clear()
        task = asyncio.create_task(session.dispatch_event(buttons()[-1]._i, "click", None))
        await asyncio.wait_for(sender.started.wait(), 1)
        await settle()
        assert buttons()[-1].disabled
        await click(buttons()[-1])
        assert sender.calls == [experiment]
        assert sender.calls[0] is not experiment

        sender.finish.set()
        await task
        await settle()
        assert not buttons()[-1].disabled
        assert automation().controls[2].content.controls[1].value == "아직 대기열에 등록된 작업이 없습니다."
        if not session.components_mode:
            assert session.page._i not in wire.patches

        wire.patches.clear()
        await click(buttons()[1])
        assert len(automation().controls[2].content.controls) == 2
        assert not buttons()[2].disabled
        if not session.components_mode:
            assert buttons()[0] is picker
            assert set(wire.patches) == {automation().controls[2]._i, start._i}
        assert not wire.errors, wire.errors
    finally:
        sender.finish.set()
        if task is not None:
            await task
        session.close()
        await settle()
