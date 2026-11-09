# Model Workbench

이미지 분류 실험을 구성하는 Windows 데스크톱 앱입니다.

```powershell
uv sync
uv run flet run src/main.py
```

- **학습 실험**에서 새 실험을 만들고 데이터셋과 모델을 카탈로그와 선택 목록 사이에서 끌어 옮길 수 있습니다. 파라미터를 편집한 뒤 **설정 저장**을 누르면 `%LOCALAPPDATA%\ModelWorkbench\experiments.json`에 기록됩니다.
- **학습 자동화**에서 저장된 실험을 대기열에 추가하고 준비, 학습, 검증 단계를 시뮬레이션할 수 있습니다. 작업 내역은 현재 앱 세션에 유지됩니다.
- **결과 확인**은 `src/assets/samples/predictions.csv`를 읽습니다. 행을 선택하면 샘플 이미지가 열리고, **오분류만** 스위치로 불일치 항목을 모아 볼 수 있습니다.

화면은 `src/ui`, 저장과 데이터 처리는 `src/backend`에 있습니다. 테스트는 `uv run pytest`로 실행합니다.

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
