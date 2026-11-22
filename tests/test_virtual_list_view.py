import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import flet as ft
import msgpack
from flet.messaging.session import Session

from backend.experiments import ExperimentStore
from backend.virtual_list import ROW_COUNT, row_values
from main import main
from test_transport import RecordingWire, settle
from ui.virtual_list import VirtualListView


async def test_screen_is_lazy_and_only_requested_rows_are_built():
    screen = VirtualListView()
    assert screen.content is None and screen.table is None
    with patch("ui.virtual_list.row_values", wraps=row_values) as builder:
        content = screen.build()
        table = screen.table
        assert screen.build() is content
        assert builder.call_count == 0
        assert isinstance(table.rows, range) and len(table.rows) == ROW_COUNT
        assert table.response == {}
        await table._fetch(SimpleNamespace(revision=0, start=ROW_COUNT - 8, count=72, request_id=1))
        assert builder.call_count == 8
        assert table.response["rows"][-1] == list(row_values(ROW_COUNT - 1))
        assert len(table.response["rows"]) == 8


async def test_sort_can_finish_while_screen_is_detached():
    screen = VirtualListView()
    screen.build()
    table = screen.table
    started, finish = asyncio.Event(), asyncio.Event()

    async def worker(work):
        started.set()
        await finish.wait()
        return list(reversed(range(ROW_COUNT)))

    with patch("flet_virtual_table.datagrid.asyncio.to_thread", worker):
        task = asyncio.create_task(table._sort(SimpleNamespace(column_index=0, ascending=False)))
        await started.wait()
        table.will_unmount()
        finish.set()
        await task
    assert table.sort_column_index == 0
    assert not table.sort_ascending
    assert screen.build() is screen.content
    assert "내림차순" in screen.status.value
    await table._fetch(SimpleNamespace(revision=table.revision, start=0, count=1, request_id=2))
    assert table.response["rows"][0] == list(row_values(ROW_COUNT - 1))


async def test_navigation_sends_bounded_patches_and_keeps_selection(tmp_path):
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
    session.get_page_patch()

    def layout():
        root = ft.unwrap_component(session.page.controls)
        root = root[0] if isinstance(root, list) else root
        return [ft.unwrap_component(control) for control in root.controls]

    def screen():
        return ft.unwrap_component(layout()[1].content)

    async def navigate(index):
        button = next(item for item in layout()[0].content.controls if item.key == f"nav-{index}")
        await session.dispatch_event(button._i, "click", None)
        await settle()

    try:
        with patch("ui.virtual_list.row_values", wraps=row_values) as builder:
            main(session.page, ExperimentStore(tmp_path / "experiments.json"))
            await settle()
            msgpack.packb(session.get_page_patch(), default=wire.encode)
            assert builder.call_count == 0
            wire.sizes.clear()
            await navigate(4)
            table = screen().controls[2].content
            assert table.row_count == ROW_COUNT and builder.call_count == 0
            assert max(wire.sizes) < 30_000
            await session.dispatch_event(table._i, "range_request", dict(
                revision=0, start=499_900, count=72, request_id=1,
            ))
            await settle()
            assert builder.call_count == 72
            table = screen().controls[2].content
            assert table.response["start"] == 499_900
            await session.dispatch_event(table._i, "selection_request", dict(
                row_id=499_901, selected=True, select_all=False,
            ))
            await settle()
            table = screen().controls[2].content
            assert table.selected_count == 1
            await navigate(0)
            wire.sizes.clear()
            await navigate(4)
            if not session.components_mode:
                assert screen().controls[2].content is table
            table = screen().controls[2].content
            assert table.selected_count == 1
            assert max(wire.sizes) < 100_000
            assert builder.call_count == 72
            assert not wire.errors, wire.errors

            started, finish = asyncio.Event(), asyncio.Event()

            async def worker(work):
                started.set()
                await finish.wait()
                return range(ROW_COUNT - 1, -1, -1)

            with patch("flet_virtual_table.datagrid.asyncio.to_thread", worker):
                task = asyncio.create_task(session.dispatch_event(table._i, "sort_request", dict(
                    column_index=0, ascending=False,
                )))
                await asyncio.wait_for(started.wait(), 1)
                await navigate(0)
                finish.set()
                await task
                await settle()
            await navigate(4)
            table = screen().controls[2].content
            assert table.selected_count == 1
            assert table.sort_column_index == 0 and not table.sort_ascending
            await session.dispatch_event(table._i, "range_request", dict(
                revision=table.revision, start=0, count=72, request_id=2,
            ))
            await settle()
            table = screen().controls[2].content
            assert table.response["rows"][0] == list(row_values(ROW_COUNT - 1))
            assert not wire.errors, wire.errors
    finally:
        session.close()
        await settle()
