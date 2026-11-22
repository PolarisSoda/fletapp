"""A real stock Flet ListView with bounded Python rows and fixed headings.

on-demand/prototype optimize Flutter widgets; ListWindow separately bounds Python
construction. The list fits whole visible rows, so native pixel-wheel scrolling
cannot race the logical one-row wheel handler. The independent thumb addresses
the entire provider. Native Flet cells/rows can contain arbitrary controls.
"""
import flet as ft

from controls.sticky_list import StickyListView


class WindowedListView(StickyListView):
    def __init__(self, *args, use_prototype=False, row_control_builder=None, **kwargs):
        self.use_prototype = use_prototype
        self.row_control_builder = row_control_builder
        super().__init__(*args, **kwargs)

    def create_surface(self):
        self.list_view = ft.ListView(
            controls=self.build_rows(), expand=True, spacing=0, padding=0,
            build_controls_on_demand=True,
            item_extent=None if self.use_prototype else self.row_height,
            prototype_item=ft.Container(height=self.row_height) if self.use_prototype else None,
            cache_extent=self.row_height * 2, key="native-window-list",
        )
        return ft.Container(
            width=self.table_width, height=float("inf"), key="native-list-surface",
            on_size_change=self.resize, size_change_interval=50,
            content=ft.Column([self.build_header(), self.list_view], spacing=0, expand=True),
        )

    def build_header(self):
        partial = 0 < self.model.selected_count < self.model.count
        controls = [ft.Container(
            content=ft.Checkbox(value=None if partial else self.model.selected_count > 0,
                                tristate=partial, on_change=self.toggle_all, tooltip="전체 선택"),
            width=52, height=self.heading_height, alignment=ft.Alignment.CENTER,
        )]
        for col, (label, width) in enumerate(zip(self.labels, self.widths)):
            async def sort(_, column=col):
                await self.sort_column(column)
            arrow = ft.Icons.UNFOLD_MORE if self.model.sort_column_index != col else ft.Icons.ARROW_UPWARD if self.model.sort_ascending else ft.Icons.ARROW_DOWNWARD
            controls.append(ft.Container(
                content=ft.Row([ft.Text(label, size=14, expand=True), ft.Icon(arrow, size=14)], spacing=2),
                width=width, height=self.heading_height, on_click=sort,
                padding=ft.Padding.symmetric(horizontal=12), key=f"list-sort-{col}", tooltip=f"{label} 정렬",
            ))
        return ft.Container(ft.Row(controls, spacing=0), height=self.heading_height, bgcolor="#E8EDF5", key="native-list-header")

    def build_rows(self):
        controls = []
        for row_id, values in self.model.rows():
            if len(values) != len(self.labels):
                raise ValueError("Row cell count does not match columns")
            if self.row_control_builder is not None:
                content = self.row_control_builder(self.model.records[row_id], row_id, self.model.selected(row_id))
            else:
                cells = [ft.Container(
                    ft.Checkbox(value=self.model.selected(row_id), on_change=lambda e, rid=row_id: self.select_row(rid, e.control.value)),
                    width=52, alignment=ft.Alignment.CENTER,
                )]
                for col, (value, width) in enumerate(zip(values, self.widths)):
                    child = self.cell_builder(self.model.records[row_id], row_id, col) if self.cell_builder else None
                    cells.append(ft.Container(
                        child if child is not None else ft.Text(str(value) if value is not None else "", size=14,
                                                               max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        width=width, height=self.row_height, padding=ft.Padding.symmetric(horizontal=12),
                        alignment=ft.Alignment.CENTER_RIGHT if col in self.numeric else ft.Alignment.CENTER_LEFT,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ))
                content = ft.Row(cells, spacing=0, vertical_alignment=ft.CrossAxisAlignment.STRETCH)
            controls.append(ft.Container(
                content, height=self.row_height, key=f"list-row-{row_id}",
                bgcolor="#D5E8FA" if self.model.selected(row_id) else "white",
                border=ft.Border.only(bottom=ft.BorderSide(.5, "#DDDDDD")),
                on_click=lambda _, rid=row_id: self.select_row(rid), tooltip=f"행 {row_id + 1} 선택",
            ))
        return controls

    def refresh_surface(self):
        self.use_prototype = getattr(self.model, "use_prototype", self.use_prototype)
        self.list_view.item_extent = None if self.use_prototype else self.row_height
        self.list_view.prototype_item = ft.Container(height=self.row_height) if self.use_prototype else None
        self.list_view.controls = self.build_rows()
        self.canvas.content.controls = [self.build_header(), self.list_view]
