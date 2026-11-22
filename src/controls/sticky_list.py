"""Pure Flet viewport: Canvas cells, row wheel steps, and an independent scrollbar.

No custom Flutter extension, HTML, JavaScript or virtual-table imports. Only
visible values enter the control tree. Canvas cells are text, not editable widgets.
"""
import time

import flet as ft
import flet.canvas as cv

from backend.list_window import ListWindow, wheel_step


class StickyListView(ft.Container):
    def __init__(self, columns, records, row_builder, *, column_widths=None,
                 numeric_columns=(), sort_keys=None, model=None, on_change=None, **kwargs):
        self.model = model if model is not None else ListWindow(records, row_builder, sort_keys=sort_keys)
        self.labels = tuple(columns)
        self.widths = tuple(column_widths or [140] * len(columns))
        if not self.labels or len(self.widths) != len(self.labels) or any(w < 60 for w in self.widths):
            raise ValueError("Provide a width of at least 60 for every column")
        self.numeric = set(numeric_columns)
        self.row_height, self.heading_height = 38, 46
        self.table_width = 52 + sum(self.widths)
        self.on_model_change = on_change
        self._attached = False
        self.last_draw_ms = 0
        self.canvas = cv.Canvas(
            key="pure-list-canvas", width=self.table_width, height=float("inf"),
            shapes=self.draw(), on_resize=self.resize, resize_interval=50,
        )
        self.gestures = ft.GestureDetector(
            content=self.canvas, on_scroll=self.wheel, on_tap_down=self.tap,
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

    def position_label(self):
        m = self.model
        end = min(m.count, m.first + m.visible)
        text = f"{m.first + 1 if m.count else 0:,}–{end:,} / {m.count:,}행  ·  {m.selected_count:,}행 선택"
        if m.sorting:
            text += "  ·  정렬 중…"
        elif m.sort_column_index is not None:
            text += f"  ·  {self.labels[m.sort_column_index]} {'오름차순' if m.sort_ascending else '내림차순'}"
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
                shapes.append(cv.Text(20, y + 7, "−" if partial else "✓", style=ft.TextStyle(size=13, color="white"), key=f"tick-{slot}"))

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
            self.canvas.shapes = self.draw()
            self.track.shapes = self.draw_track()
            self.position.value = self.position_label()
            if self._attached:
                self.page.update(self.canvas, self.track, self.position)

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

    async def tap(self, event):
        if event.local_position is None:
            return
        x, y = event.local_position.x, event.local_position.y
        if y < self.heading_height:
            if x < 52:
                self.model.toggle_all()
            else:
                boundary = 52
                for col, width in enumerate(self.widths):
                    boundary += width
                    if x < boundary:
                        task = self.model.sort(col)
                        # The worker yields during sorting; navigation stays usable.
                        await task
                        break
        else:
            slot = int((y - self.heading_height) // self.row_height)
            position = self.model.first + slot
            if slot >= self.model.visible or position >= self.model.count:
                return
            self.model.toggle(self.model.order[position])
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
