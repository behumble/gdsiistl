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
uv run --locked gdsiistl.py convert example/example.gds example/layerstack.json
```

JSON의 이름과 높이를 적용하여 `example/example.gds_substrate.stl`, `example/example.gds_soi.stl`, `example/example.gds_metal.stl`을 생성합니다.

# 사용법

먼저 GDSII 파일에서 편집용 layerstack 초안을 생성합니다.

```sh
uv run --locked gdsiistl.py draft-layers path/to/file.gds
```

`path/to/file.gds.layerstack.json`이 생성되고 STL은 만들지 않습니다. 도형이 있는 모든 레이어/datatype 쌍을 감지하며, 기존 초안은 덮어쓰지 않습니다. 텍스트 편집기로 JSON을 열어 원하는 출력 이름으로 `name`을 바꾸세요. 기본 `zmin`과 `zmax`는 번호순으로 각 레이어를 GDS 사용자 단위 1만큼 쌓으므로 단순한 3D 시각화에는 수정할 필요가 없습니다. GDSII에는 실제 공정 순서와 두께가 없으므로 물리적 치수가 필요할 때만 z 값을 수정합니다.

그다음 GDS와 JSON을 모두 지정하여 변환합니다.

```sh
uv run --locked gdsiistl.py convert path/to/file.gds path/to/file.gds.layerstack.json
```

포함된 [example/layerstack.json](example/layerstack.json)은 다음과 같습니다.

```json
{
  "1/0": {"zmin": 0, "zmax": 550, "name": "substrate"},
  "3/0": {"zmin": 552, "zmax": 592, "name": "soi"},
  "6/0": {"zmin": 592, "zmax": 593, "name": "metal"}
}
```

키는 GDS의 `레이어/datatype` 쌍이며 이름이나 프로그래밍 데이터형이 아닙니다. 다른 GDS 쌍을 선택할 목적이 아니라면 키를 바꾸지 마세요. GDS에 없는 쌍은 오류로 처리합니다. 높이는 GDS 사용자 단위를 사용하며 JSON에 적힌 쌍만 내보냅니다. 출력된 STL 파일은 [Blender](https://www.blender.org/) 등에서 열어 보고 렌더링할 수 있습니다.

## 참고

GDSII 도형의 다각형 경계를 삼각형으로 분할하는 라이브러리의 제약 때문에, 내보내기 전에 다각형의 경계(즉, 모든 도형)를 약간 이동시킵니다. 이동량은 코드에 약 0.01 단위로 고정되어 있으며, 일반적인 마이크로미터 단위를 기준으로 하면 10나노미터입니다. 또한 아직 완전히 파악되지 않은 다른 관련 제약 또는 버그 때문에 다각형의 구멍을 덮는 삼각형이 추가로 생성될 때가 있습니다. 자세한 내용은 소스 코드의 주석을 참조하세요.

따라서 출력 메시가 완전히 닫혀 있거나, 치수가 정확하거나, 모든 다각형의 구멍을 유지한다고 보장할 수는 없습니다. 다만 오차는 매우 작으며 삼각형이 부족한 쪽보다는 추가되는 쪽으로 나타납니다. Blender 등의 프로그램에서 불필요한 면을 삭제하면 거의 완벽한 시각화 결과를 얻을 수 있습니다.
