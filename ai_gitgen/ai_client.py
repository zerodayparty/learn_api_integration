"""외부 AI REST API 요청과 응답 처리를 담당한다."""  # 파일의 책임을 설명한다.

import json  # Python 값과 JSON 요청·응답을 서로 바꾼다.
import socket  # 네트워크 시간 초과 오류를 구분한다.
import urllib.error  # HTTP와 URL 요청 오류 종류를 사용한다.
import urllib.request  # 외부 패키지 없이 HTTPS 요청을 보낸다.

from ai_gitgen.errors import ApiRequestError  # 안전한 API 오류 형식을 가져온다.
from ai_gitgen.models import ApiSettings  # API 설정 데이터 구조를 가져온다.
from ai_gitgen.security import mask_sensitive_text  # 오류문 속 민감정보를 가리는 함수를 가져온다.


def _build_request(settings: ApiSettings, system_prompt: str, user_prompt: str) -> urllib.request.Request:  # 제공자 형식에 맞는 HTTP 요청을 만든다.
    
    if settings.api_format == "anthropic":  # Anthropic Messages 형식을 사용할지 확인한다.
        payload = {"model": settings.model, "max_tokens": settings.max_tokens, "temperature": settings.temperature, "system": system_prompt, "messages": [{"role": "user", "content": user_prompt}]}  # Anthropic 요청 본문을 만든다.
        headers = {"Content-Type": "application/json", "x-api-key": settings.api_key, "anthropic-version": "2023-06-01"}  # Anthropic 인증과 버전 헤더를 만든다.
    
    else:  # 그 외에는 OpenAI 호환 Chat Completions 형식을 사용한다.
        payload = {"model": settings.model, "temperature": settings.temperature, "max_tokens": settings.max_tokens, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]}  # OpenAI 호환 요청 본문을 만든다.
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.api_key}"}  # Bearer 인증 헤더를 만든다.
    
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")  # 한글을 유지한 JSON을 UTF-8 바이트로 바꾼다.
    
    return urllib.request.Request(settings.api_url, data=encoded, headers=headers, method="POST")  # POST 요청 객체를 완성해 돌려준다.


def _extract_text(payload: object, api_format: str) -> str:  # 제공자별 응답 JSON에서 생성 텍스트를 꺼낸다.
    
    try:  # 예상과 다른 응답을 안전한 오류로 바꾸기 시작한다.
        if api_format == "anthropic":  # Anthropic 응답 구조인지 확인한다.
            content = payload["content"]  # content 배열을 가져온다.
            text_parts = [item["text"] for item in content if item.get("type") == "text"]  # 텍스트 조각만 순서대로 꺼낸다.
            text = "\n".join(text_parts).strip()  # 여러 텍스트 조각을 한 결과로 합친다.
        else:  # OpenAI 호환 응답 구조를 처리한다.
            text = payload["choices"][0]["message"]["content"].strip()  # 첫 번째 생성 답변의 내용을 꺼낸다.
    
    except (KeyError, IndexError, TypeError, AttributeError) as error:  # 필수 응답 필드가 없을 때 오류를 잡는다.
        raise ApiRequestError("AI API 응답 형식을 해석할 수 없습니다.") from error  # 내부 구조를 노출하지 않는 오류로 바꾼다.
    
    if not text:  # 생성 텍스트가 빈 문자열인지 확인한다.
        raise ApiRequestError("AI API가 빈 응답을 반환했습니다.")  # 빈 결과를 성공으로 처리하지 않는다.
    
    return text  # 정상 생성 텍스트를 돌려준다.


def _safe_http_detail(error: urllib.error.HTTPError) -> str:  # HTTP 오류 본문에서 안전한 짧은 설명을 만든다.
    try:  # 오류 본문도 형식이 깨질 수 있으므로 안전하게 읽는다.
        raw = error.read(4096).decode("utf-8", errors="replace")  # 최대 4KB(Kilobyte)만 읽어 과도한 출력을 막는다.
        payload = json.loads(raw)  # JSON 오류 본문을 Python 값으로 바꾼다.
        detail = payload.get("error", {}).get("message", "") if isinstance(payload, dict) else ""  # 일반적인 error.message만 꺼낸다.

    except (OSError, ValueError, AttributeError):  # 본문을 읽거나 JSON으로 바꾸지 못한 경우를 처리한다.
        detail = ""  # 상세 원인을 비워 상태 코드만 사용하게 한다.

    finally:  # 성공과 실패에 관계없이 HTTP 오류 응답 자원을 정리한다.
        error.close()  # 열린 응답 스트림과 연결을 닫아 자원 누수를 막는다.

    return mask_sensitive_text(str(detail))[:200]  # 민감정보를 가리고 최대 200자로 제한한다.


# ✅  system_prompt와 user_prompt를 인자로 받아서 실제 AI API를 호출하는 함수
def generate_text(settings: ApiSettings, system_prompt: str, user_prompt: str) -> str:  # AI API를 정확히 한 번 호출해 텍스트를 받는다.
    
    request = _build_request(settings, system_prompt, user_prompt)  # 설정과 프롬프트로 HTTP 요청을 만든다.
    
    try:  # 네트워크와 응답 형식 오류를 사용자 메시지로 바꾸기 시작한다.
        with urllib.request.urlopen(request, timeout=settings.timeout) as response:  # 지정된 시간까지만 응답을 기다린다.
            raw = response.read()  # 응답 본문을 바이트로 읽는다.
        payload = json.loads(raw.decode("utf-8"))  # UTF-8 JSON 응답을 Python 값으로 바꾼다.
    
    except urllib.error.HTTPError as error:  # 서버가 4xx 또는 5xx 상태를 보낸 경우를 잡는다.
        detail = _safe_http_detail(error)  # 비밀값이 제거된 짧은 상세 오류를 만든다.
        suffix = f" - {detail}" if detail else ""  # 상세 내용이 있을 때만 메시지에 붙인다.
        raise ApiRequestError(f"AI API 요청 실패(HTTP {error.code}){suffix}") from error  # 인증 실패 등을 상태 코드와 함께 알린다.
    
    except (urllib.error.URLError, socket.timeout, TimeoutError) as error:  # 연결 실패나 시간 초과를 잡는다.
        reason = mask_sensitive_text(str(getattr(error, "reason", error)))[:200]  # 네트워크 원인에서도 민감정보를 가린다.
        raise ApiRequestError(f"AI API 네트워크 오류: {reason}") from error  # 사용자가 원인을 구분할 수 있게 알린다.
    
    except (UnicodeDecodeError, json.JSONDecodeError) as error:  # 응답이 UTF-8 JSON이 아닐 때를 잡는다.
        raise ApiRequestError("AI API가 올바른 JSON 응답을 반환하지 않았습니다.") from error  # 원문을 노출하지 않고 형식 오류를 알린다.
    
    return _extract_text(payload, settings.api_format)  # 제공자 형식에 맞게 최종 텍스트를 꺼낸다.
