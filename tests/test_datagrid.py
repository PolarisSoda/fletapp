from unittest.mock import patch
from types import SimpleNamespace as E
import asyncio
import pytest
import flet as ft
from flet_datagrid import DataGrid, Selection

@pytest.fixture
def grid():
    with patch.object(DataGrid, 'update'):
        yield DataGrid(columns=[ft.DataColumn('Number'), ft.DataColumn('Name')],
                       records=[(30, 'c'), (10, 'a'), (20, 'b')])

async def fetch(grid, revision=None):
    await grid._fetch(E(revision=grid.revision if revision is None else revision, start=0, count=72, request_id=1))

async def test_sort_selection_and_stale_requests(grid):
    await grid._select(E(select_all=False, row_id=0, selected=True))
    await grid._sort(E(column_index=0, ascending=True))
    await fetch(grid)
    assert grid.response['row_ids'] == [1, 2, 0]
    assert grid.response['selected'] == [False, False, True]
    before = grid.response
    await fetch(grid, revision=0)
    assert grid.response is before
    await grid._sort(E(column_index=1, ascending=False))
    await fetch(grid)
    assert grid.response['rows'] == [[30, 'c'], [20, 'b'], [10, 'a']]

async def test_select_all_and_exceptions(grid):
    await grid._select(E(select_all=True, selected=True))
    await grid._select(E(select_all=False, row_id=1, selected=False))
    assert list(grid.selection.ids()) == [0, 2]
    assert grid.selected_count == 2
    await fetch(grid)
    assert grid.response['selected'] == [True, False, True]
    grid.set_rows([])
    assert grid.selected_count == 0 and grid.row_count == 0

def test_select_all_is_constant_space():
    selection = Selection(500_000)
    selection.select_all(True)
    assert selection.selected_count == 500_000 and len(selection.exceptions) == 0
    selection.set(499_999, False)
    assert selection.selected_count == 499_999 and selection.exceptions == {499_999}

async def test_native_controls_and_callbacks():
    events = []
    column = ft.DataColumn(ft.Text('Name'), on_sort=lambda e: events.append(e.ascending))
    row = ft.DataRow(cells=[ft.DataCell(ft.Text('Hello'))], on_select_change=lambda e: events.append(e.data))
    with patch.object(DataGrid, 'update'):
        table = DataGrid(columns=[column], rows=[row])
        await table._sort(E(column_index=0, ascending=True))
        await table._select(E(select_all=False, row_id=0, selected=True))
        await fetch(table)
        assert table.response['rows'][0][0] is row.cells[0]
        assert events == [True, True]

async def test_lazy_builder_only_builds_window():
    visited = []
    with patch.object(DataGrid, 'update'):
        table = DataGrid(columns=[ft.DataColumn('A')], records=range(500_000),
                         row_builder=lambda x: visited.append(x) or [x], sort_keys={0: lambda x: x})
        await table._fetch(E(revision=0, start=499_990, count=72, request_id=1))
        assert visited == list(range(499_990, 500_000))
        with pytest.raises(ValueError):
            await table._fetch(E(revision=0, start=0, count=513, request_id=2))

async def test_preselected_rows_replacement_and_disabled_sort():
    with patch.object(DataGrid, 'update'):
        first = ft.DataRow(cells=[ft.DataCell('a')], selected=True)
        table = DataGrid(columns=[ft.DataColumn('A')], rows=[first], sortable=[False])
        assert table.selected_count == 1
        await table._sort(E(column_index=0, ascending=False))
        assert table.sort_column_index is None
        await table._select(E(select_all=True, selected=False))
        assert first.selected is False
        table.rows = [ft.DataRow(cells=[ft.DataCell('b')], selected=True)]
        assert table.selected_count == 1 and table.revision == 1

async def test_concurrent_sort_only_latest_wins(grid):
    original = asyncio.to_thread
    calls = 0
    async def controlled(work):
        nonlocal calls
        calls += 1
        position = calls
        result = work()
        await asyncio.sleep(.03 if position == 1 else 0)
        return result
    with patch('flet_virtual_table.datagrid.asyncio.to_thread', controlled):
        await asyncio.gather(grid._sort(E(column_index=0, ascending=True)),
                             grid._sort(E(column_index=0, ascending=False)))
    assert grid.sort_ascending is False
    assert list(grid._order) == [0, 2, 1]
