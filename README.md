# Model Workbench

이미지 분류 실험을 구성하는 Windows 데스크톱 앱입니다.

앱과 가상화 확장을 같은 상위 폴더에 클론하세요. 확장 폴더 이름은
`flet-virtual-table`이어야 하며, `pyproject.toml`과 `uv.lock`은 이 상대 경로를 사용합니다.

```powershell
git clone https://github.com/PolarisSoda/flet_datagrid.git flet-virtual-table
git clone https://github.com/PolarisSoda/fletapp.git
cd fletapp
uv sync
uv run flet build web --module-name main --yes
uv run flet serve build/web
```

- **학습 실험**에서 새 실험을 만들고 데이터셋과 모델을 카탈로그와 선택 목록 사이에서 끌어 옮길 수 있습니다. 파라미터를 편집한 뒤 **설정 저장**을 누르면 `%LOCALAPPDATA%\ModelWorkbench\experiments.json`에 기록됩니다.
- **학습 자동화**에서 저장된 실험을 대기열에 추가하고 준비, 학습, 검증 단계를 시뮬레이션할 수 있습니다. 작업 내역은 현재 앱 세션에 유지됩니다.
- **결과 확인**은 `src/assets/samples/predictions.csv`를 읽습니다. 행을 선택하면 샘플 이미지가 열리고, **오분류만** 스위치로 불일치 항목을 모아 볼 수 있습니다.
- **대용량 목록**은 50만 행 × 10열 샘플을 고정 헤더, 가로·세로 스크롤, 열 정렬, 행 선택과 함께 표시합니다. 필요한 범위만 생성·전송하며 재진입 시 선택과 정렬 상태를 유지합니다. 스크롤 위치는 화면 재진입 시 처음으로 돌아갑니다.
- **순수 Flet 목록**은 같은 데이터를 앱 내부 `StickyListView` 컨트롤로 표시합니다. 기본 Flet Canvas와 실제 Flet 클릭·셀 컨트롤을 사용하며, 화면에 보이는 행만 그립니다. 각 목록은 휠 이벤트 한 번에 정확히 한 행씩 이동합니다. 스크롤바 드래그로 전체 범위를 이동할 수 있습니다.
- **ListView 목록**은 실제 `ft.ListView`와 고정 헤더를 사용합니다. `build_controls_on_demand=True`를 적용했고, `prototype` 스위치로 고정 `item_extent`와 prototype 방식을 비교할 수 있습니다. Python에서도 가시 행만 생성하여 전체 50만 개의 컨트롤을 만들지 않습니다.
- 순수 Flet 및 ListView 탭의 **복합 셀**을 켜면 실제 `Row`, `Column`, 아이콘과 실행 버튼이 나타납니다. 버튼 실행과 행 선택은 독립적으로 동작합니다. 순수 Flet 클릭은 그려진 좌표 추정 대신 행 ID에 연결된 실제 컨트롤로 처리합니다.
- **순수 Flet 목록**과 **ListView 목록**의 데이터셋 필터에서 전체, CIFAR-10, Oxford Pets, Flowers-102를 선택할 수 있습니다. 조건에 맞는 행의 인덱스만 추리고 화면에 보이는 행만 다시 표시합니다. 기존 정렬은 유지하며, 필터 변경 시 맨 위로 이동하고 행 선택을 초기화합니다. 필터와 위치는 화면을 오가도 유지됩니다.

대용량 목록은 로컬 `flet-virtual-table` 확장을 사용하므로 기본 `flet run` 클라이언트 대신 확장을 포함한 빌드가 필요합니다.

```powershell
uv run flet build windows --module-name main --yes
# 또는 웹 빌드 후 로컬 확인
uv run flet build web --module-name main --yes
uv run flet serve build/web
```

순수 Flet 컨트롤만 기본 클라이언트에서 실행하려면 `uv run flet run src/pure_list_demo.py --web`을 사용하세요. 이 진입점은 로컬 가상화 확장을 가져오지 않습니다. 세 구현의 차이와 비교 조건은 [VIRTUAL_TABLE.md](VIRTUAL_TABLE.md)에 설명되어 있습니다.
ListView 버전만 실행하려면 `uv run flet run src/listview_demo.py --web`을 사용하세요.

화면은 `src/ui`, 저장과 데이터 처리는 `src/backend`에 있습니다. 테스트는 `uv run pytest`로 실행합니다.

## 순수 Flet Canvas 목록: 위치와 사용법

사이드바의 **순수 Flet 목록**은 `ft.ListView`가 아니라 Canvas로 표를 그리는
앱 내부 컨트롤입니다. 별도 Flutter 확장 없이 기본 Flet API만 사용합니다.

| 파일 | 역할 |
| --- | --- |
| [src/controls/sticky_list.py](src/controls/sticky_list.py) | `StickyListView`: Canvas 표, 고정 헤더, 클릭 처리, 오른쪽 고정 세로 스크롤바 |
| [src/backend/list_window.py](src/backend/list_window.py) | `ListWindow`: 표시 범위, 정렬, 필터, 선택 상태, 행 데이터 캐시 |
| [src/ui/pure_list.py](src/ui/pure_list.py) | 50만 행 데모 화면, 데이터셋 필터와 복합 셀 예제 |
| [src/pure_list_demo.py](src/pure_list_demo.py) | Canvas 목록만 실행하는 진입점 |

프로젝트 루트에서 데모를 실행합니다. `--web`을 빼면 데스크톱으로 실행합니다.

