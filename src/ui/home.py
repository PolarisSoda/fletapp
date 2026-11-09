import flet as ft

from ui.common import ACCENT, NAV, TINT, badge, heading, muted, panel, title, view


def build_home(store, navigate):
    sections = (
        (1, "학습 실험", "데이터셋과 모델을 조합하고 파라미터를 설정합니다.", ft.Icons.SCIENCE_OUTLINED),
        (2, "학습 자동화", "저장된 실험을 대기열에 넣고 실행 단계를 확인합니다.", ft.Icons.ACCOUNT_TREE_OUTLINED),
        (3, "결과 확인", "이미지와 CSV를 나란히 보며 분류 결과를 확인합니다.", ft.Icons.IMAGE_SEARCH),
    )
    return view(
        heading("00", "홈", "이미지 분류 실험을 구성하고 결과를 검토하는 작업 공간입니다."),
        ft.Container(
            bgcolor=NAV,
            padding=28,
            border_radius=16,
            content=ft.Column(
                [
                    ft.Row([badge("IMAGE CLASSIFICATION")]),
                    ft.Text("Model Workbench", size=34, color="white", weight=ft.FontWeight.W_700),
                    ft.Text(
                        f"저장된 실험 {len(store.experiments)}개 · 샘플 분류 결과 제공",
                        color="#C1D1DF",
                        size=14,
                    ),
                    ft.Row(
                        [ft.FilledButton("학습 실험 열기", icon=ft.Icons.ARROW_FORWARD, on_click=lambda _: navigate(1))]
                    ),
                ],
                spacing=12,
            ),
        ),
        title("작업 공간"),
        ft.Row(
            [
                panel(
                    [
                        ft.Container(
                            content=ft.Icon(icon, color=ACCENT), bgcolor=TINT, padding=10, border_radius=10
                        ),
                        title(label, 17),
                        ft.Container(content=muted(description), height=44),
                        ft.TextButton("열기", on_click=lambda _, destination=index: navigate(destination)),
                    ],
                    expand=True,
                )
                for index, label, description, icon in sections
            ],
            spacing=14,
        ),
    )
