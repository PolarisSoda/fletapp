"""Deterministic large-list demo data, computed only when a row is requested."""

ROW_COUNT = 500_000
COLUMN_LABELS = (
    "실험 번호", "이름", "데이터셋", "모델", "상태",
    "에폭", "배치", "정확도 (%)", "손실", "소요 시간 (초)",
)
NUMERIC_COLUMNS = {0, 5, 6, 7, 8, 9}


def row_values(index: int) -> tuple:
    """A raw ten-value record; no Flet controls or materialized dataset."""
    return (
        index + 1,
        f"실험 {index + 1:06d}",
        ("Oxford Pets", "CIFAR-10", "Flowers-102")[index % 3],
        ("ResNet-50", "EfficientNet-B0", "ViT-B/16")[index % 3],
        ("완료", "학습 중", "대기", "검증 중")[index % 4],
        10 + index % 191,
        (16, 32, 64, 128)[index % 4],
        round(80 + (index * 17 % 2000) / 100, 2),
        round((index * 13 % 1000) / 1000, 3),
        30 + index * 7 % 3600,
    )


def sort_key(column: int):
    return lambda index: row_values(index)[column]
