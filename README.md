# YouTube Guitar Tab Parser

YouTube 기타 타브 영상에서 악보 부분만 잘라내어 한 장의 PDF로 만든다.

---

## 시작하기

프로그래밍 지식이 필요 없다. 앱 파일 하나만 있으면 된다.

### Windows

1. [Releases 페이지](https://github.com/happylife10201020/youtube-guitar-tab-parser/releases/latest)에서 `GuitarTabParser-windows.zip`을 내려받아 압축을 푼다.
2. `GuitarTabParser.exe`를 실행한다. "Windows의 PC 보호" 창이 뜨면 추가 정보 → 실행을 누른다.
3. YouTube 주소를 입력하고 Generate Tab PDF를 누른다.
4. 화면에 뜬 이미지에서 악보 영역을 드래그로 지정하고 Confirm을 누른다.
5. PDF가 자동으로 열린다. 결과물은 exe 옆 `tabs` 폴더에 영상 제목으로 저장된다.

### macOS

1. [Releases 페이지](https://github.com/happylife10201020/youtube-guitar-tab-parser/releases/latest)에서 `GuitarTabParser-mac.zip`을 내려받아 압축을 푼다.
2. `GuitarTabParser.app`을 실행한다. "확인되지 않은 개발자" 경고가 뜨면 앱을 control-클릭 후 열기를 선택한다.
3. 이후 사용법은 Windows와 같다.

### 화면 예시

앱을 실행하면 다음과 같은 순서로 진행된다.

| 1. 대기 화면 | 2. 다운로드 중 |
|---|---|
| ![대기 화면](assets/screenshots/01-ready.png) | ![다운로드 중](assets/screenshots/02-downloading.png) |

| 3. 악보 영역 지정 | 4. 완료 |
|---|---|
| ![악보 영역 지정](assets/screenshots/03-select-region.png) | ![완료](assets/screenshots/04-done.png) |

---

## 기능

- YouTube 영상 다운로드
- 지정한 영역만 잘라내기
- 중복 줄 제거
- 빈 화면 제거
- 겹치는 마디 자동 제거
- A4 PDF로 합치기

---

## 개발자용

### 버전 규칙 (SemVer)

버전은 `MAJOR.MINOR.PATCH` 형식이고 [version.py](version.py)가 단일 기준이다.

- **MAJOR**: 사용법이 달라지는 큰 변경
- **MINOR**: 새 기능 추가
- **PATCH**: 버그 수정, 내부 개선

릴리즈 절차: 변경 커밋에서 `version.py`를 올리고, 같은 버전의 태그 `v<버전>`(예: `v1.2.0`)을 푸시한다. 태그와 `version.py`가 다르면 CI가 빌드를 거부한다.

### 자동 빌드 (GitHub Actions)

- `main`에 푸시 → **개발 빌드** (`GuitarTabParserDev`, 상세 로그 창 있음) 가 워크플로 아티팩트로 올라간다.
- `v*` 태그 푸시 → **릴리즈 빌드** (`GuitarTabParser`, 상세 로그 창 없음 — 로그는 사용자 데이터 폴더의 `last-run.log`에 기록) 가 macOS/Windows 모두 빌드되어 해당 태그의 GitHub Release에 자동 첨부된다.

### yt-dlp 자동 업데이트

yt-dlp는 앱에 굳혀 넣지 않는다. 빌드에 wheel 파일로만 동봉되고, 첫 실행 때 사용자 데이터 폴더(macOS: `~/Library/Application Support/GuitarTabParser`, Windows: `%LOCALAPPDATA%\GuitarTabParser`)에 풀린 뒤 거기서 로드된다. 실행할 때마다 백그라운드에서 PyPI 최신 버전을 확인해 받아 두고, 다음 실행부터 적용된다. YouTube가 방식을 바꿔도 앱 재배포 없이 따라간다.

### exe / app 손으로 빌드하기

Windows (Python 3.8+):

```bat
build_windows.bat            :: 개발 빌드 -> dist\GuitarTabParserDev.exe
set RELEASE=1 && build_windows.bat   :: 릴리즈 빌드 -> dist\GuitarTabParser.exe
```

macOS (Mac에서만 가능 — PyInstaller는 크로스 빌드를 못 한다):

```sh
chmod +x build_mac.sh
./build_mac.sh               # 개발 빌드 -> dist/GuitarTabParserDev.app
RELEASE=1 ./build_mac.sh     # 릴리즈 빌드 -> dist/GuitarTabParser.app
```

### 소스로 직접 실행하기 (CLI)

1. 클론한다.

    ```sh
    git clone https://github.com/happylife10201020/youtube-guitar-tab-parser.git
    cd youtube-guitar-tab-parser
    ```

2. 가상환경을 만들고 활성화한다.

    ```sh
    python -m venv .venv
    ```

    Windows PowerShell: `.venv\Scripts\Activate.ps1`
    Windows cmd: `.venv\Scripts\activate.bat`
    macOS/Linux: `source .venv/bin/activate`

3. 라이브러리를 설치한다.

    ```sh
    pip install -r requirements.txt
    ```

4. 실행한다.

    ```sh
    python main.py "<youtube_url>" <output_directory>
    ```

    `<youtube_url>`: 파싱할 YouTube 영상 주소
    `<output_directory>`: 결과 PDF와 임시 파일이 저장될 폴더
    `--overlap <0~1>`: 줄마다 잘라낼 겹침 비율. 생략하면 자동 감지하고, 0이면 잘라내기를 끈다.

   실행하면 악보 영역을 드래그로 지정하는 창이 뜬다.

### GUI를 소스로 실행

```sh
python app.py
```

---

## 라이선스

MIT License. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고한다.
