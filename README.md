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
