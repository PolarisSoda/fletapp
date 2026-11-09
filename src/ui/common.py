import flet as ft


BG = "#F2F5F8"
WHITE = "#FFFFFF"
INK = "#182736"
MUTED = "#536578"
LINE = "#DCE4EC"
ACCENT = "#087F70"
TINT = "#E3F4EF"
NAV = "#142435"
NAV_SELECTED = "#234457"


def title(value, size=20):
    return ft.Text(value, size=size, color=INK, weight=ft.FontWeight.W_700)


def muted(value, size=13):
    return ft.Text(value, size=size, color=MUTED)


def badge(value, color=ACCENT, background=TINT):
    return ft.Container(
        content=ft.Text(value, size=11, color=color, weight=ft.FontWeight.W_700),
        bgcolor=background,
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
    )


def panel(controls, *, width=None, expand=None, padding=18, spacing=12):
    return ft.Container(
        content=ft.Column(controls, spacing=spacing),
        width=width,
        expand=expand,
        padding=padding,
        border_radius=14,
        border=ft.Border.all(1, LINE),
        bgcolor=WHITE,
    )


def heading(index, name, description):
    return ft.Column(
        [
            ft.Text(f"WORKSPACE  /  {index}", size=11, color=ACCENT, weight=ft.FontWeight.W_700),
            title(name, 30),
            muted(description, 14),
        ],
        spacing=5,
    )


def view(*controls):
    return ft.Column(list(controls), spacing=20, expand=True, scroll=ft.ScrollMode.AUTO)


def notify(page, message):
    page.show_dialog(ft.SnackBar(content=ft.Text(message)))
