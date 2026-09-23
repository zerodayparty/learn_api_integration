# 🟩 AI GitGen  

Git 변경 사항을 읽고 AI API(Application Programming Interface)로 커밋 메시지와 PR(Pull Request) 초안을 만드는 Python CLI(Command Line Interface) 도구다.  

이 도구는 실제 커밋, push, GitHub PR 생성을 수행하지 않는다. 사람이 검토할 텍스트 초안만 터미널에 출력한다.  

<br>

## 🟢 핵심 기능  

- `git status`로 변경 파일을 확인한다.  
- `git diff`로 추적 파일과 새 파일의 변경 내용을 모은다.  
- `commit` 명령으로 72자 이하 커밋 제목과 본문 초안을 생성한다.  
- `pr` 명령으로 80자 이하 제목과 `Why`, `What`, `How to Test` 본문을 생성한다.  
- OpenAI 호환 Chat Completions 형식과 Anthropic Messages 형식을 지원한다.  
- API 파라미터 `model`, `temperature`, `max_tokens`를 실행 옵션으로 바꿀 수 있다.  
- 안전 모드가 기본으로 켜지며 최대 10개 파일, 200줄만 전송한다.  
- `.env`, `_temporary/models.json`, 인증서, 개인 키 파일은 항상 전송에서 제외한다.  
- API는 한 번 실행할 때 정확히 1회만 호출한다.  

<br><br>

## 🟢 요구 환경  

| 항목 | 조건 |  
| --- | --- |
| 운영체제 | macOS, Linux 또는 Windows |  
| Python | 3.10 이상 |  
| Git | 설치 필요 |  
| 실행 위치 | Git 저장소 최상위 폴더 |  

외부 Python 패키지는 필요 없다. Python 표준 라이브러리만 사용한다.  

<br><br>

## 🟢 설치  

### 🟡 방법 1: 설치 없이 실행  

프로젝트 루트에서 바로 실행한다.  

```bash
python3 main.py --help  
```

- `python3`: Python 3 인터프리터를 실행하는 명령  
- `main.py`: CLI 시작 파일  
- `--help`: 사용 가능한 명령과 옵션을 출력하는 선택 사항  

### 🟡 방법 2: 가상환경에 명령 설치  

```bash
python3 -m venv .venv  
source .venv/bin/activate  
python3 -m pip install -e .  
ai-gitgen --help  
```

- `venv`: Virtual Environment의 약자이며 프로젝트 전용 Python 환경을 만든다.  
- `source`: 현재 셸에서 설정 파일을 읽어 가상환경을 활성화한다.  
- `pip`: Pip Installs Packages의 재귀 약자이며 Python 패키지를 설치한다.  
- `-e`: Editable의 약자이며 소스 수정이 설치 결과에 바로 반영되게 한다.  

<br><br>

## 🟢 환경변수 설정  

예시 파일을 복사해 실제 설정 파일을 만든다.

```bash
cp .env.example .env
```

- `cp`: Copy의 약자이며 `.env.example`을 `.env`라는 새 파일로 복사한다.
- `.env.example`: 필요한 변수 이름과 예시만 보여 주며 실행할 때 직접 읽는 파일이 아니다.
- `.env`: 실제 Key, 모델, 요청 형식, 전체 요청 주소를 보관하며 Git에서 제외된다.

`.env`에는 다음 네 값을 사용하는 서비스에 맞게 입력한다.

```dotenv
AI_API_KEY="YOUR_API_KEY"
AI_API_FORMAT="anthropic"
AI_MODEL="YOUR_MODEL_ID"
AI_API_URL="https://example.com/v1/messages"
```

`AI_API_URL`은 반드시 `/v1/messages` 또는 `/v1/chat/completions` 같은 경로까지 포함한 전체 엔드포인트를 적는다. 코드에는 대신 사용할 기본 URL이 없다.

중요 사항:  

- 실제 Key를 `.env.example`, README, 소스 코드, Git 커밋에 적지 않는다.  
- 프로그램은 시작할 때 프로젝트 루트의 `.env`를 먼저 읽는다.
- 이미 `export`로 설정된 환경변수는 `.env`보다 우선하며 자동으로 덮어쓰지 않는다.
- `_temporary/models.json`은 프로그램이 읽지 않으며 Git과 AI 전송 대상에서 제외된다.  

