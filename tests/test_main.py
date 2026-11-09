from pathlib import Path
from types import SimpleNamespace

import flet as ft
import pytest

from backend.automation import STEPS, JobQueue
from backend.experiments import ExperimentStore
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
    view = TrainingView(None, ExperimentStore(tmp_path / "experiments.json"))
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
