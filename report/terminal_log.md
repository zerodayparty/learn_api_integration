# 🟩 terminal 실습 내용  

<br>

## 🟢 1. commit 명령어 실행  

### 🟡 % python3 main.py commit                                                      


```sh
[INFO] Git status 수집 완료: 4개 파일 변경 감지  
[INFO] Git diff 수집 완료: 201줄  
[INFO] 안전 모드: ON  
[INFO] 안전 모드 전송 제한이 적용되었습니다.  
[INFO] AI API 요청 중... (이번 실행 1회)  
[DONE] 커밋 메시지 생성 완료  

=== Commit Message ===  
feat(cli): .env 파일 자동 로드 및 코드 정리  

- load_dotenv() 함수 추가로 .env 파일에서 환경변수 자동 로드 지원  
- main() 함수에서 load_dotenv() 호출 및 코드 포맷팅 개선  
=== End Commit Message ===  

[NOTICE] AI 초안은 사실과 민감정보를 검토한 뒤 사용하세요.  
```


<br><br>

## 🟢 2. pr 명령어 실행  


### 🟡 % python3 main.py pr    

```sh
[INFO] Git status 수집 완료: 4개 파일 변경 감지  
[INFO] Git diff 수집 완료: 201줄  
[INFO] 안전 모드: ON  
[INFO] 안전 모드 전송 제한이 적용되었습니다.  
[INFO] AI API 요청 중... (이번 실행 1회)  
[DONE] PR 초안 생성 완료  
```
```md
=== PR Title ===  
.env 파일 자동 로드 기능 추가 및 코드 포맷팅 개선  

=== PR Body ===  
## Why  
- 환경변수 관리를 위해 .env 파일 자동 로드 기능이 필요함  
- 테스트 환경에서 .env 로드를 제어할 수 있는 메커니즘 필요  
- 코드 가독성 향상을 위한 포맷팅 개선  

## What  
- cli.py에 load_dotenv() 함수 추가: .env 파일을 읽어 환경변수로 자동 등록  
- AI_GITGEN_NO_DOTENV 환경변수로 .env 로드 스킵 기능 지원  
- 주석 처리된 줄과 빈 줄 무시, 따옴표 처리 등 안전한 파싱 구현  
- main() 함수에서 load_dotenv() 호출 추가  
- git_service.py의 collect_git_context() 함수에 명확한 섹션 구분 추가  
- 전체 코드에 일관된 줄 간격 포맷팅 적용  

## How to Test  
- .env 파일을 프로젝트 루트에 생성하고 환경변수 설정 후 실행  
- AI_GITGEN_NO_DOTENV=1 환경변수 설정 후 .env 로드가 건너뛰어지는지 확인  
- 존재하지 않는 .env 파일 경로로 실행하여 오류 없이 진행되는지 확인  
=== End PR Draft ===  

[NOTICE] AI 초안은 사실과 민감정보를 검토한 뒤 사용하세요.  
```




<br><br>

## 🟢 3. API Key가 없는 상태에서 실행하면 오류 메시지가 출력되고 종료되는가?  

- API 주석 처리  

### 🟡 결과  
device@user learn_api_integration % python3 main.py commit  
[INFO] Git status 수집 완료: 3개 파일 변경 감지  
[INFO] Git diff 수집 완료: 92줄  
[INFO] 안전 모드: ON  
[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.  
[RECOVERY] 프로젝트 루트에서 cp .env.example .env 실행 후 .env에 실제 Key를 입력하세요.  









<br><br>

## 🟢 4. Git 변경 사항이 없으면 안내 메시지를 출력하고 종료하는가?  

- 변경사항 없는 상태  

device@user learn_api_integration % python3 main.py commit  
[INFO] 변경 사항이 없습니다. 초안을 생성하지 않고 종료합니다.  








<br><br>

## 🟢 5. -temperature 0  

### 🟡 % python3 main.py commit -temperature 0.0 -max-tokens 300                       


```sh
[INFO] Git status 수집 완료: 4개 파일 변경 감지  
[INFO] Git diff 수집 완료: 201줄  
[INFO] 안전 모드: ON  
[INFO] 안전 모드 전송 제한이 적용되었습니다.  
[INFO] AI API 요청 중... (이번 실행 1회)  
[DONE] 커밋 메시지 생성 완료  

=== Commit Message ===  
feat(cli): .env 파일 자동 로드 및 코드 정리  

- load_dotenv() 함수 추가로 .env 파일에서 환경변수 자동 로드 지원  
- main() 함수에서 load_dotenv() 호출 및 코드 포맷팅 개선  
=== End Commit Message ===  

[NOTICE] AI 초안은 사실과 민감정보를 검토한 뒤 사용하세요.  
```


### 🟡 % python3 main.py commit -temperature 0.0 -max-tokens 300  

```sh
[INFO] Git status 수집 완료: 4개 파일 변경 감지  
[INFO] Git diff 수집 완료: 201줄  
[INFO] 안전 모드: ON  
[INFO] 안전 모드 전송 제한이 적용되었습니다.  
[INFO] AI API 요청 중... (이번 실행 1회)  
[DONE] 커밋 메시지 생성 완료  

=== Commit Message ===  
feat(cli): .env 파일 자동 로드 및 코드 정리  

- load_dotenv() 함수 추가로 .env 파일에서 환경변수 자동 로드 지원  
- main() 함수에서 load_dotenv() 호출하여 초기화 단계에 통합  
=== End Commit Message ===  
```




<br><br>

## 🟢 4. -temperature 1  

### 🟡 % python3 main.py commit -temperature 1.0 -max-tokens 300  


```sh
[INFO] Git status 수집 완료: 4개 파일 변경 감지  
[INFO] Git diff 수집 완료: 201줄  
[INFO] 안전 모드: ON  
[INFO] 안전 모드 전송 제한이 적용되었습니다.  
[INFO] AI API 요청 중... (이번 실행 1회)  
[DONE] 커밋 메시지 생성 완료  

=== Commit Message ===  
feat(cli, git_service): .env 자동 로드 및 코드 정리  

- `load_dotenv()` 함수 추가로 .env 파일 자동 로드 기능 구현  
- 주요 함수에 주석 개선 및 코드 포맷팅으로 가독성 향상  
=== End Commit Message ===  

[NOTICE] AI 초안은 사실과 민감정보를 검토한 뒤 사용하세요.  
```