<br><br>

## 🟢 사용 방법  

### 🟡 커밋 메시지 생성  

```bash
python3 main.py commit  
```

옵션을 바꾼 실행 예시다.  

```bash
python3 main.py commit -model "YOUR_MODEL_ID" -temperature 0.1 -max-tokens 400  
```

### 🟡 PR 제목과 본문 생성  

```bash
python3 main.py pr  
```

Anthropic Messages 형식 예시다.  

```bash
python3 main.py pr -api-format anthropic -model "YOUR_MODEL_ID" -temperature 0.2 -max-tokens 700  
```

### 🟡 옵션 설명  

| 옵션 | 기본값 | 의미 |  
| --- | --- | --- |
| `-model`, `--model` | `AI_MODEL` 또는 기본 모델 | 사용할 모델 ID |  
| `-temperature`, `--temperature` | `0.2` | 낮을수록 일정하고 보수적이며 Anthropic 형식은 최대 1.0 |  
| `-max-tokens`, `--max-tokens` | `700` | AI가 생성할 수 있는 최대 토큰 수 |  
| `-api-format`, `--api-format` | `AI_API_FORMAT` 또는 `openai` | 요청·응답 JSON 구조 |  
| `-api-url`, `--api-url` | `AI_API_URL` 필수 | 전체 API 엔드포인트 |
| `-timeout`, `--timeout` | `30` | 최대 네트워크 대기 시간(초) |  
| `-safe-mode`, `--safe-mode` | 켜짐 | 마스킹과 최대 10개 파일·200줄 제한 |  
| `-no-safe-mode`, `--no-safe-mode` | 꺼짐 | 마스킹과 양 제한만 해제 |  

`--no-safe-mode`를 사용해도 보호 파일은 전송되지 않는다.  

<br><br>

## 🟢 파라미터 비교 실습  

비교할 때는 Git 변경 내용을 그대로 유지하고 한 번에 한 옵션만 바꾼다. 두 결과를 파일로 저장하면 눈으로 비교하기 쉽다. 각 명령은 AI API를 1회 호출하므로 아래 temperature 비교는 총 2회 요청한다.  

### 🟡 temperature 0.0과 1.0 비교  

```bash
python3 main.py commit -temperature 0.0 -max-tokens 400 > result_temperature_0.txt  
python3 main.py commit -temperature 1.0 -max-tokens 400 > result_temperature_1.txt  
diff -u result_temperature_0.txt result_temperature_1.txt  
```

- `>`: 터미널 출력을 지정한 파일에 저장한다.  
- `diff`: Difference의 뜻이며 두 파일의 다른 줄을 보여 준다.  
- `-u`: Unified Format의 약자이며 앞뒤 문맥을 포함한 통합 형식으로 차이를 보여 준다.  

| temperature | 예상되는 경향 | 출력 예시의 성격 |  
| --- | --- | --- |
| `0.0` | 표현 선택이 비교적 일정하고 보수적 | 같은 type과 비슷한 단어가 반복될 가능성이 큼 |  
| `0.2` | 기본값이며 일관성과 자연스러움의 균형 | 커밋·PR 초안에 권장 |  
| `0.8` | 표현과 요약 순서가 더 다양해질 수 있음 | 비교 실험용 |  
| `1.0` | Anthropic 형식에서 허용하는 최대값 | 다양성이 커지지만 불필요한 표현도 늘 수 있음 |  

예를 들어 같은 문서 변경도 `0.0`에서는 `docs(cli): add API setup guidance`처럼 직접적인 제목이 나오고, `1.0`에서는 다른 type이나 표현 순서를 선택할 수 있다. 이것은 이해를 위한 예상 예시이며 실제 문장은 모델 상태에 따라 달라진다. temperature가 같아도 결과 문장이 항상 같다고 보장되지는 않는다.  

### 🟡 max_tokens 120과 700 비교  

```bash
python3 main.py pr -temperature 0.2 -max-tokens 120 > result_tokens_120.txt  
python3 main.py pr -temperature 0.2 -max-tokens 700 > result_tokens_700.txt  
diff -u result_tokens_120.txt result_tokens_700.txt  
```

`max_tokens`가 너무 작으면 AI가 PR JSON과 세 섹션을 완성하기 전에 다음처럼 출력이 끊길 수 있다.  

