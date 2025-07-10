# ⚙️ 쇼츠파일럿 핵심 작동 원리 및 워크플로우

쇼츠파일럿은 총 4단계의 워크플로우를 통해 아이디어를 구체적인 결과물로 만듭니다. 각 단계는 이전 단계의 결과물을 입력으로 사용하여 유기적으로 연결됩니다.

## 1️⃣ 단계: 타겟 고객 분석 및 페르소나 생성
**목표**: 사용자가 입력한 타겟 고객 정보를 바탕으로, LLM이 살아있는 페르소나와 마케팅 인사이트를 생성합니다.

- **API 엔드포인트**: `POST /step1/target-customer`
- **작동 순서**:
  1. 사용자가 타겟 고객 정보(국가, 연령대, 성별 등)를 API에 전달합니다.
  2. FastAPI는 이 데이터를 `TargetCustomer` Pydantic 모델로 자동 검증합니다.
  3. `workflows.py`의 `generate_persona` 함수가 호출됩니다.
  4. `text_llm` (GPT 모델)은 제공된 정보와 프롬프트 지침에 따라 고객의 특징, 라이프스타일, 소비 패턴 등을 포함한 상세한 **페르소나(PersonaData)**를 생성하여 반환합니다.

## 2️⃣ 단계: 광고 컨셉 생성 (with 이미지 분석)
**목표**: 생성된 페르소나와 사용자가 선택적으로 업로드한 참조 이미지를 바탕으로, LLM이 전체 광고의 핵심 컨셉과 전략을 제안합니다.

- **API 엔드포인트**: `POST /step2/generate-ad-concept-with-images`
- **작동 순서**:
  1. 사용자가 선택적으로 참조 이미지(`ReferenceImage`) 리스트를 업로드합니다. 이미지가 없어도 진행 가능합니다.
  2. `workflows.py`의 `create_ad_concept` 함수가 호출됩니다.
  3. 참조 이미지가 있는 경우, `analyze_reference_images` 함수가 `vision_llm` (GPT-4o)을 통해 각 이미지의 특징과 광고 활용 포인트를 분석합니다.
  4. `text_llm`은 페르소나 정보와 이미지 분석 결과를 종합하여, 캐치프레이즈, 핵심 메시지, 영상 분위기, 활용 전략 등이 포함된 광고 컨셉(`ad_concept`) 텍스트를 생성합니다.
  5. 이미지 분석 결과(`analyzed_images`) 또한 함께 반환되어 다음 단계를 위해 저장됩니다.

## 3️⃣ 단계: 스토리보드 생성
**목표**: 사용자가 확정한 광고 아이디어를 바탕으로, LLM이 구체적인 장면별(Scene) 프롬프트를 생성합니다.

- **API 엔드포인트**: `POST /step3/generate-storyboard`
- **작동 순서**:
  1. 이전 단계에서 생성된 `ad_concept`을 사용자가 확인 및 수정한 최종 아이디어(`user_description`)와 2단계의 이미지 분석 결과(`analyzed_images`)를 프로젝트 상태에서 불러옵니다.
  2. `workflows.py`의 `generate_scene_prompts` 함수가 호출됩니다.
  3. LLM은 `system_template`의 정교한 지시에 따라 다음 작업을 수행합니다.
     - `prompt_text`는 이미지 생성에 유리하도록 영어로 작성합니다.
     - `video_concept` 등 나머지 필드는 한국어로 작성합니다.
     - 참조 이미지를 어느 장면에 사용할지, 또는 사용하지 않을지 창의적으로 판단합니다.
  4. 최종적으로, 각 장면의 상세 정보(`SceneImagePrompt`)가 담긴 `StoryboardOutput` Pydantic 객체를 생성하여 반환합니다. 이 객체에는 전체 장면 수, 예상 길이 등의 메타데이터도 포함됩니다.

## 4️⃣ 단계: 이미지 생성
**목표**: 생성된 스토리보드의 각 장면 프롬프트를 Runway API로 전송하여 실제 이미지를 생성합니다.

- **API 엔드포인트**: `POST /step4/generate-images`
- **작동 순서**:
  1. 3단계에서 생성된 `storyboard.scenes` 리스트를 API에 전달합니다. (전달하지 않으면 프로젝트에 저장된 값을 사용)
  2. `workflows.py`의 `generate_images_sequentially` 함수가 호출됩니다.
  3. `scenes` 리스트를 순회하며 각 `SceneImagePrompt` 객체에 대해 **직렬(Sequentially)**로 Runway API에 이미지 생성을 요청합니다. (API 정책 준수)
  4. Pydantic 모델의 alias와 `model_dump(by_alias=True)` 기능을 활용하여, 파이썬 코드(`snake_case`)와 API 요구사항(`camelCase`) 사이의 이름 규칙 차이를 자동으로 변환합니다.
  5. 각 장면의 이미지 생성이 완료되면, 성공/실패 상태와 이미지 URL이 포함된 최종 결과 리스트를 반환합니다.

## 🛠️ 주요 기술 스택
- **백엔드**: FastAPI, Uvicorn
- **LLM 연동**: LangChain, OpenAI
- **이미지 생성**: Runway API (httpx를 통한 직접 호출)
- **데이터 유효성 검사**: Pydantic
- **환경 변수 관리**: python-dotenv

## 🚀 설정 및 실행 방법

### 저장소 복제:
```bash
git clone https://github.com/kimsunggak/shortpilot.git
cd shortpilot
```

### 가상 환경 생성 및 활성화:
```bash
python -m venv myenv
source myenv/bin/activate  # macOS/Linux
myenv\Scripts\activate  # Windows
```

### 의존성 설치:
```bash
pip install -r requirements.txt
```

### 환경 변수 설정:
프로젝트 루트에 `.env` 파일을 생성합니다.
```
OPENAI_API_KEY="sk-..."
RUNWAY_API_KEY="your_runway_api_key"
```

### 서버 실행:
```bash
uvicorn client:app --reload
```
서버가 `http://localhost:8000`에서 실행됩니다.

웹 브라우저에서 `http://localhost:8000/docs`로 접속하면 자동 생성된 API 문서를 확인할 수 있습니다.
