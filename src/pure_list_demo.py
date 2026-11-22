"""Stock Flet client entry point: flet run src/pure_list_demo.py --web."""
import flet as ft

from ui.pure_list import PureListView


def main(page: ft.Page):
    page.title = "Pure Flet — 500,000 rows"
    page.padding = 22
    page.add(PureListView().build())


if __name__ == "__main__":
    ft.run(main)
