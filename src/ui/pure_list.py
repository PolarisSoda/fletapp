"""The comparison screen has no dependency on the local virtual-table package."""
import flet as ft

from backend.list_window import ListWindow
from backend.virtual_list import COLUMN_LABELS, COLUMN_WIDTHS, NUMERIC_COLUMNS, ROW_COUNT, row_values, sort_key
from controls.sticky_list import StickyListView
from ui.common import badge, heading, muted


def create_model():
    return ListWindow(range(ROW_COUNT), row_values,
                      sort_keys={i: sort_key(i) for i in range(len(COLUMN_LABELS))})


def create_control(model, on_change=None):
    return StickyListView(
        COLUMN_LABELS, model.records, model.row_builder,
        column_widths=COLUMN_WIDTHS, numeric_columns=NUMERIC_COLUMNS,
        model=model, on_change=on_change, expand=True, key="pure-list-grid",
    )


def layout(control):
    return ft.Column([
        heading("05", "순수 Flet 목록", "휠 한 번에 한 행씩 이동합니다. 오른쪽 스크롤바로 전체 범위를 탐색하세요."),
        ft.Row([badge(f"{ROW_COUNT:,}행"), badge(f"{len(COLUMN_LABELS)}열"), muted("동일한 샘플 학습 실험")]),
        control,
    ], spacing=14, expand=True, key="pure-list-screen")


class PureListView:
    def __init__(self):
        self.content = None
        self.model = None

    def build(self):
        if self.content is None:
            self.model = create_model()
            self.control = create_control(self.model)
            self.content = layout(self.control)
        return self.content


@ft.observable
class PureListState:
    def __init__(self):
        self._model = None
        self.version = 0

    def changed(self):
        self.version += 1


@ft.component
def PureListScreen(state):
    if state._model is None:
        state._model = create_model()
    _ = state.version
    return layout(create_control(state._model, state.changed))
