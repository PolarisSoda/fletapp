import asyncio
import json
import os
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Protocol
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from backend.experiments import Experiment


class ExperimentSender(Protocol):
    async def send(self, experiment: Experiment) -> None: ...


@dataclass(frozen=True)
class HttpExperimentSender:
    endpoint: str
    timeout: float = 10

    async def send(self, experiment: Experiment) -> None:
        await asyncio.to_thread(self._post, experiment)

    def _post(self, experiment: Experiment) -> None:
        url = urlsplit(self.endpoint)
        if url.scheme not in ("http", "https") or not url.hostname:
            raise ValueError("전송 주소는 HTTP(S) URL이어야 합니다.")
        payload = json.dumps(asdict(experiment), ensure_ascii=False).encode("utf-8")
        request = Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            if not 200 <= response.status < 300:
                raise OSError(f"HTTP {response.status}")


def configured_sender() -> ExperimentSender | None:
    endpoint = os.environ.get("MODEL_WORKBENCH_API_URL", "").strip()
    return HttpExperimentSender(endpoint) if endpoint else None


async def send_experiment(sender: ExperimentSender | None, experiment: Experiment) -> str:
    if sender is None:
        return "전송 주소를 설정하세요 (MODEL_WORKBENCH_API_URL)."
    try:
        await sender.send(deepcopy(experiment))
    except (OSError, ValueError) as error:
        return f"전송 실패 · {error}"
    return "저장된 실험 설정을 전송했습니다."
