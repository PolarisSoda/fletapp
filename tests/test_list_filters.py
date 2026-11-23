import asyncio
from unittest.mock import patch

import pytest
from flet.messaging.session import Session
import flet as ft

from backend.experiments import ExperimentStore
from backend.list_window import ListWindow
from backend.virtual_list import ROW_COUNT, row_values, sort_key
from main import main
from test_transport import RecordingWire, settle


async def test_filter_sort_selection_reset_and_empty_results():
    records = [("CIFAR-10", 30), ("Oxford Pets", 10), ("CIFAR-10", 20),
               ("Flowers-102", 40), ("CIFAR-10", 50)]
    model = ListWindow(records, lambda record: record)
    model.resize(84, 38, 46)  # One row makes full-range navigation testable.
    model.toggle(1)
    model.move(model.maximum)
    await model.set_filter(lambda record: record[0] == "CIFAR-10")
    assert model.count == 3 and model.total_count == 5
    assert model.first == 0 and model.selected_count == 0
    await model.sort(1)
    assert model.order == [2, 0, 4]
    model.move(model.maximum)
    assert model.rows() == [(4, records[4])]
    model.toggle(4)  # Original ID exceeds filtered count; it must still work.
    assert model.selected_count == 1
    await model.sort(1)
    assert model.order == [4, 0, 2] and model.selected(4)
    model.toggle_all()
    assert model.selected_count == 3
    model.toggle(0)
    assert model.selected_count == 2
    await model.set_filter(lambda record: False)
    assert model.count == 0 and model.rows() == []
    assert model.first == model.maximum == model.selected_count == 0
    await model.set_filter()
    assert model.order == [4, 3, 0, 2, 1]  # Active descending sort survives.
    assert model.count == 5 and model.selected_count == 0


async def test_filter_scans_only_required_field_and_bounds_row_construction():
    built = []

    def build(index):
        built.append(index)
        return row_values(index)

    model = ListWindow(range(ROW_COUNT), build, sort_keys={0: sort_key(0)})
    dataset = sort_key(2)
    await model.set_filter(lambda index: dataset(index) == "CIFAR-10")
    assert model.count == 166_667
    assert not built  # Matching does not construct full records or controls.
    assert all(values[2] == "CIFAR-10" for _, values in model.rows())
    assert len(built) == model.visible
    model.move(model.maximum)
    assert model.rows()[-1][0] == 499_999
    await model.sort(0)
    assert len(built) <= 2 * model.visible
    assert len(model.cache) <= 256


async def test_new_filter_wins_over_delayed_old_job():
    model = ListWindow(range(100), lambda index: (index,))
    started, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def worker(work):
        nonlocal calls
        calls += 1
        if calls == 1:
            started.set()
            await release.wait()
        return work()

    with patch("backend.list_window.asyncio.to_thread", worker):
        older = asyncio.create_task(model.set_filter(lambda index: index % 2 == 0))
        await asyncio.wait_for(started.wait(), 1)
        await model.set_filter(lambda index: index % 3 == 0)
        await model.sort(0)
        release.set()
        assert not await older
    assert model.order == list(range(0, 100, 3))
    assert not model.filtering and not model.sorting


async def test_browser_filter_yields_and_can_be_superseded():
    model = ListWindow(range(20_000), lambda index: (index,))
    with patch("backend.list_window.sys.platform", "emscripten"):
        older = asyncio.create_task(model.set_filter(lambda index: index % 2 == 0))
        await asyncio.sleep(0)  # The first filter must yield before completion.
        assert not older.done()
        await model.set_filter(lambda index: index == 19_999)
        assert not await older
    assert model.order == [19_999] and model.count == 1


@pytest.mark.parametrize("nav_index", [5, 6])
async def test_dataset_dropdown_filters_real_session_and_survives_navigation(tmp_path, nav_index):
    wire = RecordingWire()
    session = Session(wire)
    session.attach_connection(wire)

    def layout():
        root = ft.unwrap_component(session.page.controls)
        root = root[0] if isinstance(root, list) else root
        return [ft.unwrap_component(control) for control in root.controls]

    def screen():
        return ft.unwrap_component(layout()[1].content)

    def grid():
        return screen().controls[2]

    def picker():
        return next(control for control in screen().controls[1].controls if control.key == "dataset-filter")

    async def navigate(index):
        button = next(control for control in layout()[0].content.controls if control.key == f"nav-{index}")
        await session.dispatch_event(button._i, "click", None)
        await settle()

    async def choose(value):
        control = picker()
        session.apply_patch(control._i, {"value": value})
        await session.dispatch_event(control._i, "select", None)
        await settle()

    try:
        main(session.page, ExperimentStore(tmp_path / "experiments.json"))
        await settle()
        session.get_page_patch()
        await navigate(nav_index)
        grid().move(1000)
        await settle()
        await choose("CIFAR-10")
        assert grid().model.count == 166_667 and grid().model.first == 0
        assert all(values[2] == "CIFAR-10" for _, values in grid().model.rows())
        assert "166,667행" in grid().position.value
        grid().move(grid().model.maximum)
        await settle()
        assert grid().model.rows()[-1][0] == ROW_COUNT - 1
        grid().select_row(ROW_COUNT - 1)
        await settle()
        assert grid().model.selected_count == 1
        await navigate(0)
        await navigate(nav_index)
        assert picker().value == "CIFAR-10"
        assert grid().model.count == 166_667 and grid().model.selected_count == 1
        await choose("Flowers-102")
        assert grid().model.count == 166_666 and grid().model.selected_count == 0
        assert grid().model.first == 0
        await choose("all")
        assert grid().model.count == ROW_COUNT and grid().model.first == 0
        assert len(grid().model.cache) <= 256
        assert not wire.errors, wire.errors
    finally:
        session.close()
        await settle()
