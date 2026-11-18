# 📑 K-PDF Studio

**한글 특화 고성능 PDF 뷰어 & 리치 텍스트 / 도형 편집기**  
*PyQt6 & PyMuPDF 기반 단일 파일 완결형 고성능 윈도우 데스크톱 애플리케이션*

---

## ✨ 핵심 기능

- **한글 특화 고성능 렌더링 & 인라인 편집**:
  - PyMuPDF 기반 고속 페이지 래스터라이징 및 CJK 폰트 처리
  - 시스템 내 400여 종 폰트 및 TTC 컬렉션 페이스 완벽 인덱싱
  - 한글 텍스트 블록 인라인 수정 및 실시간 미리보기
- **도형 & 어노테이션 스튜디오**:
  - 사각형, 타원, 직선, 화살표, 하이라이트(형광펜), 취소선, 밑줄 등 8방향 핸들 자유 제어
  - 더블클릭 인라인 속성 편집 지원
- **초경량 네이티브 런처 & 바로가기**:
  - 26KB 독립 C++ 네이티브 런처 (`KPDFStudio.exe`) 포함
  - 윈도우 기본 PDF 뷰어로 원클릭 등록 (`register_kpdf_default.bat`)
  - 작업 표시줄 및 바탕화면 바로가기 원클릭 생성 (`create_shortcut.bat`)
- **네이티브 인쇄 & 듀얼 테마**:
  - Win32 GDI 네이티브 드라이버 대화상자 (`DocumentPropertiesW`) 연동 고품질 인쇄
  - 다크 모드 / 라이트 모드 실시간 전환 지원
  - 좌/우 접이식 사이드바 (썸네일 탐색기 & 속성 패널)

---

## 🚀 빠른 시작 (Quick Start)

### 1. 요구 사항
- Python 3.10 이상
- Windows 10 / 11

### 2. 필수 라이브러리 설치
```bash
pip install PyQt6 pymupdf
```
*(선택 사항: 투명 알파 이미지 고화질 합성을 위해 `pip install Pillow` 권장)*

### 3. 실행 방법
- **더블클릭 실행**: `run_kpdf_studio.bat` 또는 `KPDFStudio.exe` 실행
- **터미널 실행**:
```bash
python kpdf_studio.py
```

---

## 🛠 기본 프로그램(연결 프로그램) 등록

PDF 파일을 더블클릭했을 때 바로 K-PDF Studio로 열리도록 설정하려면:
- `register_kpdf_default.bat`을 실행하거나,
- 터미널에서 `python register_associations.py`를 실행하세요.

---

## 📂 파일 구성

- `kpdf_studio.py`: 단일 파일 완결형 메인 애플리케이션 소스코드
- `KPDFStudio.exe`: 26KB 윈도우 연결용 독립 실행 런처
- `register_kpdf_default.bat`: 윈도우 PDF 연결 프로그램 등록 스크립트
- `create_shortcut.bat` / `.ps1`: 바로가기 생성기
- `HANDOFF_KPDF_STUDIO.md`: 상세 아키텍처 및 개발 인수인계 내역서

---

## 📄 라이선스 & 면책 조항

- 본 프로젝트는 **GNU Affero General Public License v3.0 (AGPLv3)** 하에 배포됩니다.
- 본 소프트웨어는 오픈소스 라이브러리인 PyMuPDF(AGPLv3) 및 PyQt6(GPLv3)를 사용합니다.