```powershell
uv run flet run src/pure_list_demo.py --web
```

### 내 데이터로 사용하기

아래 코드를 `src/canvas_example.py`로 저장하고
`uv run flet run src/canvas_example.py --web`으로 실행할 수 있습니다.

```python
import flet as ft

from backend.list_window import ListWindow
from controls.sticky_list import StickyListView


records = [
    {"id": 1, "name": "실험 A", "dataset": "CIFAR-10"},
    {"id": 2, "name": "실험 B", "dataset": "Oxford Pets"},
    {"id": 3, "name": "실험 C", "dataset": "CIFAR-10"},
]


def row_builder(record):
    # 열 순서와 같은 개수의 원시 값을 반환합니다.
    return record["id"], record["name"], record["dataset"]


def main(page: ft.Page):
    model = ListWindow(
        records, row_builder,
        sort_keys={
            0: lambda record: record["id"],
            1: lambda record: record["name"],
            2: lambda record: record["dataset"],
        },
    )
    grid = StickyListView(
        columns=["번호", "이름", "데이터셋"],
        records=records, row_builder=row_builder, model=model,
        column_widths=[100, 220, 180], numeric_columns={0},
        row_height=38, heading_height=46, expand=True,
    )

    async def filter_dataset(event):
        value = event.control.value
        predicate = None if value == "all" else lambda record: record["dataset"] == value
        await model.set_filter(predicate)
        grid.refresh()

    page.add(ft.Column([
        ft.Dropdown(
            label="데이터셋", value="all", width=220,
            options=[
                ft.DropdownOption(key="all", text="전체 데이터셋"),
                ft.DropdownOption(key="CIFAR-10"),
                ft.DropdownOption(key="Oxford Pets"),
            ],
            on_select=filter_dataset,
        ),
        grid,
    ], expand=True))


if __name__ == "__main__":
    ft.run(main)
```

헤더를 클릭하면 해당 열로 정렬하고, 행 왼쪽 체크 영역을 클릭하면 선택합니다.
`model.selected_count`와 `model.selected(row_id)`로 선택 상태를 읽습니다.
`row_id`는 정렬·필터 후의 화면 순번이 아니라 원본 `records`의 0부터 시작하는 인덱스입니다.
필터는 `await model.set_filter(predicate)`로 적용하고, `await model.set_filter()`로 해제한 뒤
`grid.refresh()`를 호출합니다. 필터 변경 시 선택과 스크롤 위치를 초기화하고 기존 정렬은 유지합니다.

`records`에는 길이를 알 수 있고 인덱스로 접근할 수 있는 리스트나 `range` 등을 전달합니다.
`row_builder`는 보이는 행에 필요한 값만 반환하며, 최근 256개 행의 값이 캐시됩니다.
정렬·필터는 전체 데이터에서 표시할 인덱스를 계산하지만 Canvas는 보이는 행만 다시 그립니다.
큰 데이터는 위 예제처럼 열별 `sort_keys`를 제공하면 정렬 중 전체 열 값을 생성하는 비용을 줄입니다.

기본 셀은 그려진 텍스트입니다. 실제 버튼이나 `Row`가 필요하면
`cell_builder(record, row_id, column_index)`를 전달하고, 해당 셀에 넣을 Flet 컨트롤을
반환합니다. `None`을 반환한 셀은 기본 텍스트로 표시합니다. 셀 위치와 크기는 컨트롤이 계산하며,
행 높이는 고정입니다. 화면 밖으로 나간 셀 컨트롤은 버려지므로 입력값은 별도 데이터 모델에 보관하세요.
이 예제는 명령형 API이며, 선언형 UI에서의 상태 연결은 같은 [pure_list.py](src/ui/pure_list.py)의
`PureListState`와 `PureListScreen`을 참고하세요.

## 외부 전송

학습 자동화에서 저장된 실험을 고르고 **외부 전송**을 누르면 설정 전체를 JSON으로 POST합니다. 앱을 실행하기 전에 받을 API 주소를 지정하세요.

```powershell
$env:MODEL_WORKBENCH_API_URL = "https://your-server.example/api/experiments"
uv run flet run src/main.py
```

다른 API나 FTP를 연결하려면 `src/backend/transport.py`의 `ExperimentSender` 인터페이스에 맞춰 `async send(experiment)`를 구현하고, `main(page, sender=...)`으로 전달하면 됩니다.


## Run the app

### uv

Run as a desktop app:

```bash
uv run flet run
```

Run as a web app:

```bash
uv run flet run --web
```

For more details on running the app, refer to the [Getting Started Guide](https://flet.dev/docs/).

## Build the app

### Android

```bash
flet build apk -v
```

For more details on building and signing `.apk` or `.aab`, refer to the [Android Packaging Guide](https://flet.dev/docs/publish/android/).

### iOS

```bash
flet build ipa -v
```

For more details on building and signing `.ipa`, refer to the [iOS Packaging Guide](https://flet.dev/docs/publish/ios/).

### macOS

```bash
flet build macos -v
```

For more details on building macOS package, refer to the [macOS Packaging Guide](https://flet.dev/docs/publish/macos/).

### Linux

```bash
flet build linux -v
```

For more details on building Linux package, refer to the [Linux Packaging Guide](https://flet.dev/docs/publish/linux/).

### Windows

```bash
flet build windows -v
```

For more details on building Windows package, refer to the [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).

### Web

```bash
flet build web -v
```

For more details on building Web app, refer to the [Web Packaging Guide](https://flet.dev/docs/publish/web/).
