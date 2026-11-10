import asyncio
import json
from pathlib import Path

import flet as ft
import msgpack
import pytest
from flet.controls.base_control import BaseControl
from flet.messaging.protocol import configure_encode_object_for_msgpack
from flet.messaging.session import Session
from flet.pubsub.pubsub_hub import PubSubHub

from backend.automation import STEPS, JobQueue
from backend.experiments import ANIMALS, PLANTS, ExperimentStore
from backend.results import ASSETS, load_predictions
from main import main
from ui.common import BG, TINT
from ui.training import TRAINING_SEEDS


def test_experiment_settings_survive_reload(tmp_path):
    path = tmp_path / "experiments.json"
    store = ExperimentStore(path)
    experiment = store.create("새 실험")
    experiment.datasets = ["pets"]
    experiment.models = ["resnet"]
    experiment.parameters.update({"--epoch": "5", "--optimizer": "sgd", "--augment": False})
    store.save(experiment)

    restored = ExperimentStore(path).experiments[-1]
    assert restored.name == "새 실험"
    assert restored.datasets == ["pets"]
    assert restored.models == ["resnet"]
    assert restored.parameters["--epoch"] == 5
    assert restored.parameters["--optimizer"] == "sgd"
    assert restored.parameters["--augment"] is False

    restored.parameters["--epoch"] = "0"
    with pytest.raises(ValueError, match="에폭"):
        store.save(restored)
    assert ExperimentStore(path).experiments[-1].parameters["--epoch"] == 5


class Wire:
    def __init__(self):
        self.errors = []
        self.pubsubhub = PubSubHub()

    def send_message(self, message):
        msgpack.packb(message, default=encode)
        if message.action.name == "SESSION_CRASHED":
            self.errors.append(message.body)


encode = configure_encode_object_for_msgpack(BaseControl)


@pytest.fixture
async def workbench():
    wire = Wire()
    session = Session(wire)
    session.attach_connection(wire)
    msgpack.packb(session.get_page_patch(), default=encode)
    yield session

    session.close()
    await asyncio.sleep(0)
    assert not wire.errors, wire.errors


async def event(session, control, name, payload=None, **props):
    assert session.index.get(control._i) is control
    if props:
        session.apply_patch(control._i, props)
    await session.dispatch_event(control._i, name, payload)
    for _ in range(4):
        await asyncio.sleep(0)


def layout(session):
    return [ft.unwrap_component(control) for control in ft.unwrap_component(session.page.controls).controls]


def training(session):
    return ft.unwrap_component(layout(session)[1].content)


def details(session):
    return [ft.unwrap_component(child) for child in training(session).controls[1].controls]


def targets(catalogs, index):
    row = catalogs.controls[index].content.controls[1]
    return [ft.unwrap_component(area) for area in row.controls]


def cards(target):
    return {
        card.data: card for card in target.content.content.controls[2:]
        if isinstance(card, ft.Draggable)
    }


async def enter_training(session):
    await event(session, layout(session)[0].content.controls[3], "click")


async def drop(session, source, target):
    assert source.group == target.group
    offset = {"x": 0, "y": 0}
    await event(session, target, "accept", {"src_id": source._i, "l": offset, "g": offset})


async def test_training_selection_rebinds_catalog_and_parameter_events(tmp_path, workbench):
    store = ExperimentStore(tmp_path / "experiments.json")
    first, second = store.experiments[:2]
    main(workbench.page, store)
    await enter_training(workbench)
    experiments, catalogs, parameters = details(workbench)
    epoch = parameters.content.controls[1]
    await event(workbench, epoch, "change", value="41")
    await event(workbench, experiments.content.controls[2], "click")

    experiments, catalogs, parameters = details(workbench)
    assert [tile.selected for tile in experiments.content.controls[1:3]] == [False, True]
    assert catalogs.controls[0].value == second.name
    assert parameters.content.controls[1].value == str(second.parameters["--epoch"])

    available, chosen = targets(catalogs, 1)
    source = cards(available)["pets"]
    await event(workbench, chosen, "will_accept", {"accept": True, "src_id": source._i})
    available, chosen = targets(details(workbench)[1], 1)
    assert chosen.content.bgcolor == TINT
    await event(workbench, chosen, "leave", {"src_id": source._i})
    available, chosen = targets(details(workbench)[1], 1)
    assert chosen.content.bgcolor == BG
    await drop(workbench, cards(available)["pets"], chosen)
    available, chosen = targets(details(workbench)[1], 1)
    assert list(cards(chosen)) == ["pets", "cifar"]

    await drop(workbench, cards(chosen)["pets"], available)
    assert list(cards(targets(details(workbench)[1], 1)[1])) == ["cifar"]

    await event(workbench, details(workbench)[0].content.controls[1], "click")
    _, catalogs, parameters = details(workbench)
    assert catalogs.controls[0].value == first.name
    assert parameters.content.controls[1].value == "41"
    assert list(cards(targets(catalogs, 1)[1])) == ["pets"]
    assert first.parameters["--epoch"] == 20


