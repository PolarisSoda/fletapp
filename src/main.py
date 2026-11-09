import flet as ft

from backend.experiments import ExperimentStore
from backend.results import ASSETS
from ui.automation import AutomationView
from ui.common import BASE_SEED, BG, NAV, NAV_SELECTED, badge
from ui.home import build_home
from ui.results import ResultsView
from ui.training import TRAINING_SEEDS, TrainingView


NAVIGATION = (
    ("홈", ft.Icons.SPACE_DASHBOARD_OUTLINED),
    ("학습 실험", ft.Icons.SCIENCE_OUTLINED),
    ("학습 자동화", ft.Icons.ACCOUNT_TREE_OUTLINED),
    ("결과 확인", ft.Icons.IMAGE_SEARCH),
)


def main(page: ft.Page, store: ExperimentStore | None = None):
    page.title = "Model Workbench"
    page.padding = 0
    page.spacing = 0
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 1440
    page.window.height = 880
    page.window.min_width = 1200
    page.window.min_height = 680

    store = store if store is not None else ExperimentStore()
    results = ResultsView()
    active = 0
    sidebar = ft.Container(
        width=194, padding=ft.Padding.symmetric(vertical=20, horizontal=14), bgcolor=NAV
    )
    body = ft.Container(expand=True, padding=ft.Padding.only(left=22, top=22, right=22))

    def apply_theme():
        seed = TRAINING_SEEDS[training.domain] if active == 1 else BASE_SEED
        page.theme = ft.Theme(color_scheme_seed=seed)
        page.dark_theme = ft.Theme(color_scheme_seed=seed)

    def toggle_theme(_):
        dark = page.theme_mode == ft.ThemeMode.DARK
        page.theme_mode = ft.ThemeMode.LIGHT if dark else ft.ThemeMode.DARK
        render_sidebar()

    def navigate(index):
        nonlocal active
        active = index
        apply_theme()
        render_sidebar()
        render_view()

    def render_sidebar():
        dark = page.theme_mode == ft.ThemeMode.DARK
        sidebar.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.HUB_OUTLINED, color=NAV, size=20),
                            bgcolor="#7ADCC3",
                            padding=8,
                            border_radius=9,
                        ),
                        ft.Column(
                            [
                                ft.Text("MODEL", color="white", weight=ft.FontWeight.W_700, size=14),
                                ft.Text("WORKBENCH", color="#B8CBDA", size=10),
                            ],
                            spacing=0,
                        ),
                    ]
                ),
                ft.Container(
                    content=ft.Text("작업 공간", color="#A0B6C8", size=11),
                    padding=ft.Padding.only(top=22, left=8, bottom=2),
                ),
                *[
                    ft.Container(
                        key=f"nav-{index}",
                        bgcolor=NAV_SELECTED if index == active else NAV,
                        border_radius=9,
                        padding=ft.Padding.symmetric(vertical=12, horizontal=12),
                        on_click=lambda _, destination=index: navigate(destination),
                        content=ft.Row(
                            [
                                ft.Icon(icon, color="#83E3CC" if index == active else "#B8CBDA", size=20),
                                ft.Text(label, color="white", size=14),
                            ],
                            spacing=10,
                        ),
                    )
                    for index, (label, icon) in enumerate(NAVIGATION)
                ],
                ft.Container(expand=True),
                ft.TextButton(
                    "라이트 모드" if dark else "다크 모드",
                    key="theme-toggle",
                    icon=ft.Icons.LIGHT_MODE if dark else ft.Icons.DARK_MODE,
                    style=ft.ButtonStyle(color="#DCE8F3", icon_color="#DCE8F3"),
                    on_click=toggle_theme,
                ),
                ft.Row([badge("DEMO", color=NAV, background="#E3F4EF")]),
                ft.Text("로컬 실험 작업 공간", color="#B8CBDA", size=11),
            ],
            spacing=6,
        )

    def render_view():
        builders = (
            lambda: build_home(store, navigate),
            training.build,
            automation.build,
            lambda: results.build(render_view),
        )
        body.content = builders[active]()

    def refresh_automation():
        if active == 2:
            render_view()

    training = TrainingView(page, store, apply_theme)
    automation = AutomationView(page, store, refresh_automation)
    navigate(0)
    page.add(
        ft.Row(
            [sidebar, body],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    )


if __name__ == "__main__":
    ft.run(main, assets_dir=str(ASSETS))
