"""사용자 명령을 해석하고 전체 자동화 흐름을 연결한다."""  # 파일의 책임을 설명한다.

import argparse  # commit, pr 명령과 옵션을 해석한다.
import os  # API 설정을 환경변수에서 읽는다.
import sys  # 오류 메시지를 표준 오류로 분리한다.
from pathlib import Path  # 프로젝트 루트의 .env 파일 경로를 안전하게 다룬다.
from urllib.parse import urlparse  # API URL의 프로토콜과 호스트를 정확하게 검사한다.

from ai_gitgen.ai_client import generate_text  # AI API 호출 함수를 가져온다.
from ai_gitgen.errors import AppError, ApiConfigurationError  # 예상 가능한 사용자 오류를 가져온다.
from ai_gitgen.formatter import format_commit_message, format_pr_draft, validate_pr_draft  # 결과 정리와 검증 함수를 가져온다.
from ai_gitgen.git_service import collect_git_context  # Git 변경 수집 함수를 가져온다.
from ai_gitgen.models import ApiSettings  # API 설정 데이터 구조를 가져온다.
from ai_gitgen.prompt_builder import SYSTEM_PROMPT, build_commit_prompt, build_pr_prompt  # 명령별 프롬프트 생성 함수를 가져온다.


def load_dotenv(dotenv_path: str | Path | None = None, override: bool = False) -> None:  # 프로젝트 루트의 .env 값을 환경변수로 등록한다.
    path = Path(dotenv_path) if dotenv_path is not None else Path.cwd() / ".env"  # 별도 경로가 없으면 현재 프로젝트 루트의 .env를 고른다.
    if not path.is_file():  # .env 파일이 실제로 존재하는지 확인한다.
        return  # 파일이 없으면 이후 필수 설정 검사에서 정확한 변수 이름을 안내하게 한다.
    try:  # 파일을 읽지 못하는 운영체제 오류를 설정 오류로 바꾸기 시작한다.
        lines = path.read_text(encoding="utf-8").splitlines()  # UTF-8 텍스트를 줄 단위로 안전하게 읽는다.
    except OSError as error:  # 권한이나 입출력 문제로 파일을 읽지 못한 경우를 잡는다.
        raise ApiConfigurationError(".env 파일을 읽을 수 없습니다. 파일 권한을 확인하세요.") from error  # 비밀값 없이 해결 방법을 알린다.
    for line_number, raw_line in enumerate(lines, start=1):  # 각 줄과 사람이 확인하기 쉬운 줄 번호를 함께 순회한다.
        line = raw_line.strip()  # 줄 앞뒤의 공백을 제거한다.
        if not line or line.startswith("#"):  # 빈 줄 또는 설명 주석인지 확인한다.
            continue  # 환경변수가 아니므로 다음 줄로 이동한다.
        if line.startswith("export "):  # 셸의 export 표기도 허용할지 확인한다.
            line = line.removeprefix("export ").strip()  # export 단어를 제거하고 KEY=VALUE 부분만 남긴다.
        if "=" not in line:  # 변수 이름과 값을 나누는 등호가 없는지 확인한다.
            raise ApiConfigurationError(f".env {line_number}번째 줄 형식이 잘못되었습니다. KEY=VALUE 형식을 사용하세요.")  # 값은 숨기고 잘못된 줄 위치만 알린다.
        key, value = line.split("=", 1)  # 값 안의 등호는 보존하고 첫 번째 등호만 기준으로 나눈다.
        key = key.strip()  # 환경변수 이름 주변의 공백을 제거한다.
        value = value.strip()  # 환경변수 값 주변의 공백을 제거한다.
        if not key.isidentifier():  # Python 환경변수 이름으로 쓰기 어려운 잘못된 이름인지 검사한다.
            raise ApiConfigurationError(f".env {line_number}번째 줄의 환경변수 이름이 잘못되었습니다.")  # 실제 이름과 값은 출력하지 않는다.
        has_double_quotes = value.startswith('"') and value.endswith('"')  # 값이 큰따옴표 한 쌍으로 감싸졌는지 확인한다.
        has_single_quotes = value.startswith("'") and value.endswith("'")  # 값이 작은따옴표 한 쌍으로 감싸졌는지 확인한다.
        if has_double_quotes or has_single_quotes:  # .env.example처럼 따옴표를 사용한 값인지 확인한다.
            value = value[1:-1]  # 환경변수에는 바깥쪽 따옴표를 제외한 실제 값만 저장한다.
        if override or key not in os.environ:  # 명시적 덮어쓰기이거나 기존 환경변수가 없는 경우인지 확인한다.
            os.environ[key] = value  # 비밀값을 출력하지 않고 현재 Python 프로세스에만 등록한다.


