import asyncio

import flet as ft

from backend.automation import STEPS, JobQueue
from backend.transport import send_experiment
from ui.common import ACCENT, BG, badge, heading, muted, notify, panel, title, view


class AutomationView:
    def __init__(self, page, store, is_visible, sender):
        self.page = page
        self.store = store
        self.is_visible = is_visible
        self.sender = sender
        self.queue = JobQueue()
        self.selection = None
        self.sending = False

    def build(self):
        experiments = {row.id: row for row in self.store.experiments}
        if self.selection not in experiments:
            self.selection = next(iter(experiments), None)

        def select(event):
            self.selection = event.control.value

        def enqueue(_):
            experiment = experiments.get(self.selection)
            if experiment is None:
                return
            try:
                self.queue.enqueue(experiment)
            except ValueError as error:
                notify(self.page, str(error))
            else:
                self.refresh_queue()

        async def start(_):
            job = self.queue.start()
            if job is None:
                return
            self.refresh_queue()
            for _ in STEPS:
                await asyncio.sleep(1)
                self.queue.advance(job)
                self.refresh_queue()

        async def send(_):
            experiment = experiments.get(self.selection)
            if experiment is None or self.sending:
                return
            self.sending = True
            self.refresh_send()
            try:
                message = await send_experiment(self.sender, experiment)
            finally:
                self.sending = False
                self.refresh_send()
            notify(self.page, message)

        self.start_button = ft.FilledButton(
            "다음 작업 실행", icon=ft.Icons.PLAY_ARROW, on_click=start,
            disabled=not can_start(self.queue.jobs),
        )
        self.send_button = ft.OutlinedButton(
            "외부 전송", icon=ft.Icons.SEND, on_click=send,
            disabled=self.sending or not experiments,
        )
        self.jobs_panel = queue_panel(self.queue.jobs, self.remove)
        return automation_layout(
            experiment_picker(experiments, self.selection, select),
            ft.OutlinedButton(
                "대기열에 추가", icon=ft.Icons.ADD, on_click=enqueue, disabled=not experiments,
            ),
            self.start_button,
            self.send_button,
            self.jobs_panel,
        )

    def remove(self, number):
        job = next((job for job in self.queue.jobs if job.number == number), None)
        if job is not None:
            self.queue.remove(job)
            self.refresh_queue()

    def refresh_queue(self):
        if self.is_visible():
            controls = self.jobs_panel.content.controls
            controls[1:] = job_rows(self.queue.jobs, self.remove)
            self.start_button.disabled = not can_start(self.queue.jobs)
            self.page.update(self.jobs_panel, self.start_button)

    def refresh_send(self):
        if self.is_visible():
            self.send_button.disabled = self.sending or self.selection is None
            self.send_button.update()


def job_rows(jobs, remove):
    if not jobs:
        return [muted("아직 대기열에 등록된 작업이 없습니다.")]

    rows = []
    for job in jobs:
        details = [
            title(f"#{job.number:02d}  {job.experiment.name}", 15),
            muted(
                f"데이터셋 {len(job.experiment.datasets)}개 · 모델 {len(job.experiment.models)}개"
                f" · {job.experiment.parameters['--epoch']} 에폭"
            ),
        ]
        if job.status == "실행 중":
            details.extend(
                [
                    muted(STEPS[job.completed_steps]),
                    ft.ProgressBar(value=job.completed_steps / len(STEPS), color=ACCENT),
                ]
            )
        waiting = job.status == "대기 중"
        actions = [badge(job.status, color=ft.Colors.ON_SURFACE_VARIANT, background=BG)
                   if waiting else badge(job.status)]
        if waiting:
            actions.append(
                ft.IconButton(
                    ft.Icons.CLOSE, tooltip="대기열에서 제거",
                    on_click=lambda _, number=job.number: remove(number),
                )
            )
        rows.append(
            ft.Container(
                padding=14,
                bgcolor=BG,
                border_radius=10,
                content=ft.Row([ft.Column(details, expand=True, spacing=4), *actions]),
            )
        )
    return rows


def experiment_picker(experiments, selected, on_select):
    return ft.Dropdown(
        label="저장된 실험",
        value=selected,
        options=[ft.DropdownOption(key=row.id, text=row.name) for row in experiments.values()],
        on_select=on_select,
        expand=True,
    )


def automation_layout(picker, enqueue, start, send, jobs):
    return view(
        heading("02", "학습 자동화", "저장한 실험을 대기열에 추가하고 학습 흐름을 시뮬레이션하세요."),
        panel(
            [
                ft.Row([title("실행 설정"), badge("시뮬레이션")]),
                ft.Row([picker, enqueue, start, send]),
                muted("데이터셋 준비  →  모델 학습  →  검증 및 결과 정리"),
            ]
        ),
        jobs,
    )


def queue_panel(jobs, remove):
    return panel([title("작업 대기열"), *job_rows(jobs, remove)])


def can_start(jobs):
    return any(job.status == "대기 중" for job in jobs) and not any(
        job.status == "실행 중" for job in jobs
    )
