from copy import deepcopy
from dataclasses import dataclass, replace

import flet as ft

from backend.experiments import ANIMALS, CATALOG, PARAMETERS, PLANTS, Experiment
from ui.common import ACCENT, BG, LINE, SURFACE, TINT, badge, heading, muted, panel, title, view


TRAINING_SEEDS = {ANIMALS: "#2163B5", PLANTS: "#B82F3D"}


@ft.observable
@dataclass(eq=False)
class Draft:
    experiment: Experiment

    def move(self, kind, item_id, add):
        ids = getattr(self.experiment, kind)
        if add and item_id not in ids:
            self.experiment = replace(self.experiment, **{kind: [*ids, item_id]})
        elif not add and item_id in ids:
            remaining = ids.copy()
            remaining.remove(item_id)
            self.experiment = replace(self.experiment, **{kind: remaining})

    def set_parameter(self, flag, value):
        self.experiment = replace(
            self.experiment, parameters={**self.experiment.parameters, flag: value}
        )


@ft.observable
class TrainingState:
    def __init__(self):
        self.selection = {}
        self._drafts = {}

    def select(self, experiment):
        self.selection[experiment.domain] = experiment.id

    def draft_for(self, experiment):
        if experiment.id not in self._drafts:
            self._drafts[experiment.id] = Draft(deepcopy(experiment))
        return self._drafts[experiment.id]


