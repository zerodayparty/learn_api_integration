"""AI 결과를 길이와 템플릿 규칙에 맞게 정리하고 검증한다."""  # 파일의 책임을 설명한다.

import json  # PR 응답의 JSON 객체를 읽는다.
import re  # 섹션 헤더와 불릿을 찾는다.

from ai_gitgen.errors import OutputFormatError  # 사용할 텍스트가 없을 때의 오류를 가져온다.
from ai_gitgen.models import PullRequestDraft  # 검증된 PR 초안 데이터 구조를 가져온다.


def _strip_code_fence(text: str) -> str:  # AI가 실수로 붙인 Markdown 코드 울타리를 제거한다.
    cleaned = text.strip()  # 앞뒤 공백을 먼저 제거한다.
    cleaned = re.sub(r"^```(?:json|text|markdown)?\s*", "", cleaned, flags=re.IGNORECASE)  # 시작 코드 울타리를 제거한다.
    cleaned = re.sub(r"\s*```$", "", cleaned)  # 끝 코드 울타리를 제거한다.
    return cleaned.strip()  # 다시 앞뒤 공백을 정리해 돌려준다.


def _shorten_line(text: str, maximum: int) -> str:  # 한 줄 제목을 지정 길이 안으로 줄인다.
    one_line = " ".join(text.split())  # 줄바꿈과 연속 공백을 한 칸으로 바꾼다.
    
    if len(one_line) <= maximum:  # 이미 최대 길이 안인지 확인한다.
        return one_line  # 손댈 필요 없는 제목을 그대로 돌려준다.
    
    shortened = one_line[:maximum].rstrip()  # 최대 길이까지만 남기고 끝 공백을 없앤다.
    
    return shortened  # 말줄임표를 더해 길이를 넘기지 않고 결과를 돌려준다.



def format_commit_message(raw_text: str) -> str:  # AI 커밋 메시지를 최대 72자 제목 규칙에 맞춘다.
    cleaned = _strip_code_fence(raw_text)  # 불필요한 코드 울타리를 먼저 없앤다.
    
    lines = [line.rstrip() for line in cleaned.splitlines()]  # 각 줄 끝 공백을 제거한다.
    
    while lines and (not lines[0].strip() or re.match(r"(?i)^[-#* ]*commit message\s*:?-*$", lines[0].strip())):  # 빈 줄이나 라벨이 맨 앞에 있는지 확인한다.
        lines.pop(0)  # 실제 제목 앞의 불필요한 줄을 제거한다.
    
    if not lines:  # 정리 후 사용할 텍스트가 남았는지 확인한다.
        raise OutputFormatError("AI가 커밋 메시지 내용을 생성하지 않았습니다.")  # 빈 결과를 사용자에게 알린다.

    # ✅ 🔥🔥🔥🔥🔥 commit message title limit    
    title = _shorten_line(lines[0].lstrip("#*- "), 72)  # 제목 장식을 제거하고 최대 72자로 제한한다.
    
    if not title:  # 장식을 없앤 제목이 비었는지 확인한다.
        raise OutputFormatError("AI가 유효한 커밋 제목을 생성하지 않았습니다.")  # 복사할 수 없는 결과를 막는다.
    
    body_lines = [line for line in lines[1:] if line.strip()]  # 제목 뒤 빈 줄을 제외한 본문만 모은다.
    
    body = "\n".join(body_lines).strip()  # 남은 본문 줄을 다시 합친다.
    
    return f"{title}\n\n{body}" if body else title  # 본문이 있을 때만 빈 줄과 함께 붙인다.


def _extract_json_object(text: str) -> dict[str, object]:  # AI 응답에서 첫 JSON 객체를 찾아 읽는다.
    
    cleaned = _strip_code_fence(text)  # ✅ 🔥🔥🔥🔥🔥 JSON 주변의 markdown 코드 울타리를 제거한다.


    try:  # 응답 전체가 JSON인 일반 경우를 먼저 시도한다.
        value = json.loads(cleaned)  # 문자열을 Python 값으로 바꾼다.
    
    except json.JSONDecodeError:  # JSON 앞뒤에 설명이 붙은 경우를 처리한다.
        start = cleaned.find("{")  # 첫 여는 중괄호 위치를 찾는다.
        end = cleaned.rfind("}")  # 마지막 닫는 중괄호 위치를 찾는다.
    
        if start < 0 or end <= start:  # JSON 객체 모양조차 없는지 확인한다.
            return {}  # 아래의 텍스트 형식 보완 로직을 사용하도록 빈 값을 돌려준다.
    
        try:  # 찾아낸 중괄호 범위만 다시 JSON으로 읽는다.
            value = json.loads(cleaned[start:end + 1])  # 객체처럼 보이는 부분을 Python 값으로 바꾼다.
        except json.JSONDecodeError:  # 중괄호 안도 올바른 JSON이 아닌 경우를 처리한다.
            return {}  # 텍스트 형식 보완 로직을 사용하도록 빈 값을 돌려준다.
    
    return value if isinstance(value, dict) else {}  # 객체일 때만 사용하고 다른 JSON 종류는 버린다.


