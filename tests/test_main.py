import json
from pathlib import Path
from types import SimpleNamespace

import flet as ft
import pytest

from backend.automation import STEPS, JobQueue
from backend.experiments import ANIMALS, PLANTS, ExperimentStore
from backend.results import ASSETS, load_predictions
from ui.training import TrainingView


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


def test_training_catalog_supports_both_drop_directions(tmp_path):
    view = TrainingView(None, ExperimentStore(tmp_path / "experiments.json"), lambda: None)
    selected = []
    section = view.catalog_section("models", "모델", selected)
    lists = section.content.controls[1]
    catalog, chosen = (column.content for column in lists.controls)
    model = catalog.content.content.controls[2]
    assert isinstance(model, ft.Draggable)
    assert model.group == chosen.group
    chosen.on_accept(SimpleNamespace(src=model))
    assert selected == ["resnet"]

    catalog, chosen = (column.content for column in lists.controls)
    model = chosen.content.content.controls[2]
    assert model.group == catalog.group
    catalog.on_accept(SimpleNamespace(src=model))
    assert selected == []


def test_training_selection_reuses_controls_and_edits_the_selected_draft(tmp_path):
    store = ExperimentStore(tmp_path / "experiments.json")
    first, second = store.experiments[:2]
    view = TrainingView(None, store, lambda: None)
    screen = view.build().content
    experiments, details, parameters = screen.controls[1].controls
    first_tile, second_tile = experiments.content.controls[1:3]
    name, datasets, _ = details.controls
    lists = datasets.content.controls[1]
    available, chosen = (side.content for side in lists.controls)
    epoch = parameters.content.controls[1]
    epoch.on_change(SimpleNamespace(control=SimpleNamespace(value="41")))

    second_tile.on_click(None)

    assert view.content.content is screen
    assert lists.controls[0].content is available
    assert lists.controls[1].content is chosen
    assert not first_tile.selected and second_tile.selected
    assert name.value == second.name
    assert epoch.value == str(second.parameters["--epoch"])
    card = available.content.content.controls[2]
    assert card.data == "pets"
    chosen.on_will_accept(SimpleNamespace(accept=True))
    chosen.on_accept(SimpleNamespace(src=card))
    assert view.drafts[second.id].datasets == ["cifar", "pets"]
    assert view.drafts[first.id].datasets == ["pets"]

    first_tile.on_click(None)
    assert first_tile.selected and not second_tile.selected
    assert epoch.value == "41"
    assert [card.data for card in chosen.content.content.controls[2:]] == ["pets"]


def test_training_domains_keep_legacy_experiments_and_unsaved_drafts(tmp_path):
    path = tmp_path / "experiments.json"
    path.write_text(json.dumps([
        {"id": "mixed", "name": "이전 실험", "datasets": ["pets", "flowers"]},
        {"id": "pet", "name": "동물 실험", "datasets": ["pets"]},
    ]), encoding="utf-8")
    store = ExperimentStore(path)
    assert [row.domain for row in store.experiments] == [PLANTS, ANIMALS]
    assert ExperimentStore(path).create("새 식물 실험", PLANTS).domain == PLANTS
    assert ExperimentStore(path).experiments[-1].domain == PLANTS

    themes = []
    view = TrainingView(None, store, lambda: themes.append(view.domain))
    view.build()
    view.drafts["pet"].parameters["--epoch"] = "41"
    toggle = view.domain_switch().controls[1]
    toggle.on_change(SimpleNamespace(control=SimpleNamespace(value=True)))
    assert list(view.drafts) == ["pet", "mixed"]
    lists = view.catalog_section("datasets", "데이터셋", view.drafts["mixed"].datasets)
    catalog, selected = (column.content for column in lists.content.controls[1].controls)
    assert [item.data for item in catalog.content.content.controls[2:]] == [
        "plant-village", "leaf-types"
    ]
    assert [item.data for item in selected.content.content.controls[2:]] == ["pets", "flowers"]

    toggle.on_change(SimpleNamespace(control=SimpleNamespace(value=False)))
    assert themes == [PLANTS, ANIMALS]
    assert view.drafts["pet"].parameters["--epoch"] == "41"


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
