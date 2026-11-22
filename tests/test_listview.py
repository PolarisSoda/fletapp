from types import SimpleNamespace as E

import flet as ft
from flet.messaging.session import Session

from backend.experiments import ExperimentStore
from backend.virtual_list import ROW_COUNT
from controls.windowed_list_view import WindowedListView
from main import main
from test_transport import RecordingWire, settle
from ui.pure_list import PureListView


def test_listview_is_native_bounded_and_supports_both_extent_modes():
    screen = PureListView(native=True)
    screen.build()
    control = screen.control
    assert isinstance(control, WindowedListView)
    assert isinstance(control.list_view, ft.ListView)
    assert control.list_view.build_controls_on_demand
    assert control.list_view.item_extent == 38
    assert control.list_view.prototype_item is None
    assert len(control.list_view.controls) == screen.model.visible
    assert len(screen.model.cache) < 100
    control.move(control.model.maximum)
    assert control.list_view.controls[-1].key == f"list-row-{ROW_COUNT - 1}"
    screen.model.use_prototype = True
    screen.rebuild()
    assert screen.control.list_view.item_extent is None
    assert screen.control.list_view.prototype_item.height == 38
    assert len(screen.control.list_view.controls) < 100


def test_custom_whole_rows_are_built_only_for_the_window():
    visited = []

    def build(record, row_id, selected):
        visited.append(row_id)
        return ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE), ft.Text(str(record)), ft.Text("custom row")])

    control = WindowedListView(["Content"], range(ROW_COUNT), lambda i: [i],
                               row_control_builder=build, row_height=56, use_prototype=True)
    assert visited == list(range(control.model.visible))
    assert len(visited) < 20
    assert control.list_view.prototype_item.height == 56
    assert isinstance(control.list_view.controls[0].content, ft.Row)
    header = control.canvas.content.controls[0].content.controls[0].content
    assert header.value is False and not header.tristate
    control.select_row(0)
    header = control.canvas.content.controls[0].content.controls[0].content
    assert header.value is None and header.tristate
    control.move(control.model.maximum)
    assert visited[-1] == ROW_COUNT - 1


async def test_listview_rows_and_complex_children_route_native_events(tmp_path):
    wire = RecordingWire()
    session = Session(wire)
    session.attach_connection(wire)

    def layout():
        root = ft.unwrap_component(session.page.controls)
        root = root[0] if isinstance(root, list) else root
        return [ft.unwrap_component(c) for c in root.controls]

    def screen():
        return ft.unwrap_component(layout()[1].content)

    def grid():
        return screen().controls[2]

    async def navigate(index):
        button = next(c for c in layout()[0].content.controls if c.key == f"nav-{index}")
        await session.dispatch_event(button._i, "click", None)
        await settle()

    async def switch(key):
        control = next(c for c in screen().controls[1].controls if c.key == key)
        session.apply_patch(control._i, {"value": True})
        await session.dispatch_event(control._i, "change", None)
        await settle()

    try:
        main(session.page, ExperimentStore(tmp_path / "experiments.json"))
        await settle()
        session.get_page_patch()
        await navigate(6)
        assert isinstance(grid().list_view, ft.ListView)
        await session.dispatch_event(grid().canvas._i, "size_change", {"w": 1532, "h": 730})
        await settle()
        assert grid().model.visible == 18
        await session.dispatch_event(grid().gestures._i, "scroll", {
            "l": {"x": 100, "y": 100}, "g": {"x": 100, "y": 100}, "sd": {"x": 0, "y": 120},
        })
        await settle()
        assert grid().model.first == 1
        row = grid().list_view.controls[0]
        await session.dispatch_event(row._i, "click", None)
        await settle()
        assert grid().model.selected(1)

        await switch("rich-cells")
        row = grid().list_view.controls[0]
        rich_cell = row.content.controls[2].content
        assert isinstance(rich_cell, ft.Row)
        button = rich_cell.controls[-1]
        await session.dispatch_event(button._i, "click", None)
        await settle()
        assert grid().model.cell_actions[1] == 1
        assert grid().model.selected_count == 1

        await switch("list-prototype")
        assert grid().list_view.prototype_item.height == 38
        assert grid().list_view.item_extent is None
        await navigate(4)
        await navigate(5)
        await navigate(6)
        assert grid().model.first == 1 and grid().model.selected(1)
        assert grid().model.rich_cells and grid().model.use_prototype
        assert len(grid().list_view.controls) <= 18
        assert not wire.errors, wire.errors
    finally:
        session.close()
        await settle()