async def test_training_domains_keep_legacy_experiments_and_unsaved_drafts(tmp_path, workbench):
    path = tmp_path / "experiments.json"
    path.write_text(json.dumps([
        {"id": "mixed", "name": "이전 실험", "datasets": ["pets", "flowers"]},
        {"id": "pet", "name": "동물 실험", "datasets": ["pets"]},
    ]), encoding="utf-8")
    store = ExperimentStore(path)
    assert [row.domain for row in store.experiments] == [PLANTS, ANIMALS]
    assert store.create("새 식물 실험", PLANTS).domain == PLANTS
    assert ExperimentStore(path).experiments[-1].domain == PLANTS

    main(workbench.page, store)
    await enter_training(workbench)
    await event(workbench, details(workbench)[2].content.controls[1], "change", value="41")

    def domain_switch():
        return training(workbench).controls[0].controls[1].controls[1]

    await event(workbench, domain_switch(), "change", value=True)
    assert workbench.page.theme.color_scheme_seed == TRAINING_SEEDS[PLANTS]
    available, chosen = targets(details(workbench)[1], 1)
    assert list(cards(available)) == ["plant-village", "leaf-types"]
    assert list(cards(chosen)) == ["pets", "flowers"]

    await event(workbench, layout(workbench)[0].content.controls[2], "click")
    await enter_training(workbench)
    assert domain_switch().value is True
    await event(workbench, domain_switch(), "change", value=False)
    assert workbench.page.theme.color_scheme_seed == TRAINING_SEEDS[ANIMALS]
    assert details(workbench)[2].content.controls[1].value == "41"


async def test_training_creates_experiments_and_validates_before_saving(tmp_path, workbench):
    path = tmp_path / "experiments.json"
    store = ExperimentStore(path)
    main(workbench.page, store)
    await enter_training(workbench)

    def create_button():
        return ft.unwrap_component(details(workbench)[0].content.controls[-1])

    def current_dialog():
        return next(dialog for dialog in workbench.page._dialogs.controls
                    if isinstance(dialog, ft.AlertDialog) and dialog.open)

    await event(workbench, create_button(), "click")
    await event(workbench, current_dialog().actions[1], "click")
    assert current_dialog().content.error == "실험 이름을 입력하세요."
    await event(workbench, current_dialog().content, "submit", value="추가 실험")
    assert details(workbench)[1].controls[0].value == "추가 실험"
    assert ExperimentStore(path).experiments[-1].name == "추가 실험"
    assert not any(isinstance(dialog, ft.AlertDialog) and dialog.open
                   for dialog in workbench.page._dialogs.controls)

    await event(workbench, create_button(), "click")
    assert current_dialog().content.value == ""
    await event(workbench, current_dialog().actions[0], "click")

    def fields():
        return details(workbench)[2].content.controls

    await event(workbench, fields()[1], "change", value="0")
    await event(workbench, fields()[-1], "click")
    assert fields()[1].error == "에폭 값을 확인하세요."
    assert ExperimentStore(path).experiments[-1].parameters["--epoch"] == 20
    await event(workbench, fields()[1], "change", value="42")
    await event(workbench, fields()[-1], "click")
    assert fields()[1].error is None
    assert ExperimentStore(path).experiments[-1].parameters["--epoch"] == 42


async def test_workbench_navigation_keeps_results_and_automation_interactive(tmp_path, workbench):
    main(workbench.page, ExperimentStore(tmp_path / "experiments.json"))

    def sidebar():
        return layout(workbench)[0].content.controls

    def screen():
        return ft.unwrap_component(layout(workbench)[1].content)

    await event(workbench, sidebar()[7], "click")
    assert workbench.page.theme_mode == ft.ThemeMode.DARK

    await event(workbench, sidebar()[4], "click")
    enqueue = screen().controls[1].content.controls[1].controls[1]
    await event(workbench, enqueue, "click")
    assert len(screen().controls[2].content.controls) == 2

    await event(workbench, sidebar()[5], "click")
    filter_switch = screen().controls[2].controls[0].content.controls[0].controls[1]
    await event(workbench, filter_switch, "change", value=True)
    table = screen().controls[2].controls[0].content.controls[1].controls[0]
    assert len(table.rows) == sum(not row.correct for row in load_predictions())


def test_automation_runs_a_snapshot_of_the_saved_settings(tmp_path):
    store = ExperimentStore(tmp_path / "experiments.json")
    experiment = store.experiments[0]
    queue = JobQueue()
    queue.enqueue(experiment)
    queue.enqueue(experiment)
    experiment.models.clear()

    job = queue.start()
    assert job.experiment.models == ["resnet"]
    assert queue.start() is None
    for _ in STEPS:
        queue.advance(job)
    assert job.status == "완료"
    assert queue.start().number == 2


def test_results_reference_existing_sample_images():
    rows = load_predictions()
    assert len(rows) == 6
    assert sum(row.correct for row in rows) == 4
    for row in rows:
        assert Path(ASSETS, "samples", row.image).is_file()
