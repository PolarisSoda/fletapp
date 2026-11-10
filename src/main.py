import flet as ft

from backend.experiments import ANIMALS, ExperimentStore
from backend.results import ASSETS
from ui.automation import AutomationView
from ui.common import BASE_SEED, BG, NAV, NAV_SELECTED, badge
from ui.home import build_home
from ui.results import ResultsView
from ui.training import TRAINING_SEEDS, TrainingScreen, TrainingState


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

    def apply_theme(seed):
        page.theme = ft.Theme(color_scheme_seed=seed)
        page.dark_theme = ft.Theme(color_scheme_seed=seed)

    def build_sidebar(active, dark, navigate, toggle_theme):
        content = ft.Column(
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
        return ft.Container(
            width=194, padding=ft.Padding.symmetric(vertical=20, horizontal=14),
            bgcolor=NAV, content=content,
        )

    @ft.component
    def Workbench():
        active, set_active = ft.use_state(0)
        domain, set_domain = ft.use_state(ANIMALS)
        dark, set_dark = ft.use_state(False)
        _, set_revision = ft.use_state(0)
        training = ft.use_memo(TrainingState, [])

        def refresh():
            set_revision(lambda revision: revision + 1)

        automation = ft.use_memo(lambda: AutomationView(page, store, refresh), [])

        def navigate(index):
            apply_theme(TRAINING_SEEDS[domain] if index == 1 else BASE_SEED)
            set_active(index)

        def change_domain(next_domain):
            apply_theme(TRAINING_SEEDS[next_domain])
            set_domain(next_domain)

        def toggle_theme(_):
            next_dark = page.theme_mode != ft.ThemeMode.DARK
            page.theme_mode = ft.ThemeMode.DARK if next_dark else ft.ThemeMode.LIGHT
            set_dark(next_dark)

        builders = (
            lambda: build_home(store, navigate),
            lambda: TrainingScreen(store, training, domain, change_domain),
            automation.build,
            lambda: results.build(refresh),
        )
        return ft.Row(
            [
                build_sidebar(active, dark, navigate, toggle_theme),
                ft.Container(
                    key=f"screen-{active}",
                    content=builders[active](),
                    expand=True,
                    padding=ft.Padding.only(left=22, top=22, right=22),
                ),
            ],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    apply_theme(BASE_SEED)
    page.render(Workbench)


if __name__ == "__main__":
    ft.run(main, assets_dir=str(ASSETS))
