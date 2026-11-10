from copy import deepcopy

import flet as ft

from backend.experiments import ANIMALS, CATALOG, PARAMETERS, PLANTS
from ui.common import ACCENT, BG, LINE, SURFACE, TINT, badge, heading, muted, notify, panel, title, view


TRAINING_SEEDS = {ANIMALS: "#2163B5", PLANTS: "#B82F3D"}


class TrainingView:
    def __init__(self, page, store, apply_theme):
        self.page = page
        self.store = store
        self.apply_theme = apply_theme
        self.domain = ANIMALS
        self.selection = {}
        self.drafts = {}
        self.content = ft.Container(expand=True)
        self._experiment_tiles = {}
        self._bind_details = None

    def build(self):
        self.refresh()
        return self.content

    def refresh(self):
        experiments = [row for row in self.store.experiments if row.domain == self.domain]
        selected = next(
            (row for row in experiments if row.id == self.selection.get(self.domain)),
            experiments[0] if experiments else None,
        )
        rows = [title("실험 목록", 17)]
        self._experiment_tiles = {}
        for experiment in experiments:
            tile = ft.ListTile(
                title=ft.Text(experiment.name, size=13),
                leading=ft.Icon(ft.Icons.SCIENCE_OUTLINED, size=19),
                selected=experiment == selected,
                selected_color=ACCENT,
                selected_tile_color=TINT,
                shape=ft.RoundedRectangleBorder(radius=10),
                on_click=lambda _, item=experiment: self.select(item),
            )
            self._experiment_tiles[experiment.id] = tile
            rows.append(tile)
        if not experiments:
            rows.append(muted("이 분야의 실험이 없습니다."))
        rows.append(ft.OutlinedButton("새 실험", icon=ft.Icons.ADD, on_click=self.create))
        if self.store.load_error is not None:
            rows.append(muted("저장된 실험 파일을 읽을 수 없습니다. 샘플을 표시합니다."))

        controls = [panel(rows, width=210)]
        self._bind_details = None
        if selected is not None:
            draft = self.drafts.setdefault(selected.id, deepcopy(selected))
            name = title(draft.name, 22)
            datasets, bind_datasets = self._build_catalog_section(
                "datasets", "데이터셋", draft.datasets
            )
            models, bind_models = self._build_catalog_section("models", "모델", draft.models)
            parameters, bind_parameters = self.parameters(draft)

            def bind_details(draft):
                name.value = draft.name
                bind_datasets(draft.datasets)
                bind_models(draft.models)
                bind_parameters(draft)

            self._bind_details = bind_details
            controls.extend(
                [
                    ft.Column([name, datasets, models], expand=True, spacing=12),
                    parameters,
                ]
            )
        self.content.content = view(
            ft.Row(
                [
                    ft.Container(
                        content=heading(
                            "01", "학습 실험", "데이터셋과 모델을 조합하고 학습 파라미터를 저장하세요."
                        ),
                        expand=True,
                    ),
                    self.domain_switch(),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(controls, spacing=14, vertical_alignment=ft.CrossAxisAlignment.START),
        )

    def domain_switch(self):
        plant_mode = self.domain == PLANTS

        def change(event):
            self.domain = PLANTS if event.control.value else ANIMALS
            self.apply_theme()
            self.refresh()

        return ft.Row(
            [
                muted("동물 AI") if plant_mode else badge("동물 AI"),
                ft.Switch(
                    key="experiment-domain",
                    value=plant_mode,
                    tooltip="동물 AI와 식물 AI 전환",
                    on_change=change,
                    inactive_track_color=TINT,
                    inactive_thumb_color=ACCENT,
                ),
                badge("식물 AI") if plant_mode else muted("식물 AI"),
            ],
            spacing=8,
        )

    def select(self, experiment):
        self.selection[experiment.domain] = experiment.id
        tile = self._experiment_tiles.get(experiment.id)
        if tile is None or self._bind_details is None:
            self.refresh()
            return
        if tile.selected:
            return
        for item in self._experiment_tiles.values():
            item.selected = item is tile
        self._bind_details(self.drafts.setdefault(experiment.id, deepcopy(experiment)))

    def create(self, _):
        name = ft.TextField(label="실험 이름", autofocus=True, max_length=60, width=340)

        def confirm(_):
            try:
                experiment = self.store.create(name.value or "", self.domain)
            except (ValueError, OSError) as error:
                name.error = str(error)
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
                        field.error = None
                except ValueError as error:
                    if isinstance(field, ft.TextField):
                        field.error = str(error)
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
        def bind(next_draft):
            nonlocal draft
            draft = next_draft
            for flag, field in fields.items():
                value = draft.parameters[flag]
                if isinstance(field, ft.TextField):
                    field.value = str(value)
                    field.error = None
                else:
                    field.value = value

        controls = panel(
            [
                title("학습 파라미터", 17),
                *fields.values(),
                ft.FilledButton("설정 저장", icon=ft.Icons.SAVE_OUTLINED, on_click=save),
            ],
            width=262,
            spacing=10,
        )
        return controls, bind

    def catalog_section(self, kind, label, selected):
        section, _ = self._build_catalog_section(kind, label, selected)
        return section

    def _build_catalog_section(self, kind, label, selected):
        def move(item_id, add):
            if add and item_id not in selected:
                selected.append(item_id)
            elif not add and item_id in selected:
                selected.remove(item_id)
            bind(selected)

        def tile(item, add):
            return ft.Container(
                bgcolor=SURFACE,
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
            cards = {
                item.id: ft.Draggable(
                    group=f"{kind}:{add}",
                    data=item.id,
                    content=tile(item, add),
                    content_feedback=ft.Container(
                        content=badge(item.name), padding=4, bgcolor=SURFACE, border_radius=10
                    ),
                )
                for item in CATALOG[kind]
                if not add or item.domain in (None, self.domain)
            }
            caption = title("", 13)
            hint = muted("여기로 놓아 제거" if add else "여기로 놓아 추가", 11)
            empty = muted("항목 없음", 11)
            column = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
            box = ft.Container(
                bgcolor=BG,
                border=ft.Border.all(1, LINE),
                border_radius=10,
                padding=9,
                height=194,
                content=column,
            )

            def refresh():
                visible = [
                    card for item_id, card in cards.items() if (item_id not in selected) == add
                ]
                caption.value = f"{'카탈로그' if add else '선택됨'} · {len(visible)}"
                column.controls = [caption, hint, *(visible or [empty])]
                box.bgcolor = BG

            def highlight(event):
                box.bgcolor = TINT if event.accept else BG

            def leave(_):
                box.bgcolor = BG

            def accept(event):
                move(event.src.data, not add)

            area = ft.Container(
                expand=True,
                content=ft.DragTarget(
                    group=f"{kind}:{not add}",
                    content=box,
                    on_will_accept=highlight,
                    on_leave=leave,
                    on_accept=accept,
                ),
            )
            return area, refresh

        catalog, refresh_catalog = drop_area(True)
        chosen, refresh_chosen = drop_area(False)

        def bind(next_selected):
            nonlocal selected
            selected = next_selected
            refresh_catalog()
            refresh_chosen()

        bind(selected)
        lists = ft.Row([catalog, chosen], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)
        return panel([title(label, 16), lists], padding=12, spacing=8), bind