@ft.component
def TrainingScreen(store, state, domain, change_domain, notice):
    experiments = [row for row in store.experiments if row.domain == domain]
    selected = next(
        (row for row in experiments if row.id == state.selection.get(domain)),
        experiments[0] if experiments else None,
    )
    rows = [title("실험 목록", 17)]
    for experiment in experiments:
        rows.append(
            ft.ListTile(
                key=experiment.id,
                title=ft.Text(experiment.name, size=13),
                leading=ft.Icon(ft.Icons.SCIENCE_OUTLINED, size=19),
                selected=experiment == selected,
                selected_color=ACCENT,
                selected_tile_color=TINT,
                shape=ft.RoundedRectangleBorder(radius=10),
                on_click=lambda _, item=experiment: state.select(item),
            )
        )
    if not experiments:
        rows.append(muted("이 분야의 실험이 없습니다."))
    rows.append(NewExperimentButton(store, domain, state.select, notice))
    if store.load_error is not None:
        rows.append(muted("저장된 실험 파일을 읽을 수 없습니다. 샘플을 표시합니다."))

    controls = [panel(rows, width=210)]
    if selected is not None:
        draft = state.draft_for(selected)
        controls.extend(
            [
                Catalogs(draft, domain),
                Parameters(store, draft, notice, key=f"parameters:{selected.id}"),
            ]
        )

    return view(
        ft.Row(
            [
                heading(
                    "01", "학습 실험", "데이터셋과 모델을 조합하고 학습 파라미터를 저장하세요.",
                    expand=True,
                ),
                domain_switch(domain, change_domain),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        ft.Row(controls, spacing=14, vertical_alignment=ft.CrossAxisAlignment.START),
    )


def domain_switch(domain, change_domain):
    plant_mode = domain == PLANTS
    return ft.Row(
        [
            muted("동물 AI") if plant_mode else badge("동물 AI"),
            ft.Switch(
                key="experiment-domain",
                value=plant_mode,
                tooltip="동물 AI와 식물 AI 전환",
                on_change=lambda event: change_domain(PLANTS if event.control.value else ANIMALS),
                inactive_track_color=TINT,
                inactive_thumb_color=ACCENT,
            ),
            badge("식물 AI") if plant_mode else muted("식물 AI"),
        ],
        spacing=8,
    )


@ft.component
def NewExperimentButton(store, domain, select, notice):
    opened, set_opened = ft.use_state(False)
    error, set_error = ft.use_state(None)
    name, set_name = ft.use_state("")

    def close(_):
        set_opened(False)

    def open_dialog(_):
        set_error(None)
        set_name("")
        set_opened(True)

    def confirm(value):
        try:
            experiment = store.create(value or "", domain)
        except (ValueError, OSError) as failure:
            set_error(str(failure))
            return
        set_opened(False)
        select(experiment)
        notice("새 실험을 추가했습니다.")

    ft.use_dialog(
        ft.AlertDialog(
            modal=True,
            title=title("새 실험"),
            content=ft.TextField(
                label="실험 이름",
                autofocus=True,
                max_length=60,
                width=340,
                value=name,
                error=error,
                on_change=lambda event: set_name(event.control.value),
                on_submit=lambda event: confirm(event.control.value),
            ),
            actions=[
                ft.TextButton("취소", on_click=close),
                ft.FilledButton("추가", on_click=lambda _: confirm(name)),
            ],
            on_dismiss=close,
        )
        if opened else None
    )
    return ft.OutlinedButton("새 실험", icon=ft.Icons.ADD, on_click=open_dialog)


@ft.component
def Catalogs(draft, domain):
    experiment = draft.experiment
    return ft.Column(
        [
            title(experiment.name, 22),
            catalog_section(draft, domain, "datasets", "데이터셋"),
            catalog_section(draft, domain, "models", "모델"),
        ],
        expand=True,
        spacing=12,
    )


def catalog_section(draft, domain, kind, label):
    experiment = draft.experiment
    selected = getattr(experiment, kind)
    available = tuple(
        item for item in CATALOG[kind]
        if item.id not in selected and item.domain in (None, domain)
    )
    chosen = tuple(item for item in CATALOG[kind] if item.id in selected)
    lists = ft.Row(
        [
            DropArea(draft.move, kind, available, True, key="available"),
            DropArea(draft.move, kind, chosen, False, key="chosen"),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    return panel([title(label, 16), lists], padding=12, spacing=8)


@ft.memo
@ft.component
def DropArea(move_item, kind, items, add):
    hovered, set_hovered = ft.use_state(False)

    def move(item_id, add_item):
        set_hovered(False)
        move_item(kind, item_id, add_item)

    cards = [
        ft.Draggable(
            key=item.id,
            group=f"{kind}:{add}",
            data=item.id,
            content=ft.Container(
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
                            on_click=lambda _, item_id=item.id: move(item_id, add),
                        ),
                    ],
                    spacing=3,
                ),
            ),
            content_feedback=badge(item.name, background=SURFACE),
        )
        for item in items
    ]
    box = ft.Container(
        bgcolor=TINT if hovered else BG,
        border=ft.Border.all(1, LINE),
        border_radius=10,
        padding=9,
        height=194,
        content=ft.Column(
            [
                title(f"{'카탈로그' if add else '선택됨'} · {len(items)}", 13),
                muted("여기로 놓아 제거" if add else "여기로 놓아 추가", 11),
                *(cards or [muted("항목 없음", 11)]),
            ],
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
        ),
    )
    return ft.DragTarget(
        expand=True,
        group=f"{kind}:{not add}",
        content=box,
        on_will_accept=lambda event: set_hovered(event.accept),
        on_leave=lambda _: set_hovered(False),
        on_accept=lambda event: move(event.src.data, not add),
    )


@ft.component
def Parameters(store, draft, notice):
    errors, set_errors = ft.use_state({})

    def save(_):
        experiment = draft.experiment
        failures = {}
        for parameter in PARAMETERS:
            try:
                parameter.parse(experiment.parameters[parameter.flag])
            except ValueError as error:
                failures[parameter.flag] = str(error)
        set_errors(failures)
        if failures:
            notice("파라미터 값을 확인하세요.")
            return
        try:
            store.save(experiment)
        except (ValueError, OSError) as error:
            notice(f"저장 실패 · {error}")
        else:
            notice("실험 설정을 저장했습니다.")

    fields = []
    for parameter in PARAMETERS:
        value = draft.experiment.parameters[parameter.flag]
        label = f"{parameter.label}  {parameter.flag}"

        def changed(event, flag=parameter.flag):
            draft.set_parameter(flag, event.control.value)

        if parameter.action == "store_true":
            field = ft.Checkbox(label=label, value=value, on_change=changed)
        elif parameter.choices:
            field = ft.Dropdown(
                label=label,
                value=value,
                options=[ft.DropdownOption(key=option) for option in parameter.choices],
                on_select=changed,
                dense=True,
            )
        else:
            field = ft.TextField(
                label=label,
                value=str(value),
                dense=True,
                on_change=changed,
                error=errors.get(parameter.flag),
            )
        fields.append(field)
    return panel(
        [
            title("학습 파라미터", 17),
            *fields,
            ft.FilledButton("설정 저장", icon=ft.Icons.SAVE_OUTLINED, on_click=save),
        ],
        width=262,
        spacing=10,
    )
