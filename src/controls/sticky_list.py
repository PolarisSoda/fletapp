"""Pure Flet viewport: Canvas cells, row wheel steps, and an independent scrollbar.

No custom Flutter extension, HTML, JavaScript or virtual-table imports. Only
visible values enter the control tree. Optional cell_builder controls are placed
over Canvas cells; hit targets use native controls, not inferred pointer offsets.
"""
import time

import flet as ft
import flet.canvas as cv

from backend.list_window import ListWindow, wheel_step


class StickyListView(ft.Container):
    def __init__(self, columns, records, row_builder, *, column_widths=None,
                 numeric_columns=(), sort_keys=None, model=None, on_change=None,
                 cell_builder=None, row_height=38, heading_height=46, **kwargs):
        self.model = model if model is not None else ListWindow(records, row_builder, sort_keys=sort_keys)
        self.labels = tuple(columns)
        self.widths = tuple(column_widths or [140] * len(columns))
        if not self.labels or len(self.widths) != len(self.labels) or any(w < 60 for w in self.widths):
            raise ValueError("Provide a width of at least 60 for every column")
        self.numeric = set(numeric_columns)
        if row_height < 20 or heading_height < 20:
            raise ValueError("Row and heading heights must be at least 20")
        self.row_height, self.heading_height = row_height, heading_height
        self.model.resize(self.model.height, row_height, heading_height)
        self.table_width = 52 + sum(self.widths)
        self.on_model_change = on_change
        self.cell_builder = cell_builder
        self._attached = False
        self.last_draw_ms = 0
        self.canvas = self.create_surface()
        self.gestures = ft.GestureDetector(
            content=self.canvas, on_scroll=self.wheel,
            width=self.table_width, height=float("inf"), key="pure-list-input",
        )
        self.track = cv.Canvas(
            width=22, expand=True, shapes=self.draw_track(), on_resize=self.resize_track,
            resize_interval=50, key="pure-list-track-canvas",
        )
        self.track_input = ft.GestureDetector(
            content=self.track, expand=True, on_tap_down=self.track_tap,
            on_vertical_drag_start=self.drag_start, on_vertical_drag_update=self.drag,
            on_scroll=self.wheel, drag_interval=16, key="pure-list-track",
        )
        self.position = ft.Text(self.position_label(), size=12, color="#516274", key="pure-list-position")
        super().__init__(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Row([self.gestures], scroll=ft.ScrollMode.ALWAYS, spacing=0,
                                       vertical_alignment=ft.CrossAxisAlignment.STRETCH),
                        expand=True, clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ),
                    ft.Column([
                        ft.IconButton(ft.Icons.KEYBOARD_ARROW_UP, height=28, width=22,
                                      padding=0, on_click=lambda _: self.move(self.model.first - 1)),
                        self.track_input,
                        ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN, height=28, width=22,
                                      padding=0, on_click=lambda _: self.move(self.model.first + 1)),
                    ], spacing=0, width=22),
                ], expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.STRETCH),
                ft.Row([
                    ft.TextButton("처음", on_click=lambda _: self.move(0)),
                    ft.TextButton("끝", on_click=lambda _: self.move(self.model.maximum)),
                    self.position,
                ], spacing=8),
            ], spacing=4, expand=True),
            bgcolor="#FFFFFF", border=ft.Border.all(1, "#D5DBE3"),
            border_radius=10, clip_behavior=ft.ClipBehavior.HARD_EDGE, **kwargs,
        )

    def did_mount(self):
        self._attached = True

    def will_unmount(self):
        self._attached = False

    def create_surface(self):
        return cv.Canvas(
            key="pure-list-canvas", width=self.table_width, height=float("inf"),
            shapes=self.draw(), content=self.overlay(), on_resize=self.resize, resize_interval=50,
        )

    def overlay(self):
        """Native bounds share the painter's origin; IDs bind the painted record.

        A cell control is a sibling above its row hit target. Its own buttons and
        fields therefore receive input without also toggling row selection.
        """
        hits = [self.hit_box("전체 선택", self.toggle_all, 0, 0, 52, self.heading_height,
                             key="canvas-select-all")]
        x = 52
        for col, width in enumerate(self.widths):
            async def sort(_, column=col):
                await self.sort_column(column)
            hits.append(self.hit_box(f"{self.labels[col]} 정렬", sort, x, 0, width, self.heading_height,
                                     key=f"canvas-sort-{col}"))
            x += width
        for slot, (row_id, values) in enumerate(self.model.rows()):
            y = self.heading_height + slot * self.row_height
            hits.append(self.hit_box(f"행 {row_id + 1} 선택", lambda _, rid=row_id: self.select_row(rid),
                                     0, y, self.table_width, self.row_height, key=f"canvas-row-{row_id}"))
            if self.cell_builder is not None:
                x = 52
                for col, width in enumerate(self.widths):
                    content = self.cell_builder(self.model.records[row_id], row_id, col)
                    if content is not None:
                        hits.append(ft.Container(
                            content=content, left=x, top=y, width=width, height=self.row_height,
                            padding=ft.Padding.symmetric(horizontal=8), bgcolor="#D5E8FA" if self.model.selected(row_id) else "white",
                            clip_behavior=ft.ClipBehavior.HARD_EDGE, key=f"canvas-cell-{row_id}-{col}",
                            on_click=lambda _, rid=row_id: self.select_row(rid),
                        ))
                    x += width
        return ft.Stack(hits, fit=ft.StackFit.EXPAND, clip_behavior=ft.ClipBehavior.HARD_EDGE)

    @staticmethod
    def hit_box(label, handler, x, y, width, height, *, key):
        return ft.Container(
            content=ft.Semantics(label=label, button=True, content=ft.Container(expand=True)),
            left=x, top=y, width=width, height=height, bgcolor=ft.Colors.TRANSPARENT,
            on_click=handler, key=key,
        )

    def select_row(self, row_id, selected=None):
        if selected is None or self.model.selected(row_id) != selected:
            self.model.toggle(row_id)
            self.refresh()

    def toggle_all(self, _=None):
        self.model.toggle_all()
        self.refresh()

    async def sort_column(self, column):
        await self.model.sort(column)
        self.refresh()

    def position_label(self):
        m = self.model
        end = min(m.count, m.first + m.visible)
        text = f"{m.first + 1 if m.count else 0:,}–{end:,} / {m.count:,}행  ·  {m.selected_count:,}행 선택"
        if m.count != m.total_count:
            text += f"  ·  전체 {m.total_count:,}행"
        if m.filtering:
            text += "  ·  필터 적용 중…"
        elif m.sorting:
            text += "  ·  정렬 중…"
        elif m.sort_column_index is not None:
            text += f"  ·  {self.labels[m.sort_column_index]} {'오름차순' if m.sort_ascending else '내림차순'}"
        if getattr(m, "feedback", ""):
            text += f"  ·  {m.feedback}"
        return text

    def draw(self):
        started = time.perf_counter()
        shapes = [cv.Rect(0, 0, self.table_width, self.heading_height, paint=ft.Paint(color="#E8EDF5"))]
        ink = ft.TextStyle(size=14, color="#202830")
        line = ft.Paint(color="#DDDDDD", stroke_width=.5)

        def checkbox(slot, y, checked, partial=False):
            shapes.append(cv.Rect(18, y + (self.row_height - 16) / 2, 16, 16,
                                  key=f"check-{slot}", paint=ft.Paint(color="#087F70" if checked else "#64717D",
                                  style=ft.PaintingStyle.FILL if checked else ft.PaintingStyle.STROKE, stroke_width=1.5)))
            if checked or partial:
                pen = ft.Paint(color="white", stroke_width=1.6)
                cy = y + self.row_height / 2
                if partial:
                    shapes.append(cv.Line(21, cy, 31, cy, paint=pen, key=f"tick-{slot}"))
                else:
                    shapes.extend([cv.Line(21, cy, 25, cy + 4, paint=pen, key=f"tick-a-{slot}"),
                                   cv.Line(25, cy + 4, 32, cy - 5, paint=pen, key=f"tick-b-{slot}")])

        checkbox("header", 4, self.model.selected_count > 0,
                 0 < self.model.selected_count < self.model.count)
        x = 52
        for col, (label, width) in enumerate(zip(self.labels, self.widths)):
            arrow = "↕" if self.model.sort_column_index != col else "↑" if self.model.sort_ascending else "↓"
            shapes.append(cv.Text(x + 12, 13, label, style=ink, max_width=width - 36, max_lines=1, ellipsis="…", key=f"heading-{col}"))
            shapes.append(cv.Text(x + width - 24, 13, arrow, style=ink, key=f"sort-{col}"))
            x += width
        for slot, (row_id, values) in enumerate(self.model.rows()):
            if len(values) != len(self.labels):
                raise ValueError("Row cell count does not match columns")
            y = self.heading_height + slot * self.row_height
            if self.model.selected(row_id):
                shapes.append(cv.Rect(0, y, self.table_width, self.row_height, paint=ft.Paint(color="#D5E8FA"), key=f"selected-{slot}"))
            checkbox(slot, y, self.model.selected(row_id))
            x = 52
            for col, (value, width) in enumerate(zip(values, self.widths)):
                shapes.append(cv.Text(
                    x + width - 12 if col in self.numeric else x + 12, y + 10,
                    "" if value is None else str(value), style=ink,
                    alignment=ft.Alignment.TOP_RIGHT if col in self.numeric else ft.Alignment.TOP_LEFT,
                    max_width=width - 24, max_lines=1, ellipsis="…", key=f"cell-{slot}-{col}",
                ))
                x += width
            shapes.append(cv.Line(0, y + self.row_height, self.table_width, y + self.row_height, paint=line, key=f"line-{slot}"))
        if not self.model.count:
            shapes.append(cv.Text(24, self.heading_height + 20, "조건에 맞는 데이터가 없습니다.", style=ink))
        self.last_draw_ms = (time.perf_counter() - started) * 1000
        return shapes

    def draw_track(self):
        top, height, _ = self.model.thumb()
        return [cv.Rect(0, 0, 22, self.model.track_height, paint=ft.Paint(color="#F0F3F6")),
                cv.Rect(5, top, 12, height, border_radius=5, paint=ft.Paint(color="#8E9AA7"))]

    def refresh(self):
        if self.on_model_change is not None:
            self.on_model_change()
        else:
            self.refresh_surface()
            self.track.shapes = self.draw_track()
            self.position.value = self.position_label()
            if self._attached:
                self.page.update(self.canvas, self.track, self.position)

    def refresh_surface(self):
        self.canvas.shapes = self.draw()
        self.canvas.content = self.overlay()

    def move(self, first):
        if self.model.move(first):
            self.refresh()

    def wheel(self, event):
        delta = event.scroll_delta
        if abs(delta.y) >= abs(delta.x) and delta.y:
            self.move(self.model.first + wheel_step(delta.y))

    def resize(self, event):
        if self.model.resize(event.height, self.row_height, self.heading_height):
            self.refresh()

    def resize_track(self, event):
        if event.height > 0 and self.model.track_height != event.height:
            self.model.track_height = event.height
            self.refresh()

    def track_tap(self, event):
        if event.local_position is not None:
            top, height, _ = self.model.thumb()
            y = event.local_position.y
            if not top <= y <= top + height:
                self._seek(y, height / 2)

    def drag_start(self, event):
        top, height, _ = self.model.thumb()
        y = event.local_position.y
        self.model.drag_offset = y - top if top <= y <= top + height else height / 2

    def drag(self, event):
        self._seek(event.local_position.y, self.model.drag_offset)

    def _seek(self, y, offset):
        travel = self.model.thumb()[2]
        self.move((y - offset) / max(1, travel) * self.model.maximum)
