"""Deterministic large-list demo data, computed only when a row is requested."""

ROW_COUNT = 500_000
ROW_HEIGHT = 38
HEADING_HEIGHT = 46
COLUMN_WIDTHS = (110, 150, 160, 170, 120, 100, 100, 140, 110, 160)
COLUMN_LABELS = (
    "실험 번호", "이름", "데이터셋", "모델", "상태",
    "에폭", "배치", "정확도 (%)", "손실", "소요 시간 (초)",
)
NUMERIC_COLUMNS = {0, 5, 6, 7, 8, 9}
DATASETS = ("Oxford Pets", "CIFAR-10", "Flowers-102")


_VALUES = (
    lambda i: i + 1,
    lambda i: f"실험 {i + 1:06d}",
    lambda i: DATASETS[i % len(DATASETS)],
    lambda i: ("ResNet-50", "EfficientNet-B0", "ViT-B/16")[i % 3],
    lambda i: ("완료", "학습 중", "대기", "검증 중")[i % 4],
    lambda i: 10 + i % 191,
    lambda i: (16, 32, 64, 128)[i % 4],
    lambda i: round(80 + (i * 17 % 2000) / 100, 2),
    lambda i: round((i * 13 % 1000) / 1000, 3),
    lambda i: 30 + i * 7 % 3600,
)


def row_values(index: int) -> tuple:
    """A raw ten-value record; no Flet controls or materialized dataset."""
    return tuple(value(index) for value in _VALUES)


def sort_key(column: int):
    # Sorting one column must not generate ten values for every record.
    return _VALUES[column]
