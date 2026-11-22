import asyncio
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as E
from unittest.mock import patch

import flet as ft
import msgpack
from flet.messaging.session import Session

from backend.experiments import ExperimentStore
from backend.list_window import ListWindow
from backend.virtual_list import ROW_COUNT
from controls.sticky_list import StickyListView
from main import main
from test_transport import RecordingWire, settle
from ui.pure_list import PureListView


def test_pure_control_imports_without_virtual_table():
    source = Path(__file__).resolve().parents[1] / "src"
    script = '''import builtins,sys
sys.path.insert(0, sys.argv[1])
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name.startswith(("flet_virtual_table", "flet_datagrid")):
        raise ImportError("Custom extensions are unavailable")
    return original(name,*args,**kwargs)
builtins.__import__=guarded
from ui.pure_list import PureListView
for native in (False, True):
    screen=PureListView(native=native)
    screen.build()
    assert screen.control.model.count == 500000
'''
    subprocess.run([sys.executable, "-c", script, str(source)], check=True)


def test_discrete_wheel_full_range_and_bounded_cache():
    screen = PureListView()
    assert screen.content is None
    screen.build()
    control, model = screen.control, screen.model
    assert len(model.cache) == model.visible
    for delta in (1, 120, 600):
        before = model.first
        control.wheel(E(scroll_delta=ft.Offset(0, delta)))
        assert model.first == before + 1
    control.wheel(E(scroll_delta=ft.Offset(120, 0)))
    assert model.first == 3
    control.wheel(E(scroll_delta=ft.Offset(0, -120)))
    assert model.first == 2
    for i in range(400):
        model.move(i)
        model.rows()
    assert len(model.cache) <= 256
    control.track_tap(E(local_position=ft.Offset(0, model.track_height)))
    assert model.first == model.maximum
    assert model.rows()[-1][0] == ROW_COUNT - 1
    control.track_tap(E(local_position=ft.Offset(0, 0)))
    assert model.first == 0
    control.resize(E(height=730))
    assert model.visible == 18


async def test_selection_survives_sort_and_select_all_uses_exceptions():
    model = ListWindow([(30,), (10,), (20,)], lambda row: row)
    model.toggle(0)
    await model.sort(0)
    assert model.order == [1, 2, 0]
    assert model.selected(0) and model.selected_count == 1
    await model.sort(0)
    assert model.order == [0, 2, 1]
    model.toggle_all()
    assert model.selected_count == 3 and not model.exceptions
    model.toggle(1)
    assert model.selected_count == 2 and model.exceptions == {1}


async def test_pure_navigation_scroll_selection_and_small_updates(tmp_path):
    class Wire(RecordingWire):
        def __init__(self):
            super().__init__()
            self.sizes = []

        def send_message(self, message):
            self.sizes.append(len(msgpack.packb(message, default=self.encode)))
            super().send_message(message)

    wire = Wire()
    session = Session(wire)
    session.attach_connection(wire)

    def layout():
        root = ft.unwrap_component(session.page.controls)
        root = root[0] if isinstance(root, list) else root
        return [ft.unwrap_component(control) for control in root.controls]

    def control():
        return ft.unwrap_component(layout()[1].content).controls[2]

    async def navigate(index):
        button = next(c for c in layout()[0].content.controls if c.key == f"nav-{index}")
        await session.dispatch_event(button._i, "click", None)
        await settle()

    try:
        main(session.page, ExperimentStore(tmp_path / "experiments.json"))
        await settle()
        session.get_page_patch()
        wire.sizes.clear()
        await navigate(5)
        grid = control()
        assert isinstance(grid, StickyListView)
        assert max(wire.sizes) < 120_000
        await session.dispatch_event(grid.canvas._i, "resize", {"w": grid.table_width, "h": 730})
        await settle()
        assert control().model.visible == 18
        for delta in (120, 600, -1):
            grid = control()
            before = grid.model.first
            wire.sizes.clear()
            await session.dispatch_event(grid.gestures._i, "scroll", {
                "l": {"x": 100, "y": 100}, "g": {"x": 100, "y": 100},
                "sd": {"x": 0, "y": delta},
            })
            await settle()
            assert control().model.first == before + (1 if delta > 0 else -1)
            assert max(wire.sizes) < 120_000
        grid = control()
        assert grid.gestures.on_tap_down is None
        row_hit = next(c for c in grid.canvas.content.controls if c.key == "canvas-row-1")
        await session.dispatch_event(row_hit._i, "click", None)
        await settle()
        assert control().model.selected_count == 1
        await navigate(0)
        await navigate(5)
        assert control().model.first == 1
        assert control().model.selected_count == 1
        assert len(control().model.cache) <= 256

        # A thumb grab must not jump, and the drag offset must survive the
        # declarative branch replacing the control between input events.
        model = control().model
        top, height, _ = model.thumb()
        before = model.first
        control().track_tap(E(local_position=ft.Offset(10, top + height / 2)))
        assert model.first == before
        await session.dispatch_event(control().track_input._i, "vertical_drag_start", {
            "k": "mouse",
            "l": {"x": 10, "y": top + 5}, "g": {"x": 10, "y": top + 5},
        })
        await settle()
        assert model.drag_offset == 5
        await session.dispatch_event(control().track_input._i, "vertical_drag_update", {
            "l": {"x": 10, "y": model.track_height}, "g": {"x": 10, "y": model.track_height},
        })
        await settle()
        assert model.first == model.maximum
        assert model.rows()[-1][0] == ROW_COUNT - 1

        started, finish = asyncio.Event(), asyncio.Event()

        async def worker(work):
            started.set()
            await finish.wait()
            return range(ROW_COUNT)

        with patch("backend.list_window.asyncio.to_thread", worker):
            grid = control()
            heading = next(c for c in grid.canvas.content.controls if c.key == "canvas-sort-0")
            task = asyncio.create_task(session.dispatch_event(heading._i, "click", None))
            await asyncio.wait_for(started.wait(), 1)
            await navigate(0)
            finish.set()
            await task
            await settle()
        await navigate(5)
        assert control().model.sort_column_index == 0
        assert control().model.selected_count == 1
        assert control().model.first == 0
        assert not wire.errors, wire.errors
    finally:
        session.close()
        await settle()


def test_canvas_hit_targets_keep_painted_row_identity_and_support_real_controls():
    screen = PureListView()
    screen.build()
    control = screen.control
    control.move(100)
    painted_row = next(c for c in control.canvas.content.controls if c.key == "canvas-row-100")
    # Input may arrive after another scroll event updated the logical viewport.
    control.model.move(500)
    painted_row.on_click(None)
    assert control.model.selected(100)
    assert not control.model.selected(500)
    assert control.gestures.on_tap_down is None

    control.model.rich_cells = True
    screen.rebuild()
    overlay = next(c for c in screen.control.canvas.content.controls if c.key == "canvas-cell-500-1")
    assert isinstance(overlay.content, ft.Row)
    assert isinstance(overlay.content.controls[1], ft.Column)
    button = overlay.content.controls[-1]
    selected_before = screen.model.selected_count
    button.on_click(None)
    assert screen.model.cell_actions[500] == 1
    assert screen.model.selected_count == selected_before
