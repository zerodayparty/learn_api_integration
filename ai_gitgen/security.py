"""Git 변경 내용에서 민감정보를 줄이고 전송량을 제한한다."""  # 파일의 책임을 설명한다.

import re  # 민감정보 모양을 찾기 위한 정규표현식 기능을 가져온다.
from pathlib import PurePosixPath  # Git 경로를 운영체제와 무관하게 검사한다.

SAFE_MAX_FILES = 10  # 안전 모드에서 AI로 보낼 최대 파일 수를 정한다.
SAFE_MAX_LINES = 200  # 안전 모드에서 AI로 보낼 최대 diff 줄 수를 정한다.
# ⬆️ 위 수치는 요구사항에 예시로 만들어져 있으며, 필수 사항은 아닌 것으로 보임.
# ### 🟡 보안/민감정보  
# - 보안/민감정보: `git diff`에 포함될 수 있는 민감정보(API Key, 개인정보 등)는 프롬프트에 포함하지 않도록 주의한다.  
# - 아래 중 1개 이상을 `-safe-mode` 같은 옵션으로 제공한다.  
#     - (A) diff에서 특정 패턴(API Key 형태, 이메일 등)을 마스킹 후 전송  
#     - (B) 🔥 diff 일부만 전송(예: 최대 10개 파일, 최대 200줄)  
# - 생성된 커밋/PR 문구는 최종 정답이 아니며, 사용자가 검토 후 적용한다.  



_BLOCKED_NAMES = {  # 내용 자체를 AI로 보내지 않을 파일 이름을 모은다.
    ".env",  # 대표 환경변수 파일을 막는다.
    "agents.md",  # 사용자별 작업 지침과 환경 정보가 담길 수 있는 파일을 막는다.
    "models.json",  # 과제용 API Key와 모델 설정 파일을 막는다.
    "credentials",  # 일반적인 인증정보 파일을 막는다.
    "credentials.json",  # JSON 인증정보 파일을 막는다.
    "secrets.json",  # 비밀값 모음 파일을 막는다.
}  # 차단 파일 이름 모음을 닫는다.


_BLOCKED_SUFFIXES = (  # 비밀키나 인증서에 흔한 확장자를 모은다.
    ".pem",  # PEM(Privacy-Enhanced Mail) 인증서나 키 파일을 막는다.
    ".key",  # 개인 키 파일을 막는다.
    ".p12",  # PKCS(Public-Key Cryptography Standards) 인증서 파일을 막는다.
    ".pfx",  # 개인 인증서 묶음 파일을 막는다.
)  # 차단 확장자 모음을 닫는다.


# 🔥🔥🔥🔥🔥 민감정보 관련 정규표현식
# 이것으로 민감정보를 정말 다 가릴 수 있느냐라고 물으면 할 말이 없음...
_SECRET_PATTERNS = (  # 텍스트 안에서 가릴 민감정보 규칙을 모은다.
    (re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)[^\s,;\"']+"), r"\1[MASKED]"),                     # API Key 할당값을 가린다.
    (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1[MASKED]"),     # Bearer 토큰을 가린다.
    (re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"), "[MASKED_API_KEY]"),                             # sk- 형태의 API Key를 가린다.
    (re.compile(r"\bgh[opusr]_[A-Za-z0-9]{20,}\b"), "[MASKED_GITHUB_TOKEN]"),                   # GitHub 토큰 모양을 가린다.
    (re.compile(r"(?i)(password\s*[=:]\s*)[^\s,;\"']+"), r"\1[MASKED]"),                        # 비밀번호 할당값을 가린다.
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[MASKED_EMAIL]"),          # 이메일 주소를 가린다.
    (re.compile(r"/Users/[^/\s]+"), "/Users/[MASKED_USER]"),                                    # macOS 사용자 홈 경로의 계정 이름을 가린다.
    (re.compile(r"(?i)[A-Z]:\\Users\\[^\\\s]+"), r"C:\\Users\\[MASKED_USER]"),                  # Windows 사용자 홈 경로의 계정 이름을 가린다.
    (re.compile(r"-----BEGIN [^-]+ PRIVATE KEY-----.*?-----END [^-]+ PRIVATE KEY-----", re.DOTALL), "[MASKED_PRIVATE_KEY]"),  # 개인 키 블록 전체를 가린다.
)  # 민감정보 규칙 모음을 닫는다.


def is_protected_path(path: str) -> bool:  # 절대로 전송하지 않을 경로인지 검사한다.
    normalized = path.replace("\\", "/")  # Windows식 구분자도 Git식 구분자로 바꾼다.
    parts = tuple(part.lower() for part in PurePosixPath(normalized).parts)  # 대소문자 차이 없이 경로 조각을 검사한다.
    name = parts[-1] if parts else ""  # 파일 이름이 없을 때도 안전하게 처리한다.
    if name == ".env" or name.startswith(".env."):  # 모든 환경변수 파일 이름을 확인한다.
        return True  # 환경변수 파일이면 전송 대상에서 제외한다.
    if name in _BLOCKED_NAMES:  # 알려진 비밀 설정 파일인지 확인한다.
        return True  # 비밀 설정 파일이면 전송 대상에서 제외한다.
    if name.endswith(_BLOCKED_SUFFIXES):  # 키나 인증서 확장자인지 확인한다.
        return True  # 키나 인증서 파일이면 전송 대상에서 제외한다.
    if "_temporary" in parts:  # 과제의 임시 비밀정보 폴더인지 확인한다.
        return True  # 임시 비밀정보 폴더 아래 파일이면 제외한다.
    if ".agents" in parts or ".codex" in parts:  # 도구별 사용자 설정 폴더인지 확인한다.
        return True  # 사용자 환경이나 지침이 담길 수 있어 전송 대상에서 제외한다.
    return False  # 어떤 차단 규칙에도 해당하지 않으면 전송을 허용한다.


# 🔥🔥🔥🔥🔥 민감정보 관련 함수
def mask_sensitive_text(text: str) -> str:  # 문자열 안의 알려진 민감정보를 마스킹한다.
    masked = text  # 원본을 직접 바꾸지 않도록 새 변수에서 시작한다.
    for pattern, replacement in _SECRET_PATTERNS:  # 모든 민감정보 규칙을 하나씩 적용한다.
        masked = pattern.sub(replacement, masked)  # 찾은 비밀값 부분을 안전한 표시로 바꾼다.
    return masked  # 마스킹을 끝낸 문자열을 돌려준다.


def limit_diff_lines(text: str, max_lines: int = SAFE_MAX_LINES) -> tuple[str, bool]:  # diff를 최대 줄 수로 제한한다.
    lines = text.splitlines()  # 줄 단위로 정확하게 개수를 세기 위해 나눈다.
    if len(lines) <= max_lines:  # 허용 줄 수를 넘지 않았는지 확인한다.
        return text, False  # 원문과 잘리지 않았다는 표시를 돌려준다.
    kept = lines[:max_lines]  # 앞부분의 허용된 줄만 남긴다.
    kept.append(f"... [안전 모드로 {len(lines) - max_lines}줄 생략] ...")  # 생략된 분량을 사용자에게 알린다.
    return "\n".join(kept), True  # 제한된 텍스트와 잘림 표시를 돌려준다.