```text
{"title":"docs: 설정 안내 보완","body":"## Why\n- 설정 오류를 줄이기 위해\n\n## What\n- 환경변수 안내를
[출력이 여기서 종료됨]
```

이 경우 `How to Test`가 생성되지 않거나 JSON(JavaScript Object Notation)이 닫히지 않아 원래 내용을 정확히 분리할 수 없다. 후처리가 기본 섹션을 보완하더라도 잘린 의미까지 복원할 수는 없다. 커밋은 약 `300~400`, 세 섹션이 필요한 PR은 약 `600~700`부터 실험하고, 실제 모델 응답 길이에 맞게 조정한다.  

<br><br>

## 🟢 출력 예시  

### 🟡 커밋 메시지  

```text
[INFO] Git status 수집 완료: 3개 파일 변경 감지  
[INFO] Git diff 수집 완료: 120줄  
[INFO] 안전 모드: ON  
[INFO] AI API 요청 중... (이번 실행 1회)  
[DONE] 커밋 메시지 생성 완료  

=== Commit Message ===  
feat(cli): Git 변경 기반 메시지 생성 추가  

- Git 상태와 diff를 AI 프롬프트에 연결  
- API 오류와 출력 형식 검증 추가  
=== End Commit Message ===  
[COPY] 위 구획 안의 텍스트를 복사해 커밋 메시지로 사용하세요.  

[NOTICE] AI 초안은 사실과 민감정보를 검토한 뒤 사용하세요.  
[TIP] 파라미터 비교는 같은 Git 변경에서 temperature 또는 max_tokens만 바꿔 각각 실행하세요.  
```

### 🟡 PR 초안  

```text
=== PR Title ===  
feat: AI 기반 Git 초안 생성 기능 추가  

=== PR Body ===  
## Why  
- 반복되는 커밋과 PR 설명 작성을 줄이기 위해 필요했습니다.  

## What  
- Git 변경 수집과 AI API 호출을 연결했습니다.  

## How to Test  
- python3 -m unittest discover -s tests -v 명령을 실행합니다.  
=== End PR Draft ===  
[COPY] PR Title과 PR Body를 각각 복사한 뒤 실제 변경·테스트·민감정보를 검토하세요.  

[NOTICE] AI 초안은 사실과 민감정보를 검토한 뒤 사용하세요.  
[TIP] 파라미터 비교는 같은 Git 변경에서 temperature 또는 max_tokens만 바꿔 각각 실행하세요.  
```

AI가 만든 내용은 코드와 일치하지 않을 수 있다. 복사하기 전에 파일명, 변경 이유, 테스트 결과, 민감정보 포함 여부를 직접 확인한다.  

<br><br>

## 🟢 프로그램 구조  

| 경로 | 역할 | 분리한 이유 |  
| --- | --- | --- |
| `main.py` | 프로그램 시작 | 실행 진입점을 작게 유지 |  
| `ai_gitgen/cli.py` | 명령과 전체 흐름 연결 | 사용자 입력과 업무 순서를 한곳에서 관리 |  
| `ai_gitgen/git_service.py` | Git 상태와 diff 수집 | Git 실패와 API 실패를 따로 검사 |  
| `ai_gitgen/security.py` | 보호 파일 제외, 마스킹, 줄 제한 | 보안 정책을 독립적으로 테스트 |  
| `ai_gitgen/prompt_builder.py` | commit·PR 프롬프트 작성 | 프롬프트 실험이 통신 코드에 영향을 주지 않게 함 |  
| `ai_gitgen/ai_client.py` | REST API 요청과 응답 처리 | 제공자별 JSON 차이를 한곳에서 처리 |  
| `ai_gitgen/formatter.py` | 제목 길이와 PR 구조 보완 | AI의 형식 실수를 로컬에서 확정적으로 고침 |  
| `tests/` | 자동 테스트 | 실제 과금 요청 없이 실패 조건을 재현 |  
| `_practice/` | 단계별 실습 교재 | 처음부터 따라 하며 원리를 설명할 수 있게 함 |  

전체 흐름은 다음과 같다.  