def _section_bullets(body: str, heading: str, next_heading: str | None) -> list[str]:  # 특정 PR 섹션의 불릿만 꺼낸다.
    end_pattern = rf"(?=^##\s*{re.escape(next_heading)}\s*$|\Z)" if next_heading else r"\Z"  # 다음 헤더 또는 문서 끝을 섹션 경계로 정한다.
    pattern = rf"^##\s*{re.escape(heading)}\s*$\n(.*?){end_pattern}"  # 현재 헤더 아래 본문 범위를 찾는 규칙을 만든다.
    match = re.search(pattern, body, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)  # 대소문자와 여러 줄을 허용해 섹션을 찾는다.
    if not match:  # 요청한 섹션이 없었는지 확인한다.
        return []  # 보완 로직이 작동하도록 빈 목록을 돌려준다.
    bullets = []  # 정리된 불릿을 담을 목록을 만든다.
    
    for line in match.group(1).splitlines():  # 섹션 내용을 한 줄씩 검사한다.
        content = re.sub(r"^\s*[-*+]\s*", "", line).strip()  # 기존 불릿 기호와 주변 공백을 제거한다.
        if content:  # 실제 내용이 있는 줄인지 확인한다.
            bullets.append(f"- {content}")  # 모든 항목을 요구 형식인 하이픈 불릿으로 통일한다.
    
    return bullets  # 정리한 섹션 불릿을 돌려준다.


def _fallback_title_and_body(raw_text: str) -> tuple[str, str]:  # JSON이 아닐 때 일반 텍스트에서 제목과 본문을 찾는다.
    cleaned = _strip_code_fence(raw_text)  # 코드 울타리를 제거한다.
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]  # 비어 있지 않은 줄만 모은다.
    if not lines:  # 사용할 줄이 하나도 없는지 확인한다.
        raise OutputFormatError("AI가 PR 초안 내용을 생성하지 않았습니다.")  # 빈 결과를 사용자에게 알린다.
    title_line = next((line for line in lines if not line.startswith("#")), "변경 사항 정리")  # 헤더가 아닌 첫 줄을 제목 후보로 고른다.
    title = re.sub(r"(?i)^[-* ]*PR\s*Title\s*:\s*", "", title_line).strip()  # PR Title 라벨이 있으면 제거한다.
    return title, cleaned  # 찾은 제목과 전체 본문 후보를 돌려준다.


# AI가 형식을 어겼을 때
def format_pr_draft(raw_text: str) -> PullRequestDraft:  # AI PR 결과를 필수 구조로 정리한다.
    
    parsed = _extract_json_object(raw_text)  # 우선 JSON 객체로 응답을 읽는다.
    
    if parsed:  # JSON 객체를 정상적으로 찾았는지 확인한다.
        title = str(parsed.get("title", "")).strip()  # title 값을 문자열로 꺼낸다.
        body = str(parsed.get("body", "")).strip()  # body 값을 문자열로 꺼낸다.
    
    else:  # JSON이 아닌 응답도 최대한 안전하게 보완한다.
        title, body = _fallback_title_and_body(raw_text)  # 일반 텍스트에서 제목과 본문을 찾는다.
    
    if not title:  # PR 제목이 비어 있는지 확인한다.
        raise OutputFormatError("AI가 PR 제목을 생성하지 않았습니다.")  # 제목 없는 결과를 막는다.
    
    # ✅ 🔥🔥🔥🔥🔥 pr message title limit
    title = _shorten_line(title, 80)  # 줄바꿈을 없애고 최대 80자로 제한한다.
    

    # ✅ 🔥🔥🔥🔥🔥 pr message body / 불릿 처리
    why = _section_bullets(body, "Why", "What")  # Why 섹션 불릿을 읽는다.
    what = _section_bullets(body, "What", "How to Test")  # What 섹션 불릿을 읽는다.
    how = _section_bullets(body, "How to Test", None)  # How to Test 섹션 불릿을 읽는다.
    why = why or ["- Git 변경 사항의 목적을 명확히 설명하기 위해 작성했습니다."]  # 누락된 Why에 안전한 기본 불릿을 넣는다.
    what = what or ["- 수집된 Git 변경 내용을 반영했습니다."]  # 누락된 What에 안전한 기본 불릿을 넣는다.
    how = how or ["- 변경된 기능과 출력 형식을 직접 확인합니다."]  # 누락된 테스트 방법에 안전한 기본 불릿을 넣는다.
    
    
    why_text = "\n".join(why)  # Python 3.10에서도 동작하도록 Why 불릿을 f-string 밖에서 합친다.
    
    what_text = "\n".join(what)  # Python 3.10에서도 동작하도록 What 불릿을 f-string 밖에서 합친다.
    
    how_text = "\n".join(how)  # Python 3.10에서도 동작하도록 How to Test 불릿을 f-string 밖에서 합친다.
    
    normalized = f"## Why\n{why_text}\n\n## What\n{what_text}\n\n## How to Test\n{how_text}"  # 세 섹션을 요구된 순서로 다시 조립한다.
    
    return PullRequestDraft(title=title, body=normalized)  # 검증과 보완을 마친 PR 초안을 돌려준다.



def validate_pr_draft(draft: PullRequestDraft) -> None:  # 최종 PR 초안이 평가 규칙을 만족하는지 다시 확인한다.
    if "\n" in draft.title or len(draft.title) > 80:  # 제목이 한 줄이며 80자 이하인지 검사한다.
        raise OutputFormatError("PR 제목 길이 또는 줄 수 규칙을 만족하지 못했습니다.")  # 잘못된 제목을 출력하지 않는다.
    
    for heading, next_heading in (("Why", "What"), ("What", "How to Test"), ("How to Test", None)):  # 필수 세 섹션을 차례대로 검사한다.
        if not _section_bullets(draft.body, heading, next_heading):  # 현재 섹션에 불릿이 하나라도 있는지 확인한다.
            raise OutputFormatError(f"PR 본문의 {heading} 섹션에 불릿이 없습니다.")  # 빠진 형식을 구체적으로 알린다.