def _temperature(value: str) -> float:  # CLI에서 받은 temperature 값을 검사한다.
    number = float(value)  # 문자열을 소수로 바꾼다.
    if not 0.0 <= number <= 2.0:  # 일반적인 API 허용 범위인지 확인한다.
        raise argparse.ArgumentTypeError("temperature는 0.0 이상 2.0 이하여야 합니다.")  # 올바른 범위를 안내한다.
    return number  # 검증된 값을 argparse에 돌려준다.


def _positive_integer(value: str) -> int:  # CLI에서 받은 양의 정수를 검사한다.
    number = int(value)  # 문자열을 정수로 바꾼다.
    if number <= 0:  # 0이나 음수인지 확인한다.
        raise argparse.ArgumentTypeError("0보다 큰 정수를 입력하세요.")  # 허용되는 값의 조건을 안내한다.
    return number  # 검증된 정수를 argparse에 돌려준다.


def _add_common_options(parser: argparse.ArgumentParser) -> None:  # commit과 pr이 공유하는 옵션을 등록한다.
    parser.add_argument("-model", "--model", default=os.getenv("AI_MODEL", "gpt-4o-mini"), help="사용할 AI 모델 ID")  # 환경변수 우선의 모델 옵션을 만든다.
    parser.add_argument("-temperature", "--temperature", type=_temperature, default=0.2, help="결과 다양성 0.0~2.0 (기본값: 0.2)")  # 표현 다양성 옵션을 만든다.
    parser.add_argument("-max-tokens", "--max-tokens", type=_positive_integer, default=700, help="최대 출력 토큰 수 (기본값: 700)")  # 출력 길이 제한 옵션을 만든다.
    parser.add_argument("-api-format", "--api-format", choices=("openai", "anthropic"), default=os.getenv("AI_API_FORMAT", "openai"), help="REST API 요청 형식")  # 제공자별 요청 형식 옵션을 만든다.
    parser.add_argument("-api-url", "--api-url", default=os.getenv("AI_API_URL"), help="AI API 전체 엔드포인트 URL")  # 호환 API 주소 옵션을 만든다.
    parser.add_argument("-timeout", "--timeout", type=float, default=30.0, help="API 최대 대기 시간(초)")  # 네트워크 대기 시간 옵션을 만든다.
    parser.add_argument("-safe-mode", "--safe-mode", dest="safe_mode", action="store_true", default=True, help="마스킹과 전송량 제한 사용 (기본값)")  # 안전 모드를 명시적으로 켜는 옵션을 만든다.
    parser.add_argument("-no-safe-mode", "--no-safe-mode", dest="safe_mode", action="store_false", help="마스킹과 전송량 제한 해제(보호 파일은 계속 제외)")  # 안전 모드 일부를 끄는 옵션을 만든다.


def build_parser() -> argparse.ArgumentParser:  # 전체 CLI 명령 구조를 만든다.
    parser = argparse.ArgumentParser(prog="ai-gitgen", description="Git 변경 사항으로 커밋 메시지와 PR 초안을 생성합니다.")  # 최상위 도움말을 만든다.
    subparsers = parser.add_subparsers(dest="command", required=True)  # commit 또는 pr 중 하나를 필수로 받는다.
    commit_parser = subparsers.add_parser("commit", help="커밋 메시지 초안을 생성합니다.")  # commit 하위 명령을 만든다.
    _add_common_options(commit_parser)  # commit 명령에 공통 API 옵션을 붙인다.
    pr_parser = subparsers.add_parser("pr", help="PR 제목과 본문 초안을 생성합니다.")  # pr 하위 명령을 만든다.
    _add_common_options(pr_parser)  # pr 명령에 공통 API 옵션을 붙인다.
    return parser  # 완성한 명령 해석기를 돌려준다.


