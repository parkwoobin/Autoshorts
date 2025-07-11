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

## 🎙️ TTS 내레이션 생성 기능

### 스토리보드 기반 TTS 내레이션 생성

**목표**: persona_description, marketing_insights, ad_concept, 스토리보드 scene 설명을 결합하여 자연스러운 TTS 내레이션을 생성합니다.

- **API 엔드포인트**: `POST /video/create-tts-from-storyboard`
- **요청 데이터**:
```json
{
  "persona_description": "20-30대 직장인 여성으로, 건강한 라이프스타일에 관심이 많은 사람",
  "marketing_insights": "건강한 재료로 만든 간편식에 대한 니즈가 높음",
  "ad_concept": "바쁜 일상 속에서도 건강하고 맛있는 식사를 즐길 수 있는 프리미엄 도시락 브랜드",
  "storyboard_scenes": [
    {
      "scene_number": 1,
      "promptText": "A busy office worker woman looking tired while eating instant food",
      "duration": 5
    },
    {
      "scene_number": 2,
      "promptText": "A beautiful premium lunchbox with fresh vegetables and healthy ingredients",
      "duration": 5
    }
  ],
  "voice_id": "Xb7hH8MSUJpSbSDYk0k2",
  "voice_gender": "female",
  "voice_language": "ko"
}
```

- **작동 순서**:
  1. **인트로 스크립트 생성**: persona_description, marketing_insights, ad_concept을 결합하여 광고 시작 내레이션 생성
  2. **장면별 스크립트 생성**: 각 storyboard scene의 promptText를 자연스러운 한국어 내레이션으로 변환
  3. **아웃트로 스크립트 생성**: 광고 마무리 내레이션 추가
  4. **TTS 변환**: ElevenLabs API를 통해 각 스크립트를 음성 파일로 변환
  5. **결과 반환**: 성공한 TTS 파일들의 URL과 메타데이터 반환

- **응답 데이터**:
```json
{
  "success": true,
  "message": "스토리보드 기반 TTS 내레이션 생성 완료! 5개 오디오 파일 생성",
  "successful_tts": [
    {
      "scene_number": 0,
      "script_type": "intro",
      "description": "인트로 - 페르소나, 마케팅 인사이트, 광고 컨셉 소개",
      "text": "타겟 고객은 20-30대 직장인 여성으로...",
      "audio_url": "/static/audio/intro_tts_12345.mp3",
      "duration": 8.5,
      "file_size": 136000
    },
    {
      "scene_number": 1,
      "script_type": "scene",
      "description": "장면 1 설명",
      "text": "장면 1: 한 여성이 피곤해 보이며 즉석식품을 먹고 있는 모습",
      "audio_url": "/static/audio/scene1_tts_12346.mp3",
      "duration": 6.2,
      "file_size": 99200
    }
  ],
  "summary": {
    "total_scripts": 5,
    "successful": 5,
    "failed": 0,
    "success_rate": "100.0%"
  }
}
```

### 사용 예시

```python
import httpx
import asyncio

async def create_tts_narration():
    url = "http://localhost:8000/video/create-tts-from-storyboard"
    
    data = {
        "persona_description": "20-30대 직장인 여성으로, 건강한 라이프스타일에 관심이 많은 사람",
        "marketing_insights": "건강한 재료로 만든 간편식에 대한 니즈가 높음",
        "ad_concept": "바쁜 일상 속에서도 건강하고 맛있는 식사를 즐길 수 있는 프리미엄 도시락 브랜드",
        "storyboard_scenes": [
            {
                "scene_number": 1,
                "promptText": "A busy office worker woman looking tired while eating instant food",
                "duration": 5
            }
        ],
        "voice_id": "Xb7hH8MSUJpSbSDYk0k2",  # Alice (여성, 다국어)
        "voice_gender": "female",
        "voice_language": "ko"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        result = response.json()
        
        print(f"생성된 TTS 파일: {len(result['successful_tts'])}개")
        for tts in result['successful_tts']:
            print(f"- {tts['description']}: {tts['audio_url']}")

# 실행
asyncio.run(create_tts_narration())
```

### TTS + 비디오 합치기

생성된 TTS 파일들을 비디오와 합치려면:

```python
# 1. 스토리보드 기반 TTS 생성
tts_response = await client.post("/video/create-tts-from-storyboard", json=storyboard_data)
tts_scripts = [tts["text"] for tts in tts_response.json()["successful_tts"]]

# 2. TTS와 비디오 합치기
merge_data = {
    "video_urls": ["https://example.com/video1.mp4", "https://example.com/video2.mp4"],
    "text_list": tts_scripts,
    "transition_type": "fade",
    "voice_id": "Xb7hH8MSUJpSbSDYk0k2",
    "tts_volume": 0.8,
    "video_volume": 0.3
}

final_response = await client.post("/video/merge-with-tts", json=merge_data)
final_video_url = final_response.json()["video_url"]
```
