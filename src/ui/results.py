import flet as ft

from backend.results import load_predictions
from ui.common import ACCENT, BG, badge, heading, muted, panel, title, view


class ResultsView:
    def __init__(self):
        self.errors_only = False
        self.selected = None

    def build(self, refresh):
        try:
            predictions = load_predictions()
        except (OSError, ValueError, TypeError) as error:
            return view(
                heading("03", "결과 확인", "샘플 이미지와 분류 결과를 확인하세요."),
                panel([muted(f"CSV를 읽을 수 없습니다. {error}")]),
            )
        correct = sum(row.correct for row in predictions)
        visible = [row for row in predictions if not self.errors_only or not row.correct]
        if self.selected not in visible:
            self.selected = next(iter(visible), None)

        def filter_rows(event):
            self.errors_only = event.control.value
            refresh()

        def select(row):
            self.selected = row
            refresh()

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(label))
                for label in ("파일", "정답", "예측", "신뢰도", "판정")
            ],
            column_spacing=19,
            show_checkbox_column=False,
            rows=[
                ft.DataRow(
                    selected=row == self.selected,
                    on_select_change=lambda _, item=row: select(item),
                    cells=[
                        ft.DataCell(ft.Text(row.filename)),
                        ft.DataCell(ft.Text(row.actual)),
                        ft.DataCell(ft.Text(row.predicted)),
                        ft.DataCell(ft.Text(f"{row.confidence:.1%}")),
                        ft.DataCell(self.verdict(row)),
                    ],
                )
                for row in visible
            ],
        )
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
                                [
                                    title("분류 결과"),
                                    ft.Switch(
                                        label="오분류만", value=self.errors_only, on_change=filter_rows
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Row([table], scroll=ft.ScrollMode.AUTO)
                            if visible else muted("표시할 결과가 없습니다."),
                            muted(f"predictions.csv · {len(visible)}건 표시"),
                        ],
                        expand=True,
                    ),
                    self.preview(),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        )

    @staticmethod
    def verdict(row):
        if row.correct:
            return badge("일치")
        return badge("오분류", "#A73438", "#FBE7E8")

    def preview(self):
        row = self.selected
        if row is None:
            return panel([title("이미지 미리보기", 17), muted("선택한 이미지가 없습니다.")], width=330)
        return panel(
            [
                title("이미지 미리보기", 17),
                ft.Container(
                    content=ft.Image(src=f"samples/{row.image}", fit=ft.BoxFit.CONTAIN),
                    height=180,
                    width=292,
                    bgcolor=BG,
                    border_radius=10,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
                title(row.filename, 15),
                muted(f"데이터 분할 · {row.split}"),
                muted(f"정답 · {row.actual}   /   예측 · {row.predicted}"),
                ft.ProgressBar(value=row.confidence, color=ACCENT),
                muted(f"예측 신뢰도 {row.confidence:.1%}"),
            ],
            width=330,
        )
