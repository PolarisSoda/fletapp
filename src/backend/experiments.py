import json
import math
import os
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4


ANIMALS = "animals"
PLANTS = "plants"


@dataclass(frozen=True)
class CatalogItem:
    id: str
    name: str
    detail: str
    domain: str | None = None


CATALOG = {
    "datasets": (
        CatalogItem("pets", "Oxford Pets", "37종 · 7,349장", ANIMALS),
        CatalogItem("cifar", "CIFAR-10 · 동물 클래스", "새 · 고양이 · 사슴 외", ANIMALS),
        CatalogItem("flowers", "Flowers 102", "102종 · 8,189장", PLANTS),
        CatalogItem("plant-village", "PlantVillage", "잎 병해 분류 · 샘플", PLANTS),
        CatalogItem("leaf-types", "Leaf Types", "잎 품종 분류 · 샘플", PLANTS),
    ),
    "models": (
        CatalogItem("resnet", "ResNet-18", "CNN · 11.7M"),
        CatalogItem("mobile", "MobileNet V3", "경량 CNN · 5.5M"),
        CatalogItem("vit", "ViT-B/16", "Transformer · 86M"),
    ),
}


@dataclass(frozen=True)
class Parameter:
    flag: str
    label: str
    default: int | float | str | bool
    action: str = "store"
    choices: tuple[str, ...] = ()

    def parse(self, value):
        if self.action == "store_true":
            if isinstance(value, bool):
                return value
        elif self.choices:
            if value in self.choices:
                return value
        else:
            try:
                number = type(self.default)(value)
                if math.isfinite(number) and number > 0:
                    return number
            except (TypeError, ValueError, OverflowError):
                pass
        raise ValueError(f"{self.label} 값을 확인하세요.")


PARAMETERS = (
    Parameter("--epoch", "에폭", 20),
    Parameter("--batch-size", "배치 크기", 32),
    Parameter("--learning-rate", "학습률", 0.001),
    Parameter("--optimizer", "옵티마이저", "adamw", choices=("adamw", "adam", "sgd")),
    Parameter("--device", "디바이스", "cpu", choices=("cpu", "cuda")),
    Parameter("--augment", "데이터 증강", True, action="store_true"),
    Parameter("--mixed-precision", "혼합 정밀도", False, action="store_true"),
)


def defaults():
    return {parameter.flag: parameter.default for parameter in PARAMETERS}


@dataclass
class Experiment:
    id: str
    name: str
    datasets: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    parameters: dict = field(default_factory=defaults)
    domain: str = ANIMALS

    @classmethod
    def from_saved(cls, row):
        # The previous catalog had one plant dataset and no domain field.
        domain = row.get("domain", PLANTS if "flowers" in row.get("datasets", []) else ANIMALS)
        return cls(**{**row, "domain": domain, "parameters": {**defaults(), **row.get("parameters", {})}})


def demo_experiments():
    return [
        Experiment("pets-baseline", "반려동물 분류 베이스라인", ["pets"], ["resnet"]),
        Experiment("cifar-mobile", "경량 모델 성능 비교", ["cifar"], ["mobile", "resnet"]),
        Experiment("flowers-vit", "꽃 품종 전이 학습", ["flowers"], ["vit"], domain=PLANTS),
        Experiment("leaf-disease", "잎 병해 분류", ["plant-village"], ["mobile"], domain=PLANTS),
    ]


class ExperimentStore:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(os.environ.get("LOCALAPPDATA", Path.home())) / (
            "ModelWorkbench/experiments.json"
        )
        self.load_error = None
        try:
            rows = json.loads(self.path.read_text(encoding="utf-8"))
            self.experiments = [Experiment.from_saved(row) for row in rows]
        except FileNotFoundError:
            self.experiments = demo_experiments()
        except (OSError, ValueError, TypeError, AttributeError) as error:
            self.load_error = error
            self.experiments = demo_experiments()

    def save(self, experiment: Experiment):
        if self.load_error is not None:
            raise OSError("기존 실험 파일을 읽을 수 없어 저장할 수 없습니다.")
        saved = deepcopy(experiment)
        saved.parameters = {
            parameter.flag: parameter.parse(saved.parameters[parameter.flag])
            for parameter in PARAMETERS
        }
        rows = list(self.experiments)
        for index, previous in enumerate(rows):
            if previous.id == saved.id:
                rows[index] = saved
                break
        else:
            rows.append(saved)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as file:
                temporary = Path(file.name)
                json.dump([asdict(row) for row in rows], file, ensure_ascii=False, indent=2)
            temporary.replace(self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.experiments = rows
        return deepcopy(saved)

    def create(self, name: str, domain: str = ANIMALS):
        name = name.strip()
        if not name:
            raise ValueError("실험 이름을 입력하세요.")
        if any(row.name.casefold() == name.casefold() for row in self.experiments):
            raise ValueError("이미 사용 중인 실험 이름입니다.")
        return self.save(Experiment(uuid4().hex, name, domain=domain))