def _settings_from_args(args: argparse.Namespace) -> ApiSettings:  # CLI와 환경변수에서 API 설정을 만든다.
    api_key = os.getenv("AI_API_KEY", "").strip()  # 비밀 키는 명령 인자가 아니라 환경변수에서만 읽는다.
    if not api_key:  # 필수 API Key가 비어 있는지 확인한다.
        raise ApiConfigurationError("AI_API_KEY 환경변수가 설정되지 않았습니다.\n[RECOVERY] 프로젝트 루트에서 cp .env.example .env 실행 후 .env에 실제 Key를 입력하세요.")  # 자동 로드되는 .env 생성 방법과 실제 Key 입력 위치를 함께 안내한다.
    api_url = (args.api_url or "").strip()  # .env 또는 명령 옵션으로 받은 전체 요청 주소의 공백을 제거한다.
    if not api_url:  # 임의의 서비스 주소로 대신 요청하지 않도록 필수 URL을 검사한다.
        raise ApiConfigurationError("AI_API_URL 환경변수가 설정되지 않았습니다. .env.example을 복사한 .env에 전체 엔드포인트를 입력하세요.")  # 필요한 파일과 변수 이름을 안내한다.
    parsed_url = urlparse(api_url)  # 문자열을 프로토콜, 호스트, 경로 부분으로 나눈다.
    is_https = parsed_url.scheme == "https" and bool(parsed_url.hostname)  # 호스트가 있는 HTTPS 주소인지 확인한다.
    is_local_http = parsed_url.scheme == "http" and parsed_url.hostname in {"localhost", "127.0.0.1", "::1"}  # 정확한 로컬 호스트만 평문 HTTP 예외로 허용한다.
    if not is_https and not is_local_http:  # 외부 평문 HTTP 또는 잘못된 URL인지 확인한다.
        raise ApiConfigurationError("AI_API_URL은 HTTPS 주소여야 합니다. 로컬 테스트는 localhost만 HTTP를 허용합니다.")  # API Key 평문 전송 위험을 알린다.
    if parsed_url.username or parsed_url.password:  # URL 안에 인증정보가 포함됐는지 확인한다.
        raise ApiConfigurationError("AI_API_URL에 사용자 이름이나 비밀번호를 포함하지 마세요.")  # URL과 로그를 통한 인증정보 노출을 막는다.
    if args.api_format == "anthropic" and args.temperature > 1.0:  # Anthropic Messages 형식의 허용 범위를 확인한다.
        raise ApiConfigurationError("anthropic 형식의 temperature는 0.0 이상 1.0 이하여야 합니다.")  # 제공자 제한에 맞는 값을 안내한다.
    if args.timeout <= 0:  # 시간 제한이 양수인지 확인한다.
        raise ApiConfigurationError("timeout은 0보다 커야 합니다.")  # 잘못된 시간 제한을 사용자에게 알린다.
    return ApiSettings(api_key, api_url, args.api_format, args.model, args.temperature, args.max_tokens, args.timeout)  # 검증된 설정 객체를 돌려준다.


def _print_context_info(context: object, safe_mode: bool) -> None:  # 전송 범위를 비밀값 없이 사용자에게 알린다.
    print(f"[INFO] Git status 수집 완료: {context.total_changed_count}개 파일 변경 감지")  # 전체 변경 파일 수를 보여 준다.
    print(f"[INFO] Git diff 수집 완료: {context.diff_line_count}줄")  # 실제 전송될 diff 줄 수를 보여 준다.
    print(f"[INFO] 안전 모드: {'ON' if safe_mode else 'OFF'}")  # 마스킹과 제한 적용 여부를 보여 준다.
    if context.excluded_files:  # 제외된 파일이 하나라도 있는지 확인한다.
        print(f"[INFO] 보안/제한 정책으로 {len(context.excluded_files)}개 파일 내용을 제외했습니다.")  # 파일명이나 비밀값 없이 제외 개수만 알린다.
    if context.was_truncated:  # 파일 수나 줄 수 제한이 적용됐는지 확인한다.
        print("[INFO] 안전 모드 전송 제한이 적용되었습니다.")  # 일부 내용이 생략됐음을 알린다.


