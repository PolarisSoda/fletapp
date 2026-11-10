import flet as ft

from backend.results import load_predictions
from ui.common import ACCENT, badge, heading, muted, panel, title, view


class ResultsView:
    def __init__(self, page):
        self.page = page
        self.errors_only = False
        self.selected = None

    def build(self):
        try:
            predictions = load_predictions()
        except (OSError, ValueError, TypeError) as error:
            return error_view(error)

        visible = visible_rows(predictions, self.errors_only)
        if self.selected not in visible:
            self.selected = next(iter(visible), None)

        def select(row):
            self.selected = row
            for data_row, prediction in zip(table.rows, visible):
                data_row.selected = prediction == row
            preview.content.controls = preview_controls(row)
            self.page.update(table, preview)

        def filter_rows(event):
            nonlocal visible
            self.errors_only = event.control.value
            visible = visible_rows(predictions, self.errors_only)
            if self.selected not in visible:
                self.selected = next(iter(visible), None)
            table.rows = table_rows(visible, self.selected, select)
            table_area.controls = [table] if visible else [muted("표시할 결과가 없습니다.")]
            count.value = count_label(visible)
            preview.content.controls = preview_controls(self.selected)
            self.page.update(table_area, count, preview)

        table = make_table(table_rows(visible, self.selected, select))
        table_area = ft.Row(
            [table] if visible else [muted("표시할 결과가 없습니다.")], scroll=ft.ScrollMode.AUTO,
        )
        count = muted(count_label(visible))
        preview = panel(preview_controls(self.selected), width=330)
        return results_layout(predictions, self.errors_only, filter_rows, table_area, count, preview)


def results_layout(predictions, errors_only, on_filter, table_area, count, preview):
    correct = sum(row.correct for row in predictions)
    return view(
        heading("03", "결과 확인", "CSV에 저장된 이미지 분류 결과를 비교하세요."),
        ft.Row(
            [
                panel([muted("전체 이미지"), title(str(len(predictions)), 26)], expand=True),
                panel(
                    [muted("정확도"), title(f"{correct / len(predictions):.1%}" if predictions else "—", 26)],
                    expand=True,
                ),
                panel([muted("오분류"), title(str(len(predictions) - correct), 26)], expand=True),
            ]
        ),
        ft.Row(
            [
                panel(
                    [
                        ft.Row(
                            [title("분류 결과"), ft.Switch(label="오분류만", value=errors_only, on_change=on_filter)],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        table_area,
                        count,
                    ],
                    expand=True,
                ),
                preview,
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def error_view(error):
    return view(
        heading("03", "결과 확인", "샘플 이미지와 분류 결과를 확인하세요."),
        panel([muted(f"CSV를 읽을 수 없습니다. {error}")]),
    )


def preview_controls(row):
    label = title("이미지 미리보기", 17)
    if row is None:
        return [label, muted("선택한 이미지가 없습니다.")]
    return [
        label,
        ft.Image(
            src=f"samples/{row.image}", fit=ft.BoxFit.CONTAIN,
            height=180, width=292, border_radius=10,
        ),
        title(row.filename, 15),
        muted(f"데이터 분할 · {row.split}"),
        muted(f"정답 · {row.actual}   /   예측 · {row.predicted}"),
        ft.ProgressBar(value=row.confidence, color=ACCENT),
        muted(f"예측 신뢰도 {row.confidence:.1%}"),
    ]


def make_table(rows):
    return ft.DataTable(
        columns=[ft.DataColumn(ft.Text(label)) for label in ("파일", "정답", "예측", "신뢰도", "판정")],
        column_spacing=19,
        show_checkbox_column=False,
        rows=rows,
    )


def table_rows(visible, selected, select):
    return [
        ft.DataRow(
            selected=row == selected,
            on_select_change=lambda _, item=row: select(item),
            cells=[
                ft.DataCell(ft.Text(row.filename)),
                ft.DataCell(ft.Text(row.actual)),
                ft.DataCell(ft.Text(row.predicted)),
                ft.DataCell(ft.Text(f"{row.confidence:.1%}")),
                ft.DataCell(
                    badge("일치") if row.correct
                    else badge("오분류", ft.Colors.ON_ERROR_CONTAINER, ft.Colors.ERROR_CONTAINER)
                ),
            ],
        )
        for row in visible
    ]


def visible_rows(predictions, errors_only):
    return [row for row in predictions if not errors_only or not row.correct]


def count_label(visible):
    return f"predictions.csv · {len(visible)}건 표시"
