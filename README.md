# Autoshort / 워크플로우 (1~8단계)

이 레포는 아이디어 → 페르소나 → 광고 컨셉 → 스토리보드 → 이미지 → TTS → 자막(싱크/순차) → 비디오 합치기(트랜지션/BGM) → 배포(서버)까지 일련의 작업을 FastAPI API로 제공하고, FFmpeg를 통해 최종 영상을 생성합니다. 아래 1~8단계 통합 가이드를 따라 하면 전체 파이프라인을 한 번에 구축/실행할 수 있습니다.

## 빠른 시작
- OS: Windows (검증됨)
- 필수: Python 3.10+, FFmpeg 설치(환경변수 PATH 등록)
- 의존성 설치:
```powershell
pip install -r requirements.txt
```
- FFmpeg 확인:
```powershell
ffmpeg -version
```
- 서버 실행(선택):
```powershell
python fastapi_tts_subtitle_server.py
```
서버가 실행되면 기본 포트는 `http://localhost:8000` 입니다.

## 1단계: 타겟 고객 분석 및 페르소나 생성
- 목적: 입력한 타겟 고객 정보로 LLM이 상세 페르소나를 생성
- 엔드포인트: `POST /step1/target-customer`
- 입력: 국가/연령/성별/특징 등
- 내부 처리: `workflows.py`의 `generate_persona` → `PersonaData` 반환

## 2단계: 광고 컨셉 생성(이미지 분석 포함)
- 목적: 페르소나 + (선택) 참조 이미지 분석을 기반으로 광고 핵심 컨셉 생성
- 엔드포인트: `POST /step2/generate-ad-concept-with-images`
- 내부 처리: `workflows.py`의 `create_ad_concept` → `vision_llm`로 이미지 분석, `text_llm`로 컨셉 텍스트 생성

## 3단계: 스토리보드 생성
- 목적: 확정한 아이디어와 분석 결과로 장면별 프롬프트(`SceneImagePrompt`) 생성
- 엔드포인트: `POST /step3/generate-storyboard`
- 내부 처리: `workflows.py`의 `generate_scene_prompts` → 영어 `promptText` + 한국어 설명 포함한 `StoryboardOutput` 생성

## 4단계: 이미지 생성(Runway API)
- 목적: 각 장면 프롬프트를 Runway API에 직렬로 요청하여 이미지 생성
- 엔드포인트: `POST /step4/generate-images`
- 내부 처리: `workflows.py`의 `generate_images_sequentially` → 성공/실패/이미지URL 리스트 반환

## 5단계: TTS 내레이션 생성
- 목적: 페르소나/마케팅/컨셉/장면 설명을 결합해 자연스러운 한국어 내레이션을 TTS로 생성
- 엔드포인트: `POST /video/create-tts-from-storyboard`
- 내부 처리: `tts_utils.py`(ElevenLabs) → 인트로/장면/아웃트로 스크립트 별 MP3 파일 생성 후 메타정보 반환

예시 요청(요약):
```json
{
  "persona_description": "20-30대 직장인 여성...",
  "marketing_insights": "건강한 재료...",
  "ad_concept": "프리미엄 도시락 브랜드",
  "storyboard_scenes": [{"scene_number":1,"promptText":"...","duration":5}],
  "voice_id": "Xb7hH8MSUJpSbSDYk0k2",
  "voice_gender": "female",
  "voice_language": "ko"
}
```

## 6단계: 자막 생성 + 싱크/순차 개선
- 목적: TTS 오디오 길이에 맞춰 자막을 자동 생성하고, 겹침 없이 한 줄씩 순차적으로 표시
- 핵심: `subtitle_utils.py`와 문서 [SEQUENTIAL_SUBTITLES_GUIDE.md](SEQUENTIAL_SUBTITLES_GUIDE.md)
- 구현 포인트:
  - 기본 싱크 자막: `create_tts_synced_subtitle_file(...)`
  - Whisper 기반 정밀 자막: `create_precise_whisper_subtitles(...)`
  - 순차 자막 스타일/파라미터: `get_korean_subtitle_style(...)`, `max_chars`, `line_duration`, `gap_duration` 등
  - 여러 SRT를 순서대로 합치기: `merge_srt_files_sequentially(...)`

예시(순차 자막 생성):
```python
from subtitle_utils import create_sequential_subtitle_file
seq_path = create_sequential_subtitle_file(
  subtitle_file_path="원본.srt",
  output_path="순차적_자막.srt",
  max_chars=15,
  line_duration=1.5,
  gap_duration=0.3
)
```

