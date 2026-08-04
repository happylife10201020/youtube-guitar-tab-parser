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

### exe / app 다시 빌드하기

Windows: `build_windows.bat`을 실행한다. Python 3.8 이상이 필요하다.
빌드가 끝나면 `dist\GuitarTabParser.exe`가 생성된다.

macOS: Mac에서 직접 실행해야 한다. PyInstaller는 다른 OS용 앱을 크로스 빌드하지 못한다.

```sh
chmod +x build_mac.sh
./build_mac.sh
```

빌드가 끝나면 `dist/GuitarTabParser.app`이 생성된다.

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
