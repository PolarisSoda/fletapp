from copy import deepcopy

import flet as ft

from backend.experiments import CATALOG, PARAMETERS
from ui.common import ACCENT, BG, LINE, TINT, badge, heading, muted, notify, panel, title, view


class TrainingView:
    def __init__(self, page, store):
        self.page = page
        self.store = store
        self.selected_id = store.experiments[0].id if store.experiments else None
        self.drafts = {}
        self.content = ft.Container(expand=True)

    def build(self):
        self.refresh()
        return self.content

    def refresh(self):
        rows = [title("실험 목록", 17)]
        for experiment in self.store.experiments:
            selected = experiment.id == self.selected_id
            rows.append(
                ft.ListTile(
                    title=ft.Text(experiment.name, size=13),
                    leading=ft.Icon(ft.Icons.SCIENCE_OUTLINED, size=19),
                    selected=selected,
                    selected_color=ACCENT,
                    selected_tile_color=TINT,
                    shape=ft.RoundedRectangleBorder(radius=10),
                    on_click=lambda _, item=experiment: self.select(item),
                )
            )
        rows.append(ft.OutlinedButton("새 실험", icon=ft.Icons.ADD, on_click=self.create))
        if self.store.load_error is not None:
            rows.append(muted("저장된 실험 파일을 읽을 수 없습니다. 샘플을 표시합니다."))

        controls = [panel(rows, width=210)]
        selected = next((row for row in self.store.experiments if row.id == self.selected_id), None)
        if selected is not None:
            draft = self.drafts.setdefault(selected.id, deepcopy(selected))
            controls.extend(
                [
                    ft.Column(
                        [
                            title(draft.name, 22),
                            self.catalog_section("datasets", "데이터셋", draft.datasets),
                            self.catalog_section("models", "모델", draft.models),
                        ],
                        expand=True,
                        spacing=12,
                    ),
                    self.parameters(draft),
                ]
            )
        self.content.content = view(
            heading("01", "학습 실험", "데이터셋과 모델을 조합하고 학습 파라미터를 저장하세요."),
            ft.Row(controls, spacing=14, vertical_alignment=ft.CrossAxisAlignment.START),
        )

    def select(self, experiment):
        self.selected_id = experiment.id
        self.refresh()

    def create(self, _):
        name = ft.TextField(label="실험 이름", autofocus=True, max_length=60, width=340)

        def confirm(_):
            try:
                experiment = self.store.create(name.value or "")
            except (ValueError, OSError) as error:
                name.error_text = str(error)
                return
            self.page.pop_dialog()
            self.select(experiment)
            self.page.update()
            notify(self.page, "새 실험을 추가했습니다.")

        name.on_submit = confirm
        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=title("새 실험"),
                content=name,
                actions=[
                    ft.TextButton("취소", on_click=lambda _: self.page.pop_dialog()),
                    ft.FilledButton("추가", on_click=confirm),
                ],
            )
        )

    def parameters(self, draft):
        fields = {}

        def save(_):
            valid = True
            for parameter in PARAMETERS:
                field = fields[parameter.flag]
                draft.parameters[parameter.flag] = field.value
                try:
                    parameter.parse(field.value)
                    if isinstance(field, ft.TextField):
                        field.error_text = None
                except ValueError as error:
                    if isinstance(field, ft.TextField):
                        field.error_text = str(error)
                    valid = False
            self.page.update()
            if not valid:
                notify(self.page, "파라미터 값을 확인하세요.")
                return
            try:
                self.store.save(draft)
            except (ValueError, OSError) as error:
                notify(self.page, f"저장 실패 · {error}")
            else:
                notify(self.page, "실험 설정을 저장했습니다.")

        for parameter in PARAMETERS:
            value = draft.parameters[parameter.flag]

            def changed(event, flag=parameter.flag):
                draft.parameters[flag] = event.control.value

            if parameter.action == "store_true":
                field = ft.Checkbox(
                    label=f"{parameter.label}  {parameter.flag}", value=value, on_change=changed
                )
            elif parameter.choices:
                field = ft.Dropdown(
                    label=f"{parameter.label}  {parameter.flag}",
                    value=value,
                    options=[ft.DropdownOption(key=option) for option in parameter.choices],
                    on_select=changed,
                    dense=True,
                )
            else:
                field = ft.TextField(
                    label=f"{parameter.label}  {parameter.flag}",
                    value=str(value),
                    dense=True,
                    on_change=changed,
                )
            fields[parameter.flag] = field
        return panel(
            [
                title("학습 파라미터", 17),
                *fields.values(),
                ft.FilledButton("설정 저장", icon=ft.Icons.SAVE_OUTLINED, on_click=save),
            ],
            width=262,
            spacing=10,
        )

    def catalog_section(self, kind, label, selected):
        lists = ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)

        def move(item_id, add):
            if add and item_id not in selected:
                selected.append(item_id)
            elif not add and item_id in selected:
                selected.remove(item_id)
            refresh()

        def tile(item, add):
            return ft.Container(
                bgcolor="white",
                border=ft.Border.all(1, LINE),
                border_radius=8,
                padding=ft.Padding.only(left=7, right=3),
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.DRAG_INDICATOR, size=15, color=ACCENT),
                        ft.Column(
                            [title(item.name, 12), muted(item.detail, 10)], spacing=1, expand=True
                        ),
                        ft.IconButton(
                            ft.Icons.ADD if add else ft.Icons.REMOVE,
                            icon_size=16,
                            width=30,
                            height=36,
                            tooltip="실험에 추가" if add else "실험에서 제거",
                            on_click=lambda _: move(item.id, add),
                        ),
                    ],
                    spacing=3,
                ),
            )

        def drop_area(add):
            items = [item for item in CATALOG[kind] if (item.id in selected) != add]
            cards = [
                ft.Draggable(
                    group=f"{kind}:{add}",
                    data=item.id,
                    content=tile(item, add),
                    content_feedback=ft.Container(
                        content=badge(item.name), padding=4, bgcolor="white", border_radius=10
                    ),
                )
                for item in items
            ]
            box = ft.Container(
                bgcolor=BG,
                border=ft.Border.all(1, LINE),
                border_radius=10,
                padding=9,
                height=194,
                content=ft.Column(
                    [
                        title(f"카탈로그 · {len(items)}" if add else f"선택됨 · {len(items)}", 13),
                        muted("여기로 놓아 제거" if add else "여기로 놓아 추가", 11),
                        *(cards or [muted("항목 없음", 11)]),
                    ],
                    spacing=5,
                ),
            )

            def highlight(event):
                box.bgcolor = TINT if event.accept else BG

            def leave(_):
                box.bgcolor = BG

            def accept(event):
                move(event.src.data, not add)

            return ft.Container(
                expand=True,
                content=ft.DragTarget(
                    group=f"{kind}:{not add}",
                    content=box,
                    on_will_accept=highlight,
                    on_leave=leave,
                    on_accept=accept,
                ),
            )

        def refresh():
            lists.controls = [drop_area(True), drop_area(False)]

        refresh()
        return panel([title(label, 16), lists], padding=12, spacing=8)
