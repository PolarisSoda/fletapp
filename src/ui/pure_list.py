"""The comparison screen has no dependency on the local virtual-table package."""
import flet as ft

from backend.list_window import ListWindow
from backend.virtual_list import COLUMN_LABELS, COLUMN_WIDTHS, NUMERIC_COLUMNS, ROW_COUNT, row_values, sort_key
from controls.sticky_list import StickyListView
from controls.windowed_list_view import WindowedListView
from ui.common import badge, heading


def create_model():
    model = ListWindow(range(ROW_COUNT), row_values,
                       sort_keys={i: sort_key(i) for i in range(len(COLUMN_LABELS))})
    model.rich_cells = False
    model.use_prototype = False
    model.cell_actions = {}
    model.feedback = ""
    return model


def create_control(model, on_change=None, *, native=False):
    def action(row_id):
        model.cell_actions[row_id] = model.cell_actions.get(row_id, 0) + 1
        model.feedback = f"행 {row_id + 1:,} 실행 {model.cell_actions[row_id]}회"
        control.refresh()

    def cell_builder(record, row_id, col):
        if not model.rich_cells or col != 1:
            return None
        return ft.Row([
            ft.Icon(ft.Icons.SCIENCE_OUTLINED, size=14, color="#087F70"),
            ft.Column([
                ft.Text(model.values(row_id)[1], size=10, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text("Row / Column", size=9, color="#516274"),
            ], expand=True, spacing=0, alignment=ft.MainAxisAlignment.CENTER),
            ft.IconButton(ft.Icons.PLAY_ARROW, icon_size=14, width=22, height=28, padding=0,
                          tooltip=f"행 {row_id + 1} 실행", on_click=lambda _, rid=row_id: action(rid)),
        ], spacing=3)

    cls = WindowedListView if native else StickyListView
    extra = {"use_prototype": model.use_prototype} if native else {}
    control = cls(
        COLUMN_LABELS, model.records, model.row_builder,
        column_widths=COLUMN_WIDTHS, numeric_columns=NUMERIC_COLUMNS,
        model=model, on_change=on_change, cell_builder=cell_builder,
        expand=True, key="listview-grid" if native else "pure-list-grid", **extra,
    )
    return control


def layout(control, on_options=None, *, native=False):
    model = control.model

    def rich(event):
        model.rich_cells = event.control.value
        on_options()

    def prototype(event):
        model.use_prototype = event.control.value
        on_options()

    options = [ft.Switch(label="복합 셀", value=model.rich_cells, on_change=rich, key="rich-cells")]
    if native:
        options.append(ft.Switch(label="prototype", value=model.use_prototype, on_change=prototype, key="list-prototype"))
    return ft.Column([
        heading("06" if native else "05", "ListView 목록" if native else "순수 Flet 목록",
                "기본 ListView · 고정 헤더 · 실제 행 컨트롤 · 한 행 단위 휠" if native else "Canvas 위에 실제 셀 컨트롤을 올릴 수 있습니다. 복합 셀을 켜서 확인하세요."),
        ft.Row([badge(f"{ROW_COUNT:,}행"), badge(f"{len(COLUMN_LABELS)}열"), *options]),
        control,
    ], spacing=14, expand=True, key="listview-screen" if native else "pure-list-screen")


class PureListView:
    def __init__(self, *, native=False):
        self.content = None
        self.model = None
        self.native = native

    def build(self):
        if self.content is None:
            self.model = create_model()
            self.control = create_control(self.model, native=self.native)
            self.content = layout(self.control, self.rebuild, native=self.native)
        return self.content

    def rebuild(self):
        # Keep the mounted imperative control and its mutable update boundary.
        # Replacing a same-key subtree makes Flet reconcile it as frozen input.
        self.control.refresh()


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
    return layout(create_control(state._model, state.changed), state.changed)


@ft.component
def ListViewScreen(state):
    if state._model is None:
        state._model = create_model()
    _ = state.version
    return layout(create_control(state._model, state.changed, native=True), state.changed, native=True)
