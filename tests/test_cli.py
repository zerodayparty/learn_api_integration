"""CLI가 각 모듈을 올바른 순서와 횟수로 연결하는지 검사한다."""  # 테스트 파일의 책임을 설명한다.

import contextlib  # 표준 출력과 오류를 문자열로 모은다.
import io  # 출력 캡처용 메모리 문자열 파일을 만든다.
import os  # 테스트 환경변수를 임시로 설정한다.
import tempfile  # 실제 비밀 파일 대신 임시 .env 파일을 만든다.
import unittest  # Python 기본 테스트 도구를 가져온다.
from pathlib import Path  # 임시 .env 파일 경로를 안전하게 다룬다.
from unittest.mock import patch  # Git 수집과 API 호출을 가짜 함수로 바꾼다.

from ai_gitgen.cli import load_dotenv, main  # .env 로더와 실제 CLI 진입점을 가져온다.
from ai_gitgen.models import GitContext  # 테스트용 Git 맥락을 만든다.


def changed_context() -> GitContext:  # 반복 사용할 변경 있음 맥락을 만든다.
    return GitContext("main", ("main.py",), "M  main.py", "diff --git a/main.py b/main.py\n+change", 2, 1, (), False)  # 외부 정보가 없는 작은 가짜 변경을 돌려준다.


def empty_context() -> GitContext:  # 반복 사용할 변경 없음 맥락을 만든다.
    return GitContext("", (), "", "", 0, 0, (), False)  # 모든 변경 값이 빈 맥락을 돌려준다.


