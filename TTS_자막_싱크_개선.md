# TTS-자막 싱크 테스트 예시

## 문제 해결:
기존 방식: TTS 생성 → Whisper STT → 타이밍 불일치
새로운 방식: TTS 원본 텍스트 + 실제 오디오 길이 → 정확한 타이밍

## API 사용법:

### 1. 기존 TTS 생성 (7단계)
POST /video/create-tts-from-storyboard
```json
{
  "persona_description": "20대 여성",
  "product_name": "스마트워치",
  "brand_name": "테크브랜드",
  "ad_concept": "혁신적인 기술"
}
```

### 2. 새로운 정확한 자막 생성 (8-1단계 개선)
POST /video/generate-subtitles-synced
```json
{
  "tts_audio_files": [
    "static/audio/tts_1.mp3",
    "static/audio/tts_2.mp3"
  ],
  "tts_texts": [
    "테크브랜드의 스마트워치",
    "혁신이 시작됩니다"
  ],
  "tts_durations": [2.5, 3.1]
}
```

## 개선 사항:
1. ✅ TTS 원본 텍스트 사용으로 100% 정확한 내용
2. ✅ 실제 오디오 길이 기반 정확한 타이밍
3. ✅ 누적 시간 계산으로 연속 자막 정확성
4. ✅ SRT 포맷 자동 생성
5. ✅ Whisper STT 백업 방식 지원

## 결과:
- 기존: 싱크 불일치, 텍스트 인식 오류 가능
- 개선: 완벽한 싱크, 100% 정확한 텍스트