def run(args: argparse.Namespace) -> int:  # 해석된 옵션으로 Git 수집부터 출력까지 실행한다.
    context = collect_git_context(safe_mode=args.safe_mode)  # API 호출 전에 Git 변경 사항을 수집한다.
    if context.total_changed_count == 0:  # Git 변경 사항이 하나도 없는지 확인한다.
        print("[INFO] 변경 사항이 없습니다. 초안을 생성하지 않고 종료합니다.")  # 불필요한 API 비용 없이 종료 이유를 알린다.
        return 0  # 정상 상황이므로 성공 종료 번호를 돌려준다.
    _print_context_info(context, args.safe_mode)  # 수집 결과와 안전 정책을 사용자에게 보여 준다.
    if not context.changed_files:  # 모든 변경 파일이 보안 정책으로 제외됐는지 확인한다.
        raise ApiConfigurationError("AI에 안전하게 전송할 변경 파일이 없습니다. 보호 파일 내용은 전송하지 않습니다.")  # API를 호출하지 않고 안전하게 멈춘다.
    settings = _settings_from_args(args)  # API Key와 요청 옵션을 검증한다.
    prompt = build_commit_prompt(context) if args.command == "commit" else build_pr_prompt(context)  # 명령에 맞는 프롬프트를 만든다.
    print("[INFO] AI API 요청 중... (이번 실행 1회)")  # 실제 외부 요청 직전에 호출 횟수를 알린다.
    raw_result = generate_text(settings, SYSTEM_PROMPT, prompt)  # AI API를 한 번만 호출한다.
    if args.command == "commit":  # 커밋 메시지 명령인지 확인한다.
        result = format_commit_message(raw_result)  # 제목 길이와 불필요한 장식을 후처리한다.
        print("[DONE] 커밋 메시지 생성 완료")  # 성공 상태를 알린다.
        print("\n=== Commit Message ===")  # 최종 결과의 시작 구획을 표시한다.
        print(result)  # 사용자가 복사할 커밋 메시지를 출력한다.
        print("=== End Commit Message ===")  # 최종 결과의 끝 구획을 표시한다.
        print("[COPY] 위 구획 안의 텍스트를 복사해 커밋 메시지로 사용하세요.")  # 복사 가능한 범위를 사용자가 바로 알 수 있게 안내한다.
    else:  # PR 초안 명령을 처리한다.
        draft = format_pr_draft(raw_result)  # PR 제목과 본문을 필수 형식으로 정리한다.
        validate_pr_draft(draft)  # 출력 직전에 규칙을 한 번 더 검증한다.
        print("[DONE] PR 초안 생성 완료")  # 성공 상태를 알린다.
        print("\n=== PR Title ===")  # PR 제목 구획을 표시한다.
        print(draft.title)  # 한 줄 PR 제목을 출력한다.
        print("\n=== PR Body ===")  # PR 본문 구획을 표시한다.
        print(draft.body)  # 세 필수 섹션이 있는 본문을 출력한다.
        print("=== End PR Draft ===")  # 전체 PR 초안의 끝을 표시한다.
        print("[COPY] PR Title과 PR Body를 각각 복사한 뒤 실제 변경·테스트·민감정보를 검토하세요.")  # 복사 대상과 PR 등록 전 검토 항목을 한 줄로 안내한다.
    print("\n[NOTICE] AI 초안은 사실과 민감정보를 검토한 뒤 사용하세요.")  # AI 결과를 바로 적용하지 말아야 함을 알린다.
    print("[TIP] 파라미터 비교는 같은 Git 변경에서 temperature 또는 max_tokens만 바꿔 각각 실행하세요.")  # 공정한 비교를 위해 한 번에 한 조건만 바꾸라고 안내한다.
    return 0  # 전체 흐름이 성공했음을 운영체제에 알린다.


def main(argv: list[str] | None = None) -> int:  # 터미널 실행과 테스트에서 함께 쓸 진입점을 만든다.
    try:  # .env 로드부터 실행 오류까지 긴 traceback 없이 처리하기 시작한다.
        load_dotenv()  # CLI 기본값을 만들기 전에 프로젝트 루트의 .env를 먼저 읽는다.
        parser = build_parser()  # .env가 등록된 뒤 명령과 옵션을 해석할 객체를 만든다.
        args = parser.parse_args(argv)  # 실제 입력 인자를 규칙에 따라 해석한다.
        return run(args)  # 전체 자동화 흐름을 실행하고 종료 번호를 받는다.
    except AppError as error:  # Git, 설정, API, 출력 형식 오류를 한곳에서 잡는다.
        print(f"[ERROR] {error}", file=sys.stderr)  # 오류 메시지를 표준 오류로 출력한다.
        return 2  # 자동화 도구가 실패를 구분할 수 있는 종료 번호를 돌려준다.