```text
CLI 옵션 해석  
    ↓  
Git status와 diff 수집  
    ↓  
보호 파일 제외·민감정보 마스킹·전송량 제한  
    ↓  
commit 또는 PR 프롬프트 작성  
    ↓  
AI REST API 1회 호출  
    ↓  
제목 길이와 본문 구조 후처리·재검증  
    ↓  
복사 가능한 터미널 출력  
```

<br><br>

## 🟢 오류 처리  

| 상황 | 동작 |  
| --- | --- |
| Git 저장소가 아님 | 프로젝트 루트에서 실행하라는 오류와 종료 번호 `2` |  
| Git 하위 폴더에서 실행 | 저장소 루트로 이동하라는 오류 |  
| 변경 사항 없음 | API를 호출하지 않고 정상 종료 번호 `0` |  
| API Key 없음 | `cp .env.example .env` 복구 명령과 실제 Key 입력 위치 출력 |  
| 보호 파일만 변경 | 외부 전송 없이 중단 |  
| HTTP 인증·서버 오류 | 상태 코드와 안전하게 정리한 원인 출력 |  
| 네트워크 시간 초과 | 네트워크 오류 원인 출력 |  
| 잘못된 JSON 응답 | 응답 형식 오류 출력 |  
| PR 섹션 누락 | 로컬 후처리로 세 섹션과 불릿을 보완한 뒤 재검증 |  

<br><br>

## 🟢 테스트  

```bash
python3 -m unittest discover -s tests -v  
```

- `-m`: 파일 경로 대신 Python 모듈을 실행한다.  
- `unittest`: Python 기본 Unit Test 모듈이다.  
- `discover`: 정해진 이름의 테스트 파일을 자동으로 찾는다.  
- `-s tests`: Start Directory, 즉 검색 시작 폴더를 `tests`로 지정한다.  
- `-v`: Verbose의 약자이며 각 테스트 이름과 결과를 자세히 보여 준다.  

테스트는 가짜 API 응답만 사용한다. 실제 API Key, 네트워크, 비용이 필요 없다.  

<br><br>

## 🟢 보안과 비용 주의사항  

- 기본 안전 모드는 최대 10개 파일, 200줄만 AI에 보낸다.  
- API Key, Bearer 토큰, 비밀번호, 이메일, 개인 키 모양을 마스킹한다.  
- 정규표현식 마스킹이 모든 민감정보를 100% 찾는 것은 아니다.  
- 파일 이름 자체가 민감하면 AI 실행 전에 Git 변경 목록을 직접 확인한다.  
- 요청 로그나 오류 화면을 공유할 때도 Key가 없는지 다시 확인한다.  
- `temperature`와 `max_tokens`를 필요 이상으로 높이지 않는다.  
- `commit`과 `pr`은 각각 실행할 때마다 API를 1회 호출하므로 반복 실행만큼 비용이 늘어난다.  

<br><br>

## 🟢 Docker 및 Docker Compose 실행 가이드  

프로젝트는 격리된 Linux 컨테이너 환경에서 프로그램을 실행할 수 있도록 `Dockerfile`과 `compose.yaml`을 제공한다.  

### 🟡 컨테이너 환경 정보  

| 항목 | 설정값 | 설명 |  
| :--- | :--- | :--- |
| 기반 운영체제 (OS) | Debian 12 (Bookworm) | Ubuntu가 아닌 Debian 기반의 경량 공식 이미지(`python:3.12-slim`) 사용 |  
| Python 버전 | Python 3.12 | 가상환경 없이 컨테이너 기본 Python 사용 |  
| 추가 설치 도구 | Git | `git status`, `git diff` 수집을 위해 패키지 관리자(`apt-get`)로 설치 |  
| 작업 디렉토리 | `/workspace` | 호스트(내 컴퓨터)의 Git 저장소가 읽기 전용(`:ro`)으로 연결되는 위치 |  
| 보안 원칙 | API Key 이미지 제외 | 이미지를 만들 때 API Key가 포함되지 않으며, 실행 시 환경변수로만 전달 |  

<br><br>

### 🟡 Docker 단독 실행 방법  

#### ⚫️ 1. Docker 이미지 빌드 (Image Build)  
현재 폴더의 `Dockerfile`을 읽어 실행용 이미지를 만든다.  

```bash
docker build -t ai-gitgen:local .  
```