## 7단계: 비디오 합치기(트랜지션/BGM/TTS/자막)
- 목적: FFmpeg 중심으로 비디오들을 이어 붙이고, 트랜지션/자막/BGM/TTS를 통합
- 기본 모듈: `video_server_utils.py`
  - FFmpeg 경로 자동 탐색 + `ffprobe` 우선 사용
  - 다중 폴백: 트랜지션 실패 시 `concat`으로 대체, BGM 실패 시 비디오만 처리 등
  - 출력 디렉토리: `static/videos`(기본) 또는 `output_videos`
- 주요 함수:
  - `merge_videos_with_frame_transitions(...)`: 다수 비디오 + BGM + 자막 통합
  - 내부 보조: `_merge_with_transitions_only`, `_merge_with_transitions_bgm_and_subtitle`, `_simple_concat_only` 등
- 트랜지션 종류: `fade`, `wipeleft`, `slideright`, `circleopen`, `dissolve`, `pixelize` 등(FFmpeg xfade)

다중 비디오 + 순차 자막 + BGM 통합 예시(요약):
```python
from video_tts_subtitle_api import create_multiple_videos_with_sequential_subtitles
result = await create_multiple_videos_with_sequential_subtitles(
  video_files=["a.mp4","b.mp4"],
  tts_texts=["텍스트A","텍스트B"],
  voice_id="Xb7hH8MSUJpSbSDYk0k2",
  font_size=30,
  max_chars_per_line=6,
  tts_volume=0.8,
  bgm_volume=0.4,
  enable_bgm=True
)
```

## 8단계: 서버/API 사용 및 최종 배포
- 목적: FastAPI로 엔드포인트 노출, 웹에서 결과 비디오/오디오/자막 서빙
- 실행:
```powershell
python fastapi_tts_subtitle_server.py
```
- 기본 정적 폴더: `static/` (audio, subtitles, videos)
- 대표 엔드포인트(예):
  - `POST /video/create-tts-from-storyboard` → TTS 내레이션 생성
  - `POST /video/merge-with-tts` → 비디오 + TTS 통합(기존 예시)
  - 고도화된 다중 처리: `create_multiple_videos_with_sequential_subtitles(...)` (내부 함수)

생성 결과 접근:
- 비디오: `/static/videos/<파일명>`
- 오디오: `/static/audio/<파일명>`
- 자막: `/static/subtitles/<파일명>`

---

## 운영 팁 / 트러블슈팅
- FFmpeg가 인식되지 않으면 PATH 설정 또는 경로 직접 지정 필요
- 대용량 다운로드/처리 시 네트워크/디스크 용량 확인
- Whisper 사용 시 모델/환경 의존성 확인(속도/정확도 고려)
- 실패 시 자동 폴백이 동작하나, 로그를 보고 원인 파악하는 것이 좋습니다

## 로컬 테스트용 빠른 명령들
- 서버 구동:
```powershell
python fastapi_tts_subtitle_server.py
```
- API 호출 샘플(파워셸 `Invoke-RestMethod` 예):
```powershell
$body = @{ persona_description="..."; marketing_insights="..."; ad_concept="..."; storyboard_scenes=@(@{scene_number=1; promptText="..."; duration=5}) ; voice_id="Xb7hH8MSUJpSbSDYk0k2"; voice_gender="female"; voice_language="ko" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/video/create-tts-from-storyboard -ContentType application/json -Body $body
```

## 파일 구조 참고
- `video_server_utils.py`: FFmpeg 기반 비디오 병합/트랜지션/자막/BGM 통합
- `video_tts_subtitle_api.py`: 다중 비디오용 TTS+자막 워크플로우 예시 함수들
- `subtitle_utils.py`: 자막 생성/합치기/스타일 관리
- `tts_utils.py`: ElevenLabs TTS 생성
- `workflows.py`: 1~4단계(LLM 기반 분석/생성) 로직
- 정적 리소스: `static/audio`, `static/subtitles`, `static/videos`

이 문서는 전체 파이프라인(1~8단계)을 한 곳에 모아 빠르게 구축/검증할 수 있도록 구성되었습니다. 필요하면 단계별 엔드포인트를 확장하거나, FFmpeg 옵션(트랜지션/스타일/코덱)을 팀 표준에 맞게 조정하세요.
