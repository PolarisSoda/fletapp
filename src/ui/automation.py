import asyncio

import flet as ft

from backend.automation import STEPS, JobQueue
from ui.common import ACCENT, BG, TINT, badge, heading, muted, notify, panel, title, view


class AutomationView:
    def __init__(self, page, store, refresh):
        self.page = page
        self.store = store
        self.refresh = refresh
        self.queue = JobQueue()
        self.selection = None

    def build(self):
        experiments = {row.id: row for row in self.store.experiments}
        if self.selection not in experiments:
            self.selection = next(iter(experiments), None)

        def select(event):
            self.selection = event.control.value

        def enqueue(_):
            try:
                self.queue.enqueue(experiments[self.selection])
            except ValueError as error:
                notify(self.page, str(error))
            else:
                self.refresh()

        async def start(_):
            job = self.queue.start()
            if job is None:
                return
            self.refresh()
            self.page.update()
            for _ in STEPS:
                await asyncio.sleep(1)
                self.queue.advance(job)
                self.refresh()
                self.page.update()

        waiting = any(job.status == "대기 중" for job in self.queue.jobs)
        return view(
            heading("02", "학습 자동화", "저장한 실험을 대기열에 추가하고 학습 흐름을 시뮬레이션하세요."),
            panel(
                [
                    ft.Row([title("실행 설정"), badge("시뮬레이션")]),
                    ft.Row(
                        [
                            ft.Dropdown(
                                label="저장된 실험",
                                value=self.selection,
                                options=[
                                    ft.DropdownOption(key=row.id, text=row.name)
                                    for row in experiments.values()
                                ],
                                on_select=select,
                                expand=True,
                            ),
                            ft.OutlinedButton(
                                "대기열에 추가", icon=ft.Icons.ADD, on_click=enqueue,
                                disabled=not experiments,
                            ),
                            ft.FilledButton(
                                "다음 작업 실행", icon=ft.Icons.PLAY_ARROW, on_click=start,
                                disabled=self.queue.active is not None or not waiting,
                            ),
                        ]
                    ),
                    muted("데이터셋 준비  →  모델 학습  →  검증 및 결과 정리"),
                ]
            ),
            panel([title("작업 대기열"), *self.job_rows()]),
        )

    def job_rows(self):
        if not self.queue.jobs:
            return [muted("아직 대기열에 등록된 작업이 없습니다.")]

        def remove(job):
            self.queue.remove(job)
            self.refresh()

        rows = []
        for job in self.queue.jobs:
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
            actions = [badge(job.status, background=TINT if job.status != "대기 중" else BG)]
            if job.status == "대기 중":
                actions.append(
                    ft.IconButton(
                        ft.Icons.CLOSE, tooltip="대기열에서 제거", on_click=lambda _, row=job: remove(row)
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
