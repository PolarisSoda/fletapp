from copy import deepcopy
from dataclasses import dataclass

from backend.experiments import Experiment


STEPS = ("데이터셋 준비", "모델 학습", "검증 및 결과 정리")


@dataclass
class Job:
    number: int
    experiment: Experiment
    completed_steps: int = 0
    status: str = "대기 중"


class JobQueue:
    def __init__(self):
        self.jobs = []
        self.active = None
        self.next_number = 1

    def enqueue(self, experiment):
        if not experiment.datasets or not experiment.models:
            raise ValueError("데이터셋과 모델을 하나 이상 선택해 저장하세요.")
        self.jobs.append(Job(self.next_number, deepcopy(experiment)))
        self.next_number += 1

    def remove(self, job):
        if job.status == "대기 중":
            self.jobs.remove(job)

    def start(self):
        if self.active is not None:
            return None
        job = next((job for job in self.jobs if job.status == "대기 중"), None)
        if job is not None:
            self.active = job
            job.status = "실행 중"
        return job

    def advance(self, job):
        job.completed_steps += 1
        if job.completed_steps == len(STEPS):
            job.status = "완료"
            self.active = None
