# v0.1 (Not published)
- 기존에 캡스톤 디자인에서 진행되었던 내용입니다.
- 자세한 내용은 [여기](https://github.com/ByoungJoonIm/Capstone_Design)를 참고하세요.

# v0.2 (published)
- (기능) Professor의 과목 개설 가능
- (기능) professor가 다른 Professor를 특정한 과목으로 초대 가능
- (기능) 과제 추가시 input파일에서 ('\n') 단위로 파일을 분할
- (기능) Student의 코드 채점기를 Django-ace로 변경
- (기능) Student가 특정 과목에 수강신청이 가능
- (보안) Professor / Student의 역할 기반 permission 추가로 권한이 없는 페이지를 URL로 접근 불가
- (테스트) 샘플 데이터 추가

# v0.21 (Not published yet)
- (문서) professor guide 작성
- (문서) student guide 작성
- (문서) developer guide 작성
- (문서) main readme 작성
- (기능) homepage를 release 노트로 변경 및 footer에 가이드 추가

# To Do
- 디자인 개선
- Docker 이미지 배포
- Professor의 과제 등록시 파일 분할 방법 개선
- Student가 과제 수행시, 만료된 과제에 대한 처리
- 과제 채점의 메모리/시간 제한 추가
- Professor의 과제 삭제 및 수정
- Dmoj-server를 분리하여 dmoj-cli 대신 사용
- 관리자 기능 추가
  - 계정 추가/수정/삭제