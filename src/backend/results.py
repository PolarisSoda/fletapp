import csv
from dataclasses import dataclass
from pathlib import Path


ASSETS = Path(__file__).resolve().parents[1] / "assets"


@dataclass(frozen=True)
class Prediction:
    filename: str
    image: str
    actual: str
    predicted: str
    confidence: float
    split: str

    @property
    def correct(self):
        return self.actual == self.predicted


def load_predictions():
    with (ASSETS / "samples" / "predictions.csv").open(encoding="utf-8-sig", newline="") as file:
        return [
            Prediction(**{**row, "confidence": float(row["confidence"])})
            for row in csv.DictReader(file)
        ]
