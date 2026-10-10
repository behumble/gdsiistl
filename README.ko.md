# gdsiistl

[English](README.md) | [한국어](README.ko.md)

GDSII 파일을 STL 파일로 변환합니다.

이 프로젝트는 [dteal/gdsiistl](https://github.com/dteal/gdsiistl)의 포크입니다. 원작자의 작업에 깊은 존경과 감사를 표합니다.

---

GDSII 파일에는 집적 회로나 MEMS 칩을 위한 크고 복잡한 2D 설계가 담겨 있는 경우가 많습니다. 이런 설계를 3D로 시각화하면 유용하지만, 파일 구조가 복잡해 쉽지 않습니다. 이 스크립트는 GDSII 파일에서 선택한 레이어를 3D로 돌출시키고, 외부 프로그램에서 시각화할 수 있도록 레이어별 STL 파일로 출력합니다.

# 빠른 시작

Git을 설치합니다. uv가 없다면 [uv 공식 설치 안내](https://docs.astral.sh/uv/getting-started/installation/)를 참고하세요. 그다음 터미널에서 저장소를 복제하고 의존성을 설치합니다.

```sh
git clone https://github.com/behumble/gdsiistl
cd gdsiistl
uv sync --locked
```

`.python-version` 파일에 Python 3.12가 지정되어 있습니다. 설치되어 있지 않으면 uv가 다운로드할 수 있습니다. `uv sync --locked`는 `uv.lock`에 기록된 버전으로 로컬 `.venv`를 만듭니다.

저장소 디렉터리에서 포함된 예제 파일을 실행합니다.

```sh
uv run --locked gdsiistl.py example/example.gds
```

실행하면 `example/example.gds_substrate.stl`, `example/example.gds_soi.stl`, `example/example.gds_metal.stl`이 생성됩니다.

# 사용법

직접 준비한 GDSII 파일을 변환하려면 `gdsiistl.py` 상단의 `layerstack` 딕셔너리를 해당 파일의 레이어에 맞게 수정합니다. 포함된 예제의 설정은 다음과 같습니다.

```python
layerstack = {
    # GDSII 레이어 번호: (아래쪽 z, 위쪽 z, 출력 이름)
    1: (0, 550, 'substrate'),
    3: (552, 592, 'soi'),
    6: (592, 593, 'metal'),
}
```

레이어 번호를 입력 GDSII 파일에 맞게 바꾸고, 각 레이어의 아래쪽과 위쪽 높이를 파일의 사용자 단위로 지정한 뒤 출력 파일에 사용할 이름을 정하세요. `layerstack`에 적힌 레이어만 내보냅니다.

그다음 저장소 디렉터리에서 아래 명령을 실행합니다. 경로는 실제 GDSII 파일 경로로 바꾸세요.

```sh
uv run --locked gdsiistl.py path/to/file.gds
```

`substrate`라는 이름의 레이어는 입력 파일과 같은 디렉터리에 `path/to/file.gds_substrate.stl`로 저장됩니다. 출력된 STL 파일은 [Blender](https://www.blender.org/) 등에서 열어 보고 렌더링할 수 있습니다.

## 참고

GDSII 도형의 다각형 경계를 삼각형으로 분할하는 라이브러리의 제약 때문에, 내보내기 전에 다각형의 경계(즉, 모든 도형)를 약간 이동시킵니다. 이동량은 코드에 약 0.01 단위로 고정되어 있으며, 일반적인 마이크로미터 단위를 기준으로 하면 10나노미터입니다. 또한 아직 완전히 파악되지 않은 다른 관련 제약 또는 버그 때문에 다각형의 구멍을 덮는 삼각형이 추가로 생성될 때가 있습니다. 자세한 내용은 소스 코드의 주석을 참조하세요.

따라서 출력 메시가 완전히 닫혀 있거나, 치수가 정확하거나, 모든 다각형의 구멍을 유지한다고 보장할 수는 없습니다. 다만 오차는 매우 작으며 삼각형이 부족한 쪽보다는 추가되는 쪽으로 나타납니다. Blender 등의 프로그램에서 불필요한 면을 삭제하면 거의 완벽한 시각화 결과를 얻을 수 있습니다.
