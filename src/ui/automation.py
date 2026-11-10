import asyncio
from dataclasses import replace

import flet as ft

from backend.automation import STEPS, JobQueue
from backend.transport import send_experiment
from ui.common import ACCENT, BG, badge, heading, muted, panel, title, view


@ft.observable
class AutomationState:
    def __init__(self):
        self._queue = JobQueue()
        self.jobs = ()
        self.selection = None
        self.sending = False

    def publish_jobs(self):
        self.jobs = tuple(replace(job) for job in self._queue.jobs)

    def enqueue(self, experiment):
        self._queue.enqueue(experiment)
        self.publish_jobs()

    def remove(self, number):
        job = next((job for job in self._queue.jobs if job.number == number), None)
        if job is not None:
            self._queue.remove(job)
            self.publish_jobs()

    def start(self):
        job = self._queue.start()
        if job is not None:
            self.publish_jobs()
        return job

    def advance(self, job):
        self._queue.advance(job)
        self.publish_jobs()


@ft.component
def AutomationScreen(store, state, sender, notice):
    experiments = {row.id: row for row in store.experiments}
    selected = state.selection if state.selection in experiments else next(iter(experiments), None)

    def select(event):
        state.selection = event.control.value

    def current_experiment():
        return experiments.get(state.selection, experiments.get(selected))

    def enqueue(_):
        experiment = current_experiment()
        if experiment is None:
            return
        try:
            state.enqueue(experiment)
        except ValueError as error:
            notice(str(error))

    async def start(_):
        job = state.start()
        if job is not None:
            for _ in STEPS:
                await asyncio.sleep(1)
                state.advance(job)

    async def send(_):
        experiment = current_experiment()
        if experiment is None or state.sending:
            return
        state.sending = True
        try:
            message = await send_experiment(sender, experiment)
        finally:
            state.sending = False
        notice(message)

    return automation_layout(
        experiment_picker(experiments, selected, select),
        ft.OutlinedButton(
            "대기열에 추가", icon=ft.Icons.ADD, on_click=enqueue, disabled=not experiments,
        ),
        ft.FilledButton(
            "다음 작업 실행", icon=ft.Icons.PLAY_ARROW, on_click=start,
            disabled=not can_start(state.jobs),
        ),
        ft.OutlinedButton(
            "외부 전송", icon=ft.Icons.SEND, on_click=send,
            disabled=state.sending or not experiments,
        ),
        queue_panel(state.jobs, state.remove),
    )


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
