import flet as ft

from backend.experiments import ExperimentStore
from backend.results import ASSETS
from backend.transport import ExperimentSender, configured_sender
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


def main(
    page: ft.Page,
    store: ExperimentStore | None = None,
    sender: ExperimentSender | None = None,
):
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
    sender = sender if sender is not None else configured_sender()
    results = ResultsView(page)
    active = 0
    sidebar = ft.Container(
        width=194, padding=ft.Padding.symmetric(vertical=20, horizontal=14), bgcolor=NAV
    )
    body = ft.Container(expand=True, padding=ft.Padding.only(left=22, top=22, right=22))

    def apply_theme():
        seed = TRAINING_SEEDS[training.domain] if active == 1 else BASE_SEED
        if page.theme is not None and page.theme.color_scheme_seed == seed:
            return False
        page.theme = ft.Theme(color_scheme_seed=seed)
        page.dark_theme = ft.Theme(color_scheme_seed=seed)
        return True

    def toggle_theme(_):
        dark = page.theme_mode == ft.ThemeMode.DARK
        page.theme_mode = ft.ThemeMode.LIGHT if dark else ft.ThemeMode.DARK
        theme_button.content = "다크 모드" if dark else "라이트 모드"
        theme_button.icon = ft.Icons.DARK_MODE if dark else ft.Icons.LIGHT_MODE

    def navigate(index):
        nonlocal active
        previous = active
        active = index
        theme_changed = apply_theme()
        buttons[previous].style = nav_style(False)
        buttons[index].style = nav_style(True)
        render_view()
        if body.parent is not None and not theme_changed:
            page.update(body, *[buttons[item] for item in dict.fromkeys((previous, index))])

    def nav_style(selected):
        return ft.ButtonStyle(
            bgcolor=NAV_SELECTED if selected else NAV,
            color="white",
            icon_color="#83E3CC" if selected else "#B8CBDA",
            shape=ft.RoundedRectangleBorder(radius=9),
            padding=ft.Padding.symmetric(vertical=12, horizontal=12),
            alignment=ft.Alignment.CENTER_LEFT,
        )

    buttons = [
        ft.TextButton(
            label, key=f"nav-{index}", icon=icon, width=166,
            on_click=lambda _, destination=index: navigate(destination),
        )
        for index, (label, icon) in enumerate(NAVIGATION)
    ]
    theme_button = ft.TextButton(
        "다크 모드",
        key="theme-toggle",
        icon=ft.Icons.DARK_MODE,
        style=ft.ButtonStyle(color="#DCE8F3", icon_color="#DCE8F3"),
        on_click=toggle_theme,
    )

    def build_sidebar():
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
                *buttons,
                ft.Column(expand=True),
                theme_button,
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
            results.build,
        )
        body.content = builders[active]()

    training = TrainingView(page, store, apply_theme)
    automation = AutomationView(page, store, lambda: active == 2, sender)
    build_sidebar()
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
