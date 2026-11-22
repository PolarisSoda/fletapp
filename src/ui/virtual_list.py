"""A bounded, sticky-header list screen using the existing native grid renderer.

Unlike a stock ListView full of Python controls, only the current viewport is
serialized. Flutter's TableView pins the heading and virtualizes both axes.
"""

import flet as ft
from flet_datagrid import DataGrid
from flet_virtual_table import FletVirtualTable

from backend.virtual_list import COLUMN_LABELS, NUMERIC_COLUMNS, ROW_COUNT, row_values, sort_key
from ui.common import LINE, badge, heading, muted


class NavigationDataGrid(DataGrid):
    """Allow a worker sort to finish safely after navigating away.

    The cached Python state is sent on the next mount; detached controls must
    never send patches to a client that has already disposed their widget.
    """

    def did_mount(self):
        self._attached = True

    def will_unmount(self):
        self._attached = False

    def update(self):
        if getattr(self, "_attached", False):
            super().update()


class VirtualListView:
    """Create the screen on first navigation, then reuse its bounded control tree."""

    def __init__(self):
        self.content = None
        self.table = None

    def build(self):
        if self.content is not None:
            return self.content

        self.status = muted("선택한 행이 없습니다.")
        self.table = create_table(self.report)
        self.content = list_layout(self.table, self.status)
        return self.content

    def report(self, _=None):
        self.status.value = selection_text(self.table)
        if getattr(self.table, "_attached", False):
            self.status.update()


def create_table(on_change):
    return NavigationDataGrid(
        key="virtual-list-grid",
        columns=[
            ft.DataColumn(label, numeric=index in NUMERIC_COLUMNS)
            for index, label in enumerate(COLUMN_LABELS)
        ],
        records=range(ROW_COUNT),
        row_builder=row_values,
        sort_keys={index: sort_key(index) for index in range(len(COLUMN_LABELS))},
        column_widths=[110, 150, 160, 170, 120, 100, 100, 140, 110, 160],
        row_height=38,
        heading_row_height=46,
        on_selection_change=on_change,
        on_sort=on_change,
        expand=True,
    )


def list_layout(table, status):
    # Keep a finite viewport. An outer scrolling Column would defeat layout
    # constraints and make the pinned header scroll with the whole screen.
    return ft.Column(
        [
            heading("04", "대용량 목록", "스크롤해도 열 제목은 고정됩니다. 행을 선택하거나 열 제목을 눌러 정렬하세요."),
            ft.Row([
                badge(f"{ROW_COUNT:,}행"),
                badge(f"{len(COLUMN_LABELS)}열"),
                muted("샘플 학습 실험"),
            ]),
            ft.Container(
                content=table,
                border=ft.Border.all(1, LINE),
                border_radius=10,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                expand=True,
            ),
            status,
        ],
        key="virtual-list-screen",
        spacing=14,
        expand=True,
    )


def selection_text(table):
    selected = f"{table.selected_count:,}행 선택" if table.selected_count else "선택한 행이 없습니다."
    if table.sort_column_index is not None:
        direction = "오름차순" if table.sort_ascending else "내림차순"
        selected += f"  ·  {COLUMN_LABELS[table.sort_column_index]} {direction}"
    return selected


@ft.observable
class VirtualListState:
    """Keep mutable data operations outside the frozen declarative control tree."""

    def __init__(self):
        self._engine = None
        self.version = 0

    async def fetch(self, event):
        await self._engine._fetch(event)
        self.version += 1

    async def select(self, event):
        await self._engine._select(event)
        self.version += 1

    async def sort(self, event):
        await self._engine._sort(event)
        self.version += 1


@ft.component
def VirtualListScreen(state):
    if state._engine is None:
        state._engine = create_table(None)
    # Reading the observable revision subscribes only this screen. Each render
    # describes a fresh control; callbacks mutate the separate provider engine.
    _ = state.version
    engine = state._engine
    fields = (
        "columns", "row_count", "row_height", "column_widths", "response",
        "revision", "sort_column_index", "sort_ascending", "sortable",
        "show_checkbox_column", "selected_count", "heading_row_height",
    )
    table = FletVirtualTable(
        **{name: getattr(engine, name) for name in fields},
        key="virtual-list-grid",
        expand=True,
        on_range_request=state.fetch,
        on_selection_request=state.select,
        on_sort_request=state.sort,
    )
    return list_layout(table, muted(selection_text(engine)))
