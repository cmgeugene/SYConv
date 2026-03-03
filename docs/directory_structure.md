# 프로젝트 디렉터리 구조 및 파일별 역할 명세서 (Project Structure & File Roles)

이 문서는 하이브리드(Python + React) 방식으로 개발되는 영어 문제집 단어 추출 앱의 전체 폴더 구조와 각 폴더 및 파일이 담당하는 역할(Role)을 상세히 정의합니다. 개발 과정에서 파일을 생성하고 코드를 작성할 때 이 문서를 나침반으로 삼습니다.

## 최상위 디렉터리 (Root Directory)

```text
SYConv/
├── docs/                 # 프로젝트 기획, 요구사항, 아키텍처 등 문서 
├── backend/              # Python 기반의 API 서버 및 이미지/자연어 처리 핵심 로직
├── frontend/             # React 기반의 사용자 UI (뷰어 및 데이터 검수 시트)
└── README.md             # 프로젝트 소개 및 실행 방법 안내
```

---

## 1. Backend 디렉터리 구조 (`backend/`)

Python FastAPI를 사용하여 이미지 전처리, OCR 구동, 그리고 외부 LLM API(OpenAI/Anthropic)와의 통신을 전담하는 백엔드 서버입니다.

```text
backend/
├── app/                        # FastAPI 애플리케이션 핵심 소스코드
│   ├── main.py                 # 앱 엔트리 포인트 (FastAPI 인스턴스 생성, CORS 설정, 라우터 등록)
│   ├── api/                    # API 엔드포인트 라우터 모음
│   │   ├── routes.py           # 파일 업로드(POST) 및 처리 결과를 반환하는 API 엔드포인트 정의
│   │   └── dependencies.py     # API 라우터에서 공통으로 사용하는 의존성 (예: 인증, 파일 검증 등 - 필요시 확장)
│   ├── core/                   # 핵심 비즈니스 로직 및 알고리즘
│   │   ├── image_processing.py # OpenCV 기반 이미지 처리 (2열 청킹, 형광펜(HSV) 박스 좌표 추출)
│   │   ├── ocr_engine.py       # EasyOCR/Tesseract 구동, 텍스트 및 기본 좌표 추출, 형광펜 박스와의 교차 영역(Intersection) 계산
│   │   ├── llm_parser.py       # 추출된 텍스트 묶음을 OpenAI/Anthropic API로 전송, 프롬프트 엔지니어링 및 JSON 결과 파싱
│   │   └── config.py           # 환경 변수 및 설정 관리 (API 키, OCR 모델 경로, 로깅 레벨 등)
│   ├── models/                 # Pydantic 데이터 모델 (요청 및 응답 스키마 정의 타입 힌팅용)
│   │   └── schemas.py          # API 응답 규격 (예: { word, pos, meaning, bbox_x, bbox_y })
│   └── utils/                  # 공통 유틸리티 함수
│       └── file_helper.py      # 임시 파일 저장, PDF를 이미지로 변환(pdf2image) 등 파일 조작 헬퍼
├── tests/                      # 백엔드 단위 테스트(Unit Test) 및 통합 테스트 코드
│   └── test_processing.py      # 이미지 처리 및 API 응답 테스트 검증 스크립트
├── requirements.txt            # Python 의존성 패키지 목록 (fastapi, opencv-python, easyocr 등)
└── .env.example                # 환경 변수 템플릿 파일 (실제 .env는 gitignore 처리)
```

---

## 2. Frontend 디렉터리 구조 (`frontend/`)

React(Vite) 기반으로 구동되며, 사용자가 업로드한 문서(이미지) 원본과 백엔드에서 분석한 결과(단어 리스트)를 동시에 보고 편집할 수 있는 대시보드 형태의 UI입니다.

```text
frontend/
├── index.html                  # React 앱이 마운트되는 최상위 HTML 파일
├── package.json                # npm 의존성 패키지 및 빌드 스크립트 (react, vite, ag-grid, xlsx 등)
├── vite.config.js              # Vite 빌더 설정 파일 (포트, 프록시 설정 등)
├── src/                        # 프론트엔드 핵심 소스코드
│   ├── main.jsx                # React 앱 엔트리 포인트 (컴포넌트 렌더링 및 프로바이더 설정)
│   ├── App.jsx                 # 최상위 레이아웃 컴포넌트 (상태 관리 로직 및 분할 화면 구성)
│   ├── App.css                 # 전역 스타일 및 레이아웃 CSS (Tailwind 등 유틸리티 사용 가능)
│   ├── components/             # 재사용 가능한 UI 컴포넌트 모음
│   │   ├── layout/
│   │   │   └── SplitPane.jsx   # 좌/우 화면 분할 및 크기 조절이 가능한 레이아웃 컨테이너
│   │   ├── viewer/
│   │   │   ├── DocumentViewer.jsx # (좌측 UI) 원본 이미지를 표시하고 캔버스/SVG로 하이라이트 박스를 그리는 컴포넌트
│   │   │   └── CanvasOverlay.jsx  # 이미지 위에 투명한 박스(Bounding Box)를 정확한 좌표에 렌더링하는 헬퍼 컴포넌트
│   │   ├── datasheet/
│   │   │   └── DataSheet.jsx   # (우측 UI) Ag-Grid 등을 활용해 데이터(단어/품사/뜻)를 표 형태로 렌더링하고 편집(수정) 기능을 제공
│   │   └── common/
│   │       ├── FileUpload.jsx  # 드래그 앤 드롭 파일 업로드 컴포넌트
│   │       └── LoadingSpinner.jsx # 백엔드 처리 중 표시될 로딩 UI
│   ├── services/               # 백엔드 API와의 통신을 담당하는 계층
│   │   └── api.js              # 파일 업로드(fetch/axios) 및 데이터 송수신 로직 (추상화)
│   ├── utils/                  # 프론트엔드 공통 유틸리티
│   │   ├── exportHelper.js     # 검수 완료된 JSON 데이터를 엑셀(.xlsx) 또는 .xml 형식으로 변환하여 다운로드하는 로직 (XLSX.js 활용)
│   │   └── coordinateMath.js   # 백엔드의 이미지 좌표(고해상도)를 프론트엔드 뷰어(축소된 화면) 비율에 맞게 변환하는 수학 함수
│   └── assets/                 # 정적 리소스 (로고, 아이콘 디폴트 이미지 등)
└── .env                        # 프론트엔드 환경 변수 (예: VITE_API_BASE_URL)
```

## 핵심 요약
* **`backend/core/`**: 프로젝트의 심장. 컴퓨터 비전(OpenCV)과 자연어 처리(LLM)가 결합되는 주요 알고리즘이 위치합니다.
* **`frontend/src/components/viewer/` & `datasheet/`**: 앱의 UX를 결정짓는 눈. 백엔드의 분석 결과 좌표를 부드럽게 시각화하고, 사용자가 쉽게 검수할 수 있는 인터페이스를 담당합니다.