- `docker`: Docker 컨테이너 제어 도구  
- `build`: Dockerfile을 읽어 이미지를 생성하는 하위 명령  
- `-t` (Tag): 생성할 이미지의 이름(`ai-gitgen`)과 태그(`local`) 지정  
- `.`: 현재 폴더를 빌드 컨텍스트(작업 파일 위치)로 전달  

#### ⚫️ 2. Docker 컨테이너 실행 (Container Run)  
호스트의 Git 저장소를 읽기 전용으로 연결하고, 환경변수를 주입하여 실행한다.  

```bash
# 커밋 메시지 생성 실행  
docker run --rm -v "$PWD:/workspace:ro" -e AI_API_KEY -e AI_API_FORMAT -e AI_MODEL -e AI_API_URL ai-gitgen:local commit  

# PR 초안 생성 실행  
docker run --rm -v "$PWD:/workspace:ro" -e AI_API_KEY -e AI_API_FORMAT -e AI_MODEL -e AI_API_URL ai-gitgen:local pr  
```

- `run`: 이미지를 바탕으로 새 컨테이너를 실행  
- `--rm` (Remove): 실행이 끝나면 일회용 컨테이너를 자동 삭제  
- `-v` (Volume): 호스트 폴더(`$PWD`)를 컨테이너 내부(`/workspace`)에 연결  
- `:ro` (Read-Only): 컨테이너가 원본 소스 코드를 임의로 수정하거나 삭제하지 못하도록 읽기 전용으로 잠금  
- `-e` (Environment): 호스트 터미널에 설정된 환경변수를 컨테이너 안으로 안전하게 전달  

<br><br>

### 🟡 Docker Compose 실행 방법  

`compose.yaml` 설정을 사용하면 긴 `docker run` 옵션을 매번 입력하지 않고 간결하게 실행할 수 있다.  

#### ⚫️ 1. Compose 빌드  
```bash
docker compose build  
```

- `compose`: 여러 컨테이너 옵션을 파일로 관리하는 Docker 공식 플러그인  
- `build`: `compose.yaml`에 정의된 `Dockerfile`로 서비스 이미지 빌드  

#### ⚫️ 2. Compose 명령 실행  
호스트 터미널에 `AI_API_KEY` 환경변수가 설정되어 있어야 한다.  

```bash
# 커밋 메시지 생성 실행  
docker compose run --rm ai-gitgen commit  

# PR 초안 생성 실행  
docker compose run --rm ai-gitgen pr  
```

- `compose run`: `compose.yaml`에 등록된 `ai-gitgen` 서비스를 1회성 컨테이너로 실행  
- `commit` / `pr`: 컨테이너 내부 프로그램(`main.py`)에 전달할 작업 명령  

<br><br>

### 🟡 컨테이너 내부 Bash 셸 접속 방법  

컨테이너 내부 파일 구조나 환경(Debian OS, Python 버전 등)을 직접 확인하고 싶을 때 `bash`로 대화형 접속을 할 수 있다.  

`Dockerfile`에 기본 실행 파일(`ENTRYPOINT`)이 지정되어 있으므로 `--entrypoint bash` 옵션을 주어 진입점을 교체하고 `-it` 옵션으로 실행한다.  

```bash
# Docker 명령으로 Bash 접속  
docker run --rm -it --entrypoint bash -v "$PWD:/workspace:ro" ai-gitgen:local  

# Docker Compose 명령으로 Bash 접속  
docker compose run --rm --entrypoint bash ai-gitgen  
```

- `-i` (Interactive): 키보드 표준 입력(stdin) 유지  
- `-t` (Pseudo-TTY): 터미널 화면(프롬프트) 할당  
- `--entrypoint bash`: 기본 실행 프로그램 대신 `bash` 셸 실행  
- 접속 후 `cat /etc/os-release` 명령을 입력하면 Debian 기반임을 눈으로 직접 확인할 수 있으며, 종료 시에는 `exit`를 입력한다.  

자세한 단계별 실습 과정은 `_practice/38_Docker로_마지막_실습.md` 문서를 참고한다.  

<br><br>

## 🟢 현재 범위 밖의 기능  

- `git commit` 자동 실행  
- `git push` 자동 실행  
- GitHub 저장소 생성  
- GitHub PR 자동 생성  
- 실제 AI 응답의 사실 여부 자동 보증  

GitHub 원격 반영은 사용자가 결과를 검토한 뒤 직접 수행한다.  