class CliTest(unittest.TestCase):  # 전체 CLI 연결 동작 검사를 묶는다.
    def capture(self, arguments: list[str], load_environment: bool = False) -> tuple[int, str, str]:  # CLI 종료 번호와 두 출력을 함께 모은다.
        stdout = io.StringIO()  # 표준 출력을 받을 메모리 파일을 만든다.
        stderr = io.StringIO()  # 표준 오류를 받을 메모리 파일을 만든다.
        dotenv_context = contextlib.nullcontext() if load_environment else patch("ai_gitgen.cli.load_dotenv")  # 일반 테스트가 실제 .env를 읽지 않게 격리한다.
        with dotenv_context, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):  # .env와 터미널 출력을 테스트 범위 안에서만 제어한다.
            code = main(arguments)  # 전달된 CLI 인자로 프로그램을 실행한다.
        return code, stdout.getvalue(), stderr.getvalue()  # 종료 번호와 모은 출력을 돌려준다.

    @patch("ai_gitgen.cli.generate_text")  # 실제 API 호출을 가짜 함수로 바꾼다.
    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_no_changes_skips_api(self, collect: object, generate: object) -> None:  # 변경 없을 때 API를 부르지 않는지 검사한다.
        collect.return_value = empty_context()  # Git 수집 결과를 변경 없음으로 설정한다.
        code, stdout, stderr = self.capture(["commit"])  # commit 명령을 실행하고 출력을 모은다.
        self.assertEqual(code, 0)  # 변경 없음은 정상 종료여야 한다.
        self.assertIn("변경 사항이 없습니다", stdout)  # 사용자가 종료 이유를 확인할 수 있어야 한다.
        self.assertEqual(stderr, "")  # 오류 출력은 없어야 한다.
        generate.assert_not_called()  # 비용이 드는 API는 호출하지 않아야 한다.

    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_missing_api_key_fails(self, collect: object) -> None:  # API Key 누락 오류를 검사한다.
        collect.return_value = changed_context()  # API가 필요한 변경 있음 상태를 만든다.
        with patch.dict(os.environ, {}, clear=True):  # 현재 환경변수를 테스트 동안 모두 비운다.
            code, stdout, stderr = self.capture(["commit"])  # commit 명령을 실행하고 출력을 모은다.
        self.assertEqual(code, 2)  # 설정 오류 종료 번호여야 한다.
        self.assertIn("AI_API_KEY", stderr)  # 필요한 환경변수 이름을 안내해야 한다.
        self.assertIn("cp .env.example .env", stderr)  # 프로젝트 루트에서 설정 파일을 만드는 복구 명령을 안내해야 한다.
        self.assertIn("실제 Key", stderr)  # 복사 후 사용자가 바꿔야 할 값을 분명히 알려야 한다.
        self.assertNotIn("Traceback", stderr)  # 초보자에게 불필요한 내부 traceback은 없어야 한다.
        self.assertIn("Git status 수집 완료", stdout)  # API 전 단계인 Git 수집은 완료됐음을 보여야 한다.

    @patch("ai_gitgen.cli.generate_text")  # 실제 API 호출을 가짜 커밋 응답으로 바꾼다.
    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_commit_calls_api_once(self, collect: object, generate: object) -> None:  # 커밋 생성의 호출 횟수와 출력을 검사한다.
        collect.return_value = changed_context()  # 변경 있음 상태를 만든다.
        generate.return_value = "feat: 자동 생성 추가\n\n- main.py 변경"  # 가짜 AI 커밋 응답을 준비한다.
        with patch.dict(os.environ, {"AI_API_KEY": "fake-key", "AI_API_URL": "https://example.test/v1/messages"}, clear=True):  # 테스트용 가짜 키와 URL만 환경변수에 넣는다.
            code, stdout, stderr = self.capture(["commit", "-temperature", "0.1", "-max-tokens", "400"])  # 옵션을 바꿔 명령을 실행한다.
        self.assertEqual(code, 0)  # 성공 종료여야 한다.
        self.assertEqual(stderr, "")  # 오류 출력은 없어야 한다.
        self.assertIn("=== Commit Message ===", stdout)  # 결과 시작 헤더가 있어야 한다.
        self.assertIn("feat: 자동 생성 추가", stdout)  # AI 커밋 제목이 출력되어야 한다.
        self.assertIn("[COPY] 위 구획 안의 텍스트", stdout)  # 커밋 메시지의 복사 가능 범위를 안내해야 한다.
        self.assertIn("[TIP] 파라미터 비교", stdout)  # 같은 변경에서 옵션을 비교하는 방법을 안내해야 한다.
        self.assertEqual(generate.call_count, 1)  # API는 정확히 한 번만 호출되어야 한다.
        settings = generate.call_args.args[0]  # API 함수에 전달된 설정을 꺼낸다.
        self.assertEqual(settings.temperature, 0.1)  # 바꾼 temperature가 전달되어야 한다.
        self.assertEqual(settings.max_tokens, 400)  # 바꾼 max_tokens가 전달되어야 한다.

    @patch("ai_gitgen.cli.generate_text")  # 실제 API 호출을 가짜 PR 응답으로 바꾼다.
    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_pr_output_has_required_sections(self, collect: object, generate: object) -> None:  # PR 출력의 필수 구조를 검사한다.
        collect.return_value = changed_context()  # 변경 있음 상태를 만든다.
        generate.return_value = '{"title":"feat: PR 생성","body":"## Why\\n- 이유\\n\\n## What\\n- 변경\\n\\n## How to Test\\n- 확인"}'  # 가짜 AI PR JSON을 준비한다.
        with patch.dict(os.environ, {"AI_API_KEY": "fake-key", "AI_API_URL": "https://example.test/v1/messages"}, clear=True):  # 테스트용 가짜 키와 URL만 환경변수에 넣는다.
            code, stdout, stderr = self.capture(["pr"])  # pr 명령을 실행하고 출력을 모은다.
        self.assertEqual(code, 0)  # 성공 종료여야 한다.
        self.assertEqual(stderr, "")  # 오류 출력은 없어야 한다.
        self.assertIn("=== PR Title ===", stdout)  # PR 제목 구획이 있어야 한다.
        self.assertIn("## Why\n- 이유", stdout)  # Why 섹션과 불릿이 있어야 한다.
        self.assertIn("## What\n- 변경", stdout)  # What 섹션과 불릿이 있어야 한다.
        self.assertIn("## How to Test\n- 확인", stdout)  # How to Test 섹션과 불릿이 있어야 한다.
        self.assertIn("PR Title과 PR Body를 각각 복사", stdout)  # PR 제목과 본문의 복사 방법을 안내해야 한다.
        self.assertIn("실제 변경·테스트·민감정보", stdout)  # PR 등록 전 검토할 핵심 항목을 안내해야 한다.
        self.assertEqual(generate.call_count, 1)  # API는 정확히 한 번만 호출되어야 한다.

    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_deceptive_localhost_url_is_rejected(self, collect: object) -> None:  # localhost처럼 보이는 외부 주소를 막는지 검사한다.
        collect.return_value = changed_context()  # API 설정 검사까지 진행할 변경 있음 상태를 만든다.
        with patch.dict(os.environ, {"AI_API_KEY": "fake-key"}, clear=True):  # 테스트용 가짜 Key만 환경변수에 넣는다.
            code, stdout, stderr = self.capture(["commit", "-api-url", "http://localhost.evil.example/v1"])  # 위장 호스트로 실행을 시도한다.
        self.assertEqual(code, 2)  # 안전하지 않은 URL은 오류 종료여야 한다.
        self.assertIn("HTTPS", stderr)  # 사용자가 HTTPS 조건을 확인할 수 있어야 한다.
        self.assertIn("Git status 수집 완료", stdout)  # API 요청 전 Git 수집까지만 진행돼야 한다.

    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_anthropic_temperature_range(self, collect: object) -> None:  # Anthropic temperature 상한을 검사한다.
        collect.return_value = changed_context()  # API 설정 검사까지 진행할 변경 있음 상태를 만든다.
        with patch.dict(os.environ, {"AI_API_KEY": "fake-key"}, clear=True):  # 테스트용 가짜 Key만 환경변수에 넣는다.
            code, stdout, stderr = self.capture(["commit", "-api-format", "anthropic", "-api-url", "https://example.test/v1/messages", "-temperature", "1.5"])  # 허용 범위를 넘는 값으로 실행한다.
        self.assertEqual(code, 2)  # 제공자 설정 오류 종료여야 한다.
        self.assertIn("1.0", stderr)  # Anthropic 상한을 사용자에게 알려야 한다.
        self.assertIn("Git status 수집 완료", stdout)  # API 요청 전 Git 수집까지만 진행돼야 한다.

    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_missing_api_url_fails_without_default(self, collect: object) -> None:  # URL 누락 시 기본 주소를 쓰지 않는지 검사한다.
        collect.return_value = changed_context()  # API 설정 검사까지 진행할 변경 있음 상태를 만든다.
        with patch.dict(os.environ, {"AI_API_KEY": "fake-key"}, clear=True):  # URL 없이 테스트용 가짜 키만 환경변수에 넣는다.
            code, stdout, stderr = self.capture(["commit"])  # 별도 URL 옵션 없이 commit 명령을 실행한다.
        self.assertEqual(code, 2)  # 필수 URL 누락은 설정 오류 종료 번호여야 한다.
        self.assertIn("AI_API_URL", stderr)  # 누락된 환경변수 이름을 정확히 안내해야 한다.
        self.assertNotIn("api.openai.com", stderr)  # 제거한 기본 OpenAI 주소가 오류에도 나타나지 않아야 한다.
        self.assertIn("Git status 수집 완료", stdout)  # 외부 요청 전 Git 수집까지만 진행돼야 한다.

    def test_load_dotenv_parses_file(self) -> None:  # .env 파일 파싱 기능을 검사한다.
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as temp:  # 임시 .env 파일을 만든다.
            temp.write("# 주석 줄입니다\n")  # 주석 줄을 작성한다.
            temp.write("TEST_ENV_VAR=hello_world\n")  # 일반 변수를 작성한다.
            temp.write('QUOTED_VAR="quoted_value"\n')  # 따옴표로 감싸진 값을 작성한다.
            temp.write("EMPTY_VAL=\n")  # 빈 값을 작성한다.
            temp_path = temp.name  # 임시 파일의 경로를 저장한다.
        try:  # 파일 정리 보장을 위해 try 블록을 시작한다.
            with patch.dict(os.environ, {}, clear=True):  # 실제 컴퓨터의 환경변수와 테스트 값을 분리한다.
                load_dotenv(temp_path, override=True)  # 임시 파일의 값을 현재 테스트 프로세스에 등록한다.
                self.assertEqual(os.environ.get("TEST_ENV_VAR"), "hello_world")  # 일반 값이 올바르게 등록됐는지 검사한다.
                self.assertEqual(os.environ.get("QUOTED_VAR"), "quoted_value")  # 따옴표를 제외한 값이 등록됐는지 검사한다.
                self.assertEqual(os.environ.get("EMPTY_VAL"), "")  # 빈 값도 빈 문자열로 등록됐는지 검사한다.
        finally:  # 성공/실패 여부와 관계없이 실행한다.
            Path(temp_path).unlink(missing_ok=True)  # 임시 파일을 삭제한다.

    @patch("ai_gitgen.cli.generate_text")  # 실제 외부 요청을 가짜 응답으로 바꾼다.
    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_main_loads_dotenv_before_building_parser(self, collect: object, generate: object) -> None:  # .env가 CLI 기본값보다 먼저 적용되는지 검사한다.
        collect.return_value = changed_context()  # API 설정 생성까지 진행할 변경 있음 상태를 만든다.
        generate.return_value = "feat: .env 자동 로드"  # 네트워크 없이 성공 흐름을 끝낼 가짜 결과를 준비한다.
        with tempfile.TemporaryDirectory() as temp_directory:  # 테스트가 끝나면 자동 삭제되는 임시 폴더를 만든다.
            dotenv_path = Path(temp_directory) / ".env"  # 임시 프로젝트 루트의 .env 경로를 만든다.
            dotenv_path.write_text("AI_API_KEY=fake-key\nAI_API_FORMAT=anthropic\nAI_MODEL=fake-model\nAI_API_URL=https://example.test/v1/messages\n", encoding="utf-8")  # .env.example과 같은 네 가지 설정을 가짜 값으로 작성한다.
            with patch("ai_gitgen.cli.Path.cwd", return_value=Path(temp_directory)), patch.dict(os.environ, {}, clear=True):  # 로더가 임시 .env만 읽도록 실행 위치와 환경을 격리한다.
                code, stdout, stderr = self.capture(["commit"], load_environment=True)  # 실제 load_dotenv가 포함된 commit 흐름을 실행한다.
        self.assertEqual(code, 0)  # .env 설정만으로 정상 종료해야 한다.
        self.assertEqual(stderr, "")  # 설정 오류가 없어야 한다.
        self.assertIn("커밋 메시지 생성 완료", stdout)  # 가짜 API 응답까지 처리됐는지 확인한다.
        settings = generate.call_args.args[0]  # 가짜 API 함수가 받은 최종 설정을 꺼낸다.
        self.assertEqual(settings.api_url, "https://example.test/v1/messages")  # .env의 URL이 그대로 사용됐는지 확인한다.
        self.assertEqual(settings.api_format, "anthropic")  # .env의 요청 형식이 사용됐는지 확인한다.
        self.assertEqual(settings.model, "fake-model")  # .env의 모델 ID가 사용됐는지 확인한다.


if __name__ == "__main__":  # 이 테스트 파일을 직접 실행했는지 확인한다.
    unittest.main()  # 파일 안의 모든 테스트를 실행한다.
