"""Standalone stock Flet ListView comparison, without the local grid extension."""
import flet as ft
from ui.pure_list import PureListView


def main(page: ft.Page):
    page.title = "Flet ListView — 500,000 rows"
    page.padding = 22
    page.theme_mode = ft.ThemeMode.LIGHT
    page.add(PureListView(native=True).build())


if __name__ == "__main__":
    ft.run(main)
