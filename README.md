# YouTube Guitar Tab Parser

YouTube 기타 타브(악보) 영상을 받아서, 스크롤되는 화면에서 악보만 뽑아 한 장의 **PDF**로 만들어 줍니다.

---

## 🎸 그냥 쓰고 싶어요 (설치 필요 없음)

파이썬이나 프로그래밍을 몰라도 됩니다. **앱 파일 하나만** 있으면 됩니다.

### Windows

1. **`dist\GuitarTabParser.exe`** 를 받아서 더블클릭합니다.
   - 처음 실행하면 파란 창(“Windows의 PC 보호”)이 뜰 수 있어요. 서명 안 된 개인 프로그램이라 뜨는 정상적인 경고입니다.
     **[추가 정보]** → **[실행]** 을 누르면 됩니다.
2. 창이 뜨면 **YouTube 주소**를 붙여넣습니다.
3. **Generate Tab PDF** 버튼을 누릅니다. (영상 다운로드에 몇 분 걸릴 수 있어요.)
4. 잠시 뒤 사진 한 장이 뜹니다. **마우스로 악보 부분을 네모나게 드래그**한 뒤 **Confirm** 을 누르세요. (어느 방향으로 드래그해도 됩니다.)
5. 끝! 완성된 PDF가 자동으로 열립니다. **exe 파일 옆의 `tabs` 폴더**에 **영상 제목으로 이름 붙은 PDF**(`영상제목 tab.pdf`)로 쌓이고, 영상·프레임 같은 중간 찌꺼기 파일은 자동으로 삭제됩니다. (그 폴더에 이미 있던 파일은 건드리지 않고, 같은 이름이면 `... (2).pdf` 로 추가됩니다.)
   - YouTube 주소는 주소창에서 복사한 것(재생목록 `&list=` 등이 붙어도)이나 “공유 → 링크 복사” 어느 쪽이든 됩니다.

### macOS

1. **[Releases 페이지](https://github.com/happylife10201020/youtube-guitar-tab-parser/releases/latest)** 에서 `GuitarTabParser-mac.zip` 을 받아 압축을 풀고, `GuitarTabParser.app` 을 더블클릭합니다.
   - 처음 실행하면 “확인되지 않은 개발자” 경고가 뜰 수 있어요. **[시스템 설정] → [개인정보 보호 및 보안]** 에서 **“그래도 열기”** 를 눌러주면 됩니다. (또는 앱을 우클릭(혹은 control-클릭) → **열기**.)
2~5. 사용법은 Windows와 동일합니다 (위 참고). PDF는 앱 옆의 `tabs` 폴더에 쌓입니다.

> 만드는 사람은 Python이 필요하지만, **받아서 쓰는 사람은 이 앱 파일 하나면 충분합니다.**

---

## 기능

- YouTube 영상 다운로드 (오디오 없이 영상만 받아 ffmpeg 없이 동작)
- 화면에서 지정한 영역의 타브만 잘라내기
- **중복 줄 제거** — 흰 배경 인쇄 악보, 어두운 영상 위 오버레이 악보, 움직이는 색 하이라이트(“지금 연주 중” 박스)까지 배경에 흔들리지 않고 처리
- **빈 화면 제거** — 인트로/아웃트로, 검게 페이드아웃되는 끝부분 자동 제외
- **겹치는 마디 자동 잘라내기** — 다음 줄 앞부분이 이전 줄 끝을 반복하는 영상에서 중복 마디 제거 (일정한 겹침을 자동 감지, 겹침 없는 영상은 손대지 않음)
- 결과를 A4 PDF로 합치기

---

## 개발자용

### exe / app 다시 빌드하기

**Windows**: `build_windows.bat` 을 더블클릭하면 됩니다. (Python 3.8+ 가 설치되어 있어야 함.)
빌드가 끝나면 `dist\GuitarTabParser.exe` 가 생성됩니다. 이 파일 하나만 공유하면 됩니다.

**macOS**: 반드시 Mac에서 실행해야 합니다 (PyInstaller는 다른 OS용 앱을 크로스 빌드하지 못합니다).

```sh
chmod +x build_mac.sh   # 최초 1회만
./build_mac.sh
```

빌드가 끝나면 `dist/GuitarTabParser.app` 이 생성됩니다. 이 앱 하나만 (압축해서) 공유하면 됩니다.

### 소스로 직접 실행하기 (CLI)

1. **클론**:

    ```sh
    git clone https://github.com/your-username/youtube-guitar-tab-parser.git
    cd youtube-guitar-tab-parser
    ```

2. **가상환경 생성 & 활성화**:

    ```sh
    python -m venv .venv
    ```

    - **Windows** (PowerShell): `.venv\Scripts\Activate.ps1`  또는  (cmd): `.venv\Scripts\activate.bat`
    - **macOS / Linux**: `source .venv/bin/activate`

3. **라이브러리 설치**:

    ```sh
    pip install -r requirements.txt
    ```

4. **실행**:

    ```sh
    python main.py "<youtube_url>" <output_directory>
    ```

    - `<youtube_url>`: 파싱할 YouTube 영상 주소
    - `<output_directory>`: 결과 PDF와 임시 파일이 저장될 폴더
    - 선택 옵션 `--overlap <0~1>`: 줄마다 잘라낼 겹침 비율. 생략하면 자동 감지, `0`이면 잘라내기 끔.

   실행하면 악보 영역을 마우스로 드래그해서 지정하라는 창이 뜹니다. PDF는 지정한 폴더에 저장됩니다.

### GUI를 소스로 실행

```sh
python app.py
```

---

## 라이선스

MIT License. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.
