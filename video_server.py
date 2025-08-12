"""
간소화된 비디오 서버: 트랜지션 및 비디오 합치기 전용
독립적인 FastAPI 서버
"""
import uvicorn
import os
import httpx
import asyncio
import re
import time
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Optional

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

print("🔑 환경변수 로드 완료")
print(f"   ELEVENLABS_API_KEY: {'✅ 설정됨' if os.getenv('ELEVENLABS_API_KEY') else '❌ 없음'}")
print(f"   OPENAI_API_KEY: {'✅ 설정됨' if os.getenv('OPENAI_API_KEY') else '❌ 없음'}")
print(f"   RUNWAY_API_KEY: {'✅ 설정됨' if os.getenv('RUNWAY_API_KEY') else '❌ 없음'}")
print(f"   SUNO_API_KEY: {'✅ 설정됨' if os.getenv('SUNO_API_KEY') else '❌ 없음'}")

# 비디오 서버 유틸리티 함수들 import
from video_server_utils import (
    SAMPLE_VIDEO_URLS,
    create_merger_instance,
    generate_output_filename,
    create_video_response,
    get_transition_description
)
from video_models import VideoMergeRequest, VideoConfig

# TTS와 자막 관련 import는 try-except로 처리
try:
    from tts_utils import create_tts_audio, create_multiple_tts_audio, get_elevenlabs_api_key
    TTS_AVAILABLE = True
except ImportError:
    print("⚠️ TTS 모듈을 찾을 수 없습니다. TTS 기능이 비활성화됩니다.")
    TTS_AVAILABLE = False

try:
    from subtitle_utils import generate_subtitles_with_whisper, merge_video_with_subtitles, merge_video_with_tts_and_subtitles
    SUBTITLE_AVAILABLE = True
except ImportError:
    print("⚠️ 자막 모듈을 찾을 수 없습니다. 자막 기능이 비활성화됩니다.")
    SUBTITLE_AVAILABLE = False

# SUNO BGM 생성 함수들
async def generate_suno_bgm(keyword: str = "happy", duration: int = 70):
    """SUNO API를 사용한 BGM 생성 (최대 70초)"""
    # 최대 70초로 제한
    if duration > 70:
        duration = 70
        print(f"⚠️ BGM 길이가 70초로 제한됩니다.")
    
    api_key = os.getenv('SUNO_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="SUNO_API_KEY가 설정되지 않았습니다.")
    
    api_endpoint = "https://api.sunoapi.org/api/v1/generate"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Custom Mode 페이로드
    payload = {
        "prompt": f"{keyword} upbeat band music with energetic guitar riffs, uplifting drums, positive vibes",
        "style": f"{keyword} rock band",
        "title": f"Happy {keyword.title()} Band Music",
        "customMode": True,
        "instrumental": True,
        "model": "V4",
        "callBackUrl": "https://api.example.com/callback"
    }
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(api_endpoint, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"] is not None and "taskId" in data["data"]:
                return data["data"]["taskId"]
            else:
                raise HTTPException(status_code=500, detail="태스크 ID를 받을 수 없습니다.")
        else:
            error_text = response.text
            raise HTTPException(status_code=response.status_code, detail=f"SUNO API 오류: {error_text}")

async def check_suno_task_and_download(task_id: str):
    """SUNO 태스크 상태 확인 및 BGM 다운로드"""
    api_key = os.getenv('SUNO_API_KEY')
    status_endpoint = f"https://api.sunoapi.org/api/v1/generate/record-info?taskId={task_id}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(status_endpoint, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"🔍 SUNO API 응답: {data}")
            
            if not data or "data" not in data or data["data"] is None:
                return {"success": False, "status": "pending", "message": "응답 데이터를 기다리는 중입니다..."}
            
            data_obj = data["data"]
            status = data_obj.get("status", "unknown")
            
            if "response" not in data_obj or data_obj["response"] is None:
                return {"success": False, "status": status, "message": "BGM 생성 중입니다..."}
            
            response_data = data_obj["response"]
            
            if "sunoData" not in response_data or response_data["sunoData"] is None:
                return {"success": False, "status": status, "message": "BGM 데이터를 기다리는 중입니다..."}
            
            suno_data = response_data["sunoData"]
            
            if status == "SUCCESS" and suno_data and len(suno_data) > 0:
                # 첫 번째 클립 다운로드 (두 개가 있을 경우 더 짧은 버전 선택)
                if len(suno_data) >= 2:
                    clip = suno_data[0] if suno_data[0].get('duration', 0) < suno_data[1].get('duration', 0) else suno_data[1]
                else:
                    clip = suno_data[0]
                
                audio_url = clip.get('audioUrl')
                
                if audio_url:
                    # BGM 다운로드
                    audio_response = await client.get(audio_url)
                    if audio_response.status_code == 200:
                        # 파일 저장
                        os.makedirs("static/audio", exist_ok=True)
                        bgm_filename = f"suno_bgm_{task_id[:8]}.mp3"
                        bgm_path = os.path.join("static/audio", bgm_filename)
                        
                        with open(bgm_path, "wb") as f:
                            f.write(audio_response.content)
                        
                        return {
                            "success": True,
                            "bgm_path": bgm_path,
                            "bgm_filename": bgm_filename,
                            "duration": clip.get('duration', 0),
                            "title": clip.get('title', ''),
                            "tags": clip.get('tags', '')
                        }
                    else:
                        raise HTTPException(status_code=500, detail="BGM 다운로드 실패")
                else:
                    raise HTTPException(status_code=500, detail="오디오 URL을 찾을 수 없습니다.")
            else:
                return {"success": False, "status": status, "message": "BGM 생성 중입니다..."}
                
        else:
            error_text = response.text
            raise HTTPException(status_code=response.status_code, detail=f"태스크 상태 확인 실패: {error_text}")

# FastAPI app 생성
app = FastAPI(title="Video Server", description="비디오 생성 및 합치기 서버")

# 정적 파일 서빙 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

def check_environment_variables():
    """필수 환경변수 체크"""
    required_vars = {
        "ELEVENLABS_API_KEY": "ElevenLabs TTS 서비스용",
        "OPENAI_API_KEY": "OpenAI LLM 서비스용", 
        "RUNWAY_API_KEY": "Runway 비디오 생성용",
        "SUNO_API_KEY": "SUNO 음성 생성용"
    }
    
    missing_vars = []
    for var_name, description in required_vars.items():
        if not os.getenv(var_name):
            missing_vars.append(f"{var_name} ({description})")
    
    if missing_vars:
        print("❌ 누락된 환경변수가 있습니다:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 .env 파일에 다음과 같이 설정해주세요:")
        for var_name in required_vars.keys():
            if not os.getenv(var_name):
                print(f"   {var_name}=your_api_key_here")
    else:
        print("✅ 모든 필수 환경변수가 설정되었습니다!")

# 서버 시작 시 환경변수 체크
check_environment_variables()

@app.get("/tts-selector", response_class=HTMLResponse)
async def tts_voice_selector():
    """TTS 음성 선택 웹 인터페이스"""
    try:
        with open("static/tts_voice_selector.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>TTS Voice Selector not found</h1>", 
            status_code=404
        )

@app.get("/video/status")
async def get_video_status():
    """비디오 기능 상태 확인"""
    return {
        "status": "active",
        "message": "비디오 합치기 및 트랜지션 기능이 활성화되었습니다.",
        "available_endpoints": {
            "GET /video/status": "현재 페이지 - 비디오 기능 상태 확인",
            "POST /video/generate-videos": "5단계: 4단계 이미지들 → Runway API 비디오 생성",
            "POST /video/merge-with-transitions": "6단계: 트랜지션 비디오 합치기",
            "POST /video/create-tts-from-storyboard": "7단계: 스토리보드 기반 TTS 생성",
            "POST /video/generate-subtitles": "8-1단계: TTS 오디오에서 자막 파일(.srt) 생성",
            "POST /video/generate-subtitles-synced": "8-1단계 개선: TTS 텍스트 기반 정확한 자막 생성 (싱크 완벽)",
            "POST /video/merge-with-tts-subtitles": "8-2단계: 비디오 + TTS + 자막 완전 합치기",
            "POST /video/merge-with-tts-subtitles-bgm": "🆕 8단계: 비디오 + TTS + 자막 + SUNO BGM 완전 합치기",
            "POST /bgm/generate": "🆕 SUNO BGM: 키워드 기반 밴드 BGM 생성",
            "GET /bgm/status/{task_id}": "🆕 SUNO BGM: 생성 상태 확인 및 다운로드",
        },
        "features": [
            "🎬 9가지 트랜지션 효과 (랜덤 선택)",
            "🚀 스트리밍 방식 처리 (다운로드 없음)",
            "📱 브라우저에서 바로 재생 가능",
            "🎨 Frame-level animation 지원",
            "🤖 AI 워크플로우 연동 (1-6단계)",
            "🎥 Runway API 비디오 생성 (이미지 → 비디오)",
            "🎙️ ElevenLabs TTS 음성 생성",
            "📝 Whisper 자동 자막 생성",
            "🎵 스토리보드 기반 내레이션 추가",
            "🧠 OpenAI LLM 기반 TTS 스크립트 자동 생성",
            "🔧 0.1초 정밀도 Whisper AI 자막",
            "🎤 간단한 텍스트 → TTS 변환",
            "🆕 Google LYRIA2 키워드 기반 1분 음성 생성"
        ]
    }

@app.post("/video/create-tts-from-storyboard")
async def create_tts_from_storyboard(request: dict):
    """7단계: 스토리보드 기반 TTS 생성"""
    try:
        print(f"🎙️ 7단계: OpenAI LLM 기반 TTS 내레이션 자동 생성 시작...")
        
        # 요청 데이터 추출
        persona_description = request.get("persona_description", "")
        marketing_insights = request.get("marketing_insights", "")
        ad_concept = request.get("ad_concept", "")
        storyboard_scenes = request.get("storyboard_scenes", [])
        voice_id = request.get("voice_id")
        voice_gender = request.get("voice_gender", "female")
        voice_language = request.get("voice_language", "ko")
        product_name = request.get("product_name", "상품")
        brand_name = request.get("brand_name", "브랜드")
        
        print(f"   페르소나: {persona_description[:50]}{'...' if len(persona_description) > 50 else ''}")
        print(f"   광고 컨셉: {ad_concept[:50]}{'...' if len(ad_concept) > 50 else ''}")
        print(f"   상품명: {product_name}")
        print(f"   브랜드명: {brand_name}")

        # OpenAI LLM으로 TTS 스크립트 자동 생성
        print(f"🤖 OpenAI GPT로 TTS 스크립트 자동 생성 중...")
        
        llm_prompt = f"""
당신은 짧은 영상 광고용 TTS 내레이션 전문가입니다. 
다음 정보를 바탕으로 매력적이고 설득력 있는 짧은 광고 내레이션 스크립트를 한국어로 작성해주세요.

**상품/브랜드 정보:**
- 상품명: {product_name}
- 브랜드명: {brand_name}

**타겟 고객 (페르소나):**
{persona_description if persona_description else "일반 소비자"}

**광고 컨셉:**
{ad_concept if ad_concept else "신뢰할 수 있는 브랜드"}

**중요한 제약사항:**
- 영상 길이: 5초 (매우 짧음)
- 각 TTS는 3-4초 미만이어야 함
- 각 문장은 40자 이내로 제한
- 총 3-4개의 매우 짧고 임팩트 있는 문장

**요구사항:**
1. 총 3-4개의 매우 짧은 문장 (각 문장은 3-4초 분량, 40자 이내)
2. 간결하고 임팩트 있는 톤
3. 제품의 핵심 가치를 한 줄로 표현

**출력 형식:**
각 문장을 번호와 함께 나열해주세요. 각 문장은 반드시 40자 이내여야 합니다.
예시:
1. {brand_name}의 {product_name}
2. 품질이 다릅니다
3. 지금 만나보세요

스크립트만 작성해주세요:
"""
        
        # OpenAI API 호출
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 광고 내레이션 전문가입니다. 매력적이고 설득력 있는 한국어 광고 스크립트를 작성합니다."
                },
                {
                    "role": "user",
                    "content": llm_prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        try:
            print("🌐 OpenAI API 호출 시작...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                print(f"📡 OpenAI 응답 상태: {response.status_code}")
                
                if response.status_code != 200:
                    error_text = response.text
                    print(f"❌ OpenAI API 오류 응답: {error_text}")
                    raise Exception(f"OpenAI API 요청 실패: {response.status_code} - {error_text}")
                
                response_data = response.json()
                generated_script = response_data["choices"][0]["message"]["content"]
                
                print(f"✅ OpenAI LLM 스크립트 생성 완료:")
                print(f"   생성된 스크립트:")
                print(f"   {'-'*50}")
                print(generated_script)
                print(f"   {'-'*50}")
                
        except Exception as llm_error:
            print(f"❌ OpenAI LLM 호출 실패: {llm_error}")
            # LLM 실패 시 기본 스크립트 생성
            generated_script = f"""1. {brand_name} {product_name}
2. 품질이 다릅니다
3. 특별한 가치를 제공
4. 지금 만나보세요"""
            print(f"🔄 기본 스크립트로 대체:")
            print(f"   {generated_script}")

        # 생성된 스크립트를 문장별로 파싱
        tts_scripts = []
        MAX_TTS_CHARS = 45
        
        # 번호로 시작하는 문장들 찾기
        numbered_sentences = re.findall(r'(\d+)\.\s*([^0-9]+?)(?=\d+\.|$)', generated_script, re.DOTALL)
        
        if numbered_sentences:
            for i, (number, text) in enumerate(numbered_sentences):
                clean_text = text.strip().replace('\n', ' ').replace('  ', ' ')
                if clean_text:
                    # 텍스트 길이 제한
                    if len(clean_text) > MAX_TTS_CHARS:
                        truncated_text = clean_text[:MAX_TTS_CHARS]
                        last_space = truncated_text.rfind(' ')
                        if last_space > MAX_TTS_CHARS - 10:
                            truncated_text = truncated_text[:last_space]
                        clean_text = truncated_text
                        print(f"   📏 텍스트 길이 제한: {len(clean_text)}자로 단축")
                    
                    tts_scripts.append({
                        "scene_number": int(number),
                        "script_type": "generated",
                        "text": clean_text,
                        "description": f"LLM 생성 스크립트 {number}",
                        "estimated_duration": min(len(clean_text) * 0.08, 3.8),
                        "char_count": len(clean_text)
                    })
        
        print(f"✅ 총 {len(tts_scripts)}개의 TTS 스크립트 생성 완료:")
        for script in tts_scripts:
            duration_est = script.get('estimated_duration', 3.0)
            char_count = script.get('char_count', 0)
            print(f"   - {script['description']}: {script['text'][:40]}... ({char_count}자, 예상 {duration_est:.1f}초)")

        # ElevenLabs TTS 변환
        print("🎤 TTS 변환 시작...")
        try:
            if TTS_AVAILABLE:
                script_texts = [script["text"] for script in tts_scripts]
                
                print(f"🎤 TTS 변환 프로세스:")
                print(f"   변환할 스크립트 수: {len(script_texts)}개")
                print(f"   사용할 음성 ID: {voice_id or '21m00Tcm4TlvDq8ikWAM'}")
                
                # 각 스크립트 내용 미리보기
                for i, text in enumerate(script_texts):
                    print(f"   스크립트 {i+1}: {text}")
                
                # TTS 오디오 생성
                api_key = get_elevenlabs_api_key()
                output_dir = os.path.abspath("static/audio")
                tts_results = await create_multiple_tts_audio(
                    text_list=script_texts,
                    voice_id=voice_id or '21m00Tcm4TlvDq8ikWAM',
                    api_key=api_key,
                    output_dir=output_dir
                )
                print(f"✅ TTS 변환 요청 완료, 결과 처리 중...")
            else:
                print("❌ TTS 모듈을 찾을 수 없습니다. 스크립트만 생성됩니다.")
                tts_results = []
            
        except Exception as tts_error:
            print(f"❌ TTS 변환 중 오류 발생: {tts_error}")
            tts_results = []

        # 결과 정리
        successful_tts = []
        failed_tts = []
        
        if tts_results:
            for i, (script, result) in enumerate(zip(tts_scripts, tts_results)):
                if result.success:
                    audio_filename = os.path.basename(result.audio_file_path)
                    audio_url = f"/static/audio/{audio_filename}"
                    
                    print(f"✅ TTS {i+1} 생성 완료: {audio_filename}")
                    
                    successful_tts.append({
                        "scene_number": script["scene_number"],
                        "script_type": script["script_type"],
                        "description": script["description"],
                        "text": script["text"],
                        "audio_url": audio_url,
                        "audio_file_path": result.audio_file_path,
                        "audio_filename": audio_filename,
                        "duration": result.duration,
                        "file_size": result.file_size
                    })
                else:
                    failed_tts.append({
                        "scene_number": script["scene_number"],
                        "script_type": script["script_type"],
                        "description": script["description"],
                        "text": script["text"],
                        "error": result.error
                    })
        else:
            # TTS 변환이 실행되지 않은 경우 스크립트만 반환
            for script in tts_scripts:
                successful_tts.append({
                    "scene_number": script["scene_number"],
                    "script_type": script["script_type"],
                    "description": script["description"],
                    "text": script["text"],
                    "audio_url": None,
                    "audio_file_path": None,
                    "note": "TTS 변환이 실행되지 않음"
                })
        
        print(f"✅ TTS 변환 완료: {len(successful_tts)}개 성공, {len(failed_tts)}개 실패")
        
        return {
            "step": "7단계_TTS_생성",
            "success": True,
            "message": f"OpenAI LLM으로 TTS 내레이션 자동 생성 완료! {len(successful_tts)}개 스크립트 생성",
            "generated_script": generated_script,
            "tts_scripts": tts_scripts,
            "successful_tts": successful_tts,
            "failed_tts": failed_tts,
            "summary": {
                "total_scripts": len(tts_scripts),
                "successful": len(successful_tts),
                "failed": len(failed_tts),
                "success_rate": f"{(len(successful_tts) / len(tts_scripts)) * 100:.1f}%" if tts_scripts else "0%"
            },
            "process_details": {
                "llm_script_generation": "✅ OpenAI로 대본 생성 완료",
                "tts_conversion": "✅ TTS 변환 시도" if tts_results else "⚠️ TTS 모듈 없음",
                "product_name": product_name,
                "brand_name": brand_name
            }
        }
        
    except Exception as e:
        print(f"❌ TTS 생성 중 오류 발생: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"7단계 TTS 생성 중 오류 발생: {str(e)}"
        )

@app.post("/video/generate-subtitles-synced")
async def generate_subtitles_from_tts_synced(request: dict):
    """8-1단계 개선: TTS 텍스트 기반 정확한 타이밍으로 자막 생성"""
    try:
        print(f"📝 8-1단계 (개선): TTS 텍스트 기반 정확한 자막 생성 시작...")
        
        # 요청 데이터 추출
        tts_audio_files = request.get("tts_audio_files", [])
        tts_texts = request.get("tts_texts", [])  # 원본 TTS 텍스트
        tts_durations = request.get("tts_durations", [])  # TTS 실제 길이
        
        # 입력 검증
        if not tts_audio_files:
            raise HTTPException(
                status_code=400, 
                detail="TTS 파일이 없습니다. 먼저 7단계에서 TTS를 생성해주세요."
            )
        
        print(f"📝 정확한 자막 생성 프로세스 시작:")
        print(f"   처리할 오디오 파일 수: {len(tts_audio_files)}개")
        print(f"   원본 텍스트 수: {len(tts_texts)}개")
        print(f"   오디오 길이 정보: {len(tts_durations)}개")
        
        # 자막 디렉토리 생성
        os.makedirs("./static/subtitles", exist_ok=True)
        
        subtitle_results = []
        cumulative_time = 0.0  # 누적 시간
        
        for i, audio_file in enumerate(tts_audio_files):
            audio_filename = os.path.basename(audio_file)
            print(f"📝 [{i+1}/{len(tts_audio_files)}] 정확한 자막 생성 중: {audio_filename}")
            
            try:
                # TTS 파일명을 기반으로 .srt 파일명 생성
                base_name = os.path.splitext(audio_filename)[0]
                subtitle_filename = f"{base_name}_synced.srt"
                subtitle_path = os.path.join("./static/subtitles", subtitle_filename)
                
                # 원본 텍스트와 길이 정보가 있으면 사용
                if i < len(tts_texts) and i < len(tts_durations):
                    original_text = tts_texts[i]
                    audio_duration = tts_durations[i]
                    
                    print(f"   📋 원본 텍스트: {original_text}")
                    print(f"   ⏱️ 오디오 길이: {audio_duration}초")
                    
                    # 정확한 타이밍으로 SRT 생성
                    start_time = cumulative_time
                    end_time = cumulative_time + audio_duration
                    
                    # SRT 포맷으로 자막 생성
                    srt_content = create_srt_content(
                        sequence_number=i + 1,
                        start_time=start_time,
                        end_time=end_time,
                        text=original_text
                    )
                    
                    # SRT 파일 저장
                    with open(subtitle_path, 'w', encoding='utf-8') as f:
                        f.write(srt_content)
                    
                    subtitle_results.append({
                        "audio_file": audio_file,
                        "subtitle_file": subtitle_path,
                        "subtitle_filename": subtitle_filename,
                        "original_text": original_text,
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": audio_duration,
                        "method": "text_based_timing",
                        "status": "success"
                    })
                    
                    cumulative_time = end_time
                    print(f"   ✅ 정확한 자막 생성 성공: {subtitle_filename} ({start_time:.1f}s - {end_time:.1f}s)")
                    
                else:
                    # 원본 정보가 없으면 Whisper STT 사용 (기존 방식)
                    print(f"   ⚠️ 원본 텍스트/길이 정보 없음, Whisper STT 사용")
                    
                    if SUBTITLE_AVAILABLE:
                        try:
                            from subtitle_utils import transcribe_audio_with_whisper
                            subtitle_result = await transcribe_audio_with_whisper(
                                audio_file_path=audio_file,
                                language="ko",
                                output_format="srt"
                            )
                        except ImportError:
                            print("   ❌ subtitle_utils 모듈 import 실패")
                            subtitle_result = None
                        
                        if subtitle_result and "subtitle_file" in subtitle_result:
                            subtitle_results.append({
                                "audio_file": audio_file,
                                "subtitle_file": subtitle_result["subtitle_file"],
                                "subtitle_filename": subtitle_filename,
                                "method": "whisper_stt",
                                "status": "success"
                            })
                            print(f"   ✅ Whisper 자막 생성 성공: {subtitle_filename}")
                        else:
                            subtitle_results.append({
                                "audio_file": audio_file,
                                "subtitle_filename": subtitle_filename,
                                "error": "Whisper 자막 생성 실패",
                                "method": "whisper_stt",
                                "status": "failed"
                            })
                    else:
                        subtitle_results.append({
                            "audio_file": audio_file,
                            "subtitle_filename": subtitle_filename,
                            "error": "subtitle_utils 모듈 없음",
                            "method": "none",
                            "status": "failed"
                        })
                        
            except Exception as e:
                subtitle_results.append({
                    "audio_file": audio_file,
                    "subtitle_filename": f"{os.path.splitext(audio_filename)[0]}_synced.srt",
                    "error": str(e),
                    "status": "failed"
                })
                print(f"   ❌ 자막 생성 중 오류: {e}")
        
        # 성공/실패 통계
        successful_subtitles = [r for r in subtitle_results if r.get("status") == "success"]
        failed_subtitles = [r for r in subtitle_results if r.get("status") == "failed"]
        
        print(f"✅ 정확한 자막 생성 완료:")
        print(f"   성공: {len(successful_subtitles)}개")
        print(f"   실패: {len(failed_subtitles)}개")
        print(f"   성공률: {(len(successful_subtitles) / len(tts_audio_files)) * 100:.1f}%")
        
        return {
            "step": "8-1단계_정확한_자막_생성",
            "success": True,
            "message": f"TTS 텍스트 기반 정확한 자막 생성 완료! {len(successful_subtitles)}개 .srt 파일 생성",
            "subtitle_results": subtitle_results,
            "successful_subtitles": successful_subtitles,
            "failed_subtitles": failed_subtitles,
            "total_duration": cumulative_time,
            "summary": {
                "total_files": len(tts_audio_files),
                "successful": len(successful_subtitles),
                "failed": len(failed_subtitles),
                "success_rate": f"{(len(successful_subtitles) / len(tts_audio_files)) * 100:.1f}%" if tts_audio_files else "0%"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 정확한 자막 생성 중 오류 발생: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"8-1단계 정확한 자막 생성 중 오류 발생: {str(e)}"
        )

def _create_srt_content(self, sequence_number: int, start_time: float, end_time: float, text: str) -> str:
    """SRT 포맷으로 자막 내용 생성"""
    def seconds_to_srt_time(seconds: float) -> str:
        """초를 SRT 시간 포맷(HH:MM:SS,mmm)으로 변환"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    start_srt = seconds_to_srt_time(start_time)
    end_srt = seconds_to_srt_time(end_time)
    
    return f"""{sequence_number}
{start_srt} --> {end_srt}
{text}

"""

def create_srt_content(sequence_number: int, start_time: float, end_time: float, text: str) -> str:
    """SRT 포맷으로 자막 내용 생성"""
    def seconds_to_srt_time(seconds: float) -> str:
        """초를 SRT 시간 포맷(HH:MM:SS,mmm)으로 변환"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    start_srt = seconds_to_srt_time(start_time)
    end_srt = seconds_to_srt_time(end_time)
    
    return f"""{sequence_number}
{start_srt} --> {end_srt}
{text}

"""
async def generate_videos():
    """5단계: 4단계에서 생성된 이미지들을 비디오로 변환"""
    
    # client.py의 current_project에서 4단계 이미지들 가져오기
    try:
        from client import current_project
        
        if not current_project.get("images"):
            raise HTTPException(
                status_code=400,
                detail="4단계에서 생성된 이미지가 없습니다. 먼저 4단계를 완료해주세요."
            )
        
        # 4단계에서 생성된 이미지 URL들 추출
        image_data_list = current_project["images"]
        image_urls = []
        
        print(f"🔧 current_project['images'] 내용: {len(image_data_list)}개")
        
        for i, img_data in enumerate(image_data_list):
            print(f"🔧 이미지 {i+1} 데이터: {type(img_data)} - {str(img_data)[:100]}...")
            
            # 다양한 형태의 이미지 데이터 처리
            if isinstance(img_data, dict):
                if img_data.get("url"):
                    image_urls.append(img_data["url"])
                elif img_data.get("image_url"):
                    image_urls.append(img_data["image_url"])
                elif img_data.get("generated_image_url"):
                    image_urls.append(img_data["generated_image_url"])
            elif isinstance(img_data, str):
                image_urls.append(img_data)
        
        if not image_urls:
            print(f"❌ 추출된 URL이 없습니다.")
            raise HTTPException(
                status_code=400,
                detail="4단계 이미지 데이터에서 유효한 URL을 찾을 수 없습니다."
            )
        
        print(f"✅ 4단계에서 가져온 이미지: {len(image_urls)}개")
        
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="client.py를 찾을 수 없습니다. 워크플로우를 먼저 실행해주세요."
        )
    
    print("🎬 5단계: 4단계 이미지들 → 비디오 변환 시작...")
    
    # video_models.py 설정 사용
    from video_models import ImageToVideoRequest, VideoGenerationResult
    
    video_request = ImageToVideoRequest(
        image_urls=image_urls,
        duration_per_scene=5,
        resolution="720:1280",
        model="gen4_turbo"
    )
    
    print(f"🎬 Runway API 설정:")
    print(f"   - 모델: {video_request.model}")
    print(f"   - 해상도: {video_request.resolution}")
    print(f"   - 장면당 길이: {video_request.duration_per_scene}초")
    
    # Runway API를 통한 이미지 → 동영상 변환
    generated_videos = []
    
    try:
        runway_api_key = os.getenv("RUNWAY_API_KEY")
        
        if not runway_api_key:
            raise HTTPException(
                status_code=500,
                detail="RUNWAY_API_KEY 환경 변수가 설정되지 않았습니다."
            )
        
        print("🚀 Runway API를 통한 이미지 → 동영상 변환 시작...")
        
        headers = {
            "Authorization": f"Bearer {runway_api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06"
        }
        
        base_url = "https://api.dev.runwayml.com/v1"
        
        async with httpx.AsyncClient(timeout=300) as client:
            for i, image_url in enumerate(image_urls, 1):
                print(f"\n🎬 [{i}/{len(image_urls)}] 이미지 → 동영상 변환 중...")
                print(f"   🖼️ 소스 이미지: {image_url}")
                
                payload = {
                    "model": video_request.model,
                    "promptImage": image_url,
                    "duration": video_request.duration_per_scene,
                    "ratio": video_request.resolution,
                    "seed": 42
                }
                
                try:
                    # 동영상 생성 작업 요청
                    print(f"📤 Runway API 요청: 이미지 → 동영상 변환...")
                    response = await client.post(f"{base_url}/image_to_video", headers=headers, json=payload)
                    
                    if response.status_code != 200:
                        raise Exception(f"API 요청 실패: {response.text}")
                    
                    task_id = response.json()["id"]
                    print(f"  -> 작업 ID: {task_id}")

                    # 작업 완료까지 폴링
                    for attempt in range(60):
                        await asyncio.sleep(5)
                        
                        status_response = await client.get(f"{base_url}/tasks/{task_id}", headers=headers)
                        status_data = status_response.json()
                        
                        if status_data["status"] == "SUCCEEDED":
                            video_url = status_data["output"][0]
                            print(f"  ✅ 동영상 생성 완료: {video_url}")
                            
                            result = VideoGenerationResult(
                                scene_number=i,
                                status="success",
                                video_url=video_url,
                                duration=video_request.duration_per_scene,
                                resolution=video_request.resolution
                            )
                            generated_videos.append(result.model_dump())
                            break
                        elif status_data["status"] == "FAILED":
                            print(f"  ❌ 동영상 생성 실패: {status_data.get('failure')}")
                            result = VideoGenerationResult(
                                scene_number=i,
                                status="error",
                                error=f"생성 실패: {status_data.get('failure')}",
                                duration=video_request.duration_per_scene,
                                resolution=video_request.resolution
                            )
                            generated_videos.append(result.model_dump())
                            break
                        else:
                            print(f"  ⏳ 작업 진행 중... ({attempt + 1}/60) 상태: {status_data['status']}")
                
                except Exception as video_error:
                    print(f"  ❌ 장면 {i} 처리 중 오류: {video_error}")
                    result = VideoGenerationResult(
                        scene_number=i,
                        status="error",
                        error=str(video_error),
                        duration=video_request.duration_per_scene,
                        resolution=video_request.resolution
                    )
                    generated_videos.append(result.model_dump())
    
    except Exception as api_error:
        print(f"⚠️ Runway API 호출 실패: {api_error}")
        raise HTTPException(
            status_code=500,
            detail=f"Runway API 호출 실패: {str(api_error)}"
        )
    
    # 결과 통계 계산
    successful_count = sum(1 for v in generated_videos if v.get('status') == 'success')
    failed_count = len(generated_videos) - successful_count
    success_rate = f"{(successful_count / len(generated_videos)) * 100:.1f}%" if generated_videos else "0%"
    
    # 5단계 결과를 current_project에 저장
    try:
        from client import current_project
        current_project["generated_videos"] = generated_videos
        print(f"✅ 5단계 결과를 current_project에 저장했습니다. ({successful_count}개 성공)")
    except Exception as save_error:
        print(f"⚠️ current_project 저장 실패: {save_error}")
    
    return {
        "message": "이미지 → 비디오 변환이 완료되었습니다.",
        "generated_videos": generated_videos,
        "summary": {
            "total_scenes": len(generated_videos),
            "successful": successful_count,
            "failed": failed_count,
            "success_rate": success_rate
        }
    }

@app.post("/video/merge-with-transitions")
async def merge_videos_with_transitions():
    """6단계: 5단계에서 생성된 영상들을 랜덤 트랜지션으로 합치기"""
    
    # 예시 영상 URL들 (5단계 영상이 없을 때 사용)
    example_video_urls = []
    
    # client.py의 현재 프로젝트 상태에서 생성된 영상 정보 가져오기
    video_urls = []
    use_example_videos = False
    
    try:
        from client import current_project
        
        if not current_project.get("generated_videos"):
            print("⚠️ 5단계에서 생성된 영상이 없습니다. 예시 영상을 사용합니다.")
            video_urls = example_video_urls
            use_example_videos = True
        else:
            print("📋 6단계: 5단계에서 생성된 영상들을 확인합니다...")
            
            # 생성된 영상 URL들 추출
            generated_videos = current_project["generated_videos"]
            
            # 성공적으로 생성된 영상 URL들만 추출
            for video in generated_videos:
                if video.get("status") == "success" and video.get("video_url"):
                    video_urls.append(video["video_url"])
            
            if not video_urls:
                print("⚠️ 5단계에서 생성된 유효한 영상이 없습니다. 예시 영상을 사용합니다.")
                video_urls = example_video_urls
                use_example_videos = True
        
        if use_example_videos:
            print(f"🎬 예시 영상 {len(video_urls)}개를 랜덤 트랜지션으로 합칩니다...")
        else:
            print(f"🎬 총 {len(video_urls)}개 실제 생성 영상을 랜덤 트랜지션으로 합칩니다...")
            
            # 실제 영상 URL들 출력
            for i, url in enumerate(video_urls, 1):
                print(f"   영상 {i}: {url}")
        
        # 실제 영상 URL들을 사용한 트랜지션 합치기
        merger = create_merger_instance(use_static_dir=True)
        output_filename = generate_output_filename("merged_ai_videos")
        
        video_source = "예시 영상" if use_example_videos else "실제 생성된 영상"
        print(f"🚀 {video_source} URL들로 트랜지션 합치기 시작...")
        final_video_path = merger.merge_videos_with_frame_transitions(
            video_urls,
            output_filename
        )
        video_url = merger.get_video_url(output_filename)
        
        print(f"🎉 6단계 완료: 영상이 성공적으로 합쳐졌습니다!")
        print(f"📱 브라우저에서 확인: {video_url}")
        
        # 6단계 완료 후 합쳐진 영상 파일명을 TXT 파일로 저장
        print(f"📝 6단계 완료된 영상 파일명 저장 중...")
        merged_video_list_file = "merged_video_list.txt"
        try:
            if final_video_path:
                if os.path.isabs(final_video_path):
                    actual_video_path = final_video_path
                else:
                    actual_video_path = os.path.abspath(final_video_path)
            else:
                actual_video_path = os.path.abspath(os.path.join("static", "videos", output_filename))
            
            with open(merged_video_list_file, 'w', encoding='utf-8') as f:
                f.write(actual_video_path + '\n')
            
            print(f"✅ 6단계 영상 파일명 저장 성공!")
            print(f"   파일 위치: {os.path.abspath(merged_video_list_file)}")
            print(f"   저장된 영상: {actual_video_path}")
            
        except Exception as e:
            print(f"❌ 6단계 영상 파일명 저장 실패: {e}")
        
        return {
            "step": "6단계_영상_합치기",
            "status": "success",
            "message": f"{video_source}이 랜덤 트랜지션으로 성공적으로 합쳐졌습니다.",
            "video_source": video_source,
            "input_videos": len(video_urls),
            "transitions_used": "random_transitions",
            "output_file": output_filename,
            "url": video_url,
            "duration": "estimated_duration",
            "workflow_complete": True,
            "used_example_videos": use_example_videos
        }
        
    except ImportError:
        print("⚠️ client.py를 찾을 수 없습니다. 예시 영상을 사용합니다.")
        video_urls = example_video_urls
        use_example_videos = True
        
        # 예시 영상들을 사용한 트랜지션 합치기 (동일한 로직)
        merger = create_merger_instance(use_static_dir=True)
        output_filename = generate_output_filename("merged_example_videos")
        
        print("🚀 예시 영상 URL들로 트랜지션 합치기 시작...")
        final_video_path = merger.merge_videos_with_frame_transitions(
            video_urls,
            output_filename
        )
        video_url = merger.get_video_url(output_filename)
        
        print(f"🎉 6단계 완료: 예시 영상이 성공적으로 합쳐졌습니다!")
        
        return {
            "step": "6단계_영상_합치기",
            "status": "success",
            "message": "예시 영상이 랜덤 트랜지션으로 성공적으로 합쳐졌습니다.",
            "video_source": "예시 영상",
            "input_videos": len(video_urls),
            "transitions_used": "random_transitions",
            "output_file": output_filename,
            "url": video_url,
            "duration": "estimated_duration",
            "workflow_complete": True,
            "used_example_videos": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"6단계 영상 합치기 중 오류 발생: {str(e)}"
        )

# 8단계: TTS + 자막 + BGM 완전 합치기 엔드포인트
@app.post("/video/merge-with-tts-subtitles-bgm")
async def merge_video_with_tts_subtitles_and_bgm(
    video_urls: List[str],
    tts_scripts: List[str],
    transition_type: str = "fade",
    voice_id: Optional[str] = None,
    tts_volume: float = 0.8,
    video_volume: float = 0.3,
    bgm_volume: float = 0.15,
    bgm_file: Optional[str] = None,
    bgm_keyword: str = "happy"
):
    """
    8단계: 비디오 + TTS + 자막 + SUNO BGM 완전 합치기
    - SUNO BGM이 지정되지 않으면 키워드로 자동 생성
    - BGM이 영상보다 길면 영상 길이에 맞춰 자동으로 자름
    """
    try:
        print(f"🎬 8단계: TTS + 자막 + BGM 완전 합치기 시작...")
        print(f"   비디오: {len(video_urls)}개")
        print(f"   TTS 스크립트: {len(tts_scripts)}개")
        print(f"   BGM 키워드: {bgm_keyword}")
        
        if not SUBTITLE_AVAILABLE:
            raise HTTPException(
                status_code=500,
                detail="자막 모듈이 사용할 수 없습니다."
            )
        
        # BGM 파일 처리
        selected_bgm_file = bgm_file
        
        # BGM 파일이 지정되지 않았으면 SUNO API로 생성
        if not selected_bgm_file:
            print(f"🎵 SUNO BGM 생성 중... (키워드: {bgm_keyword})")
            
            # SUNO BGM 생성 요청 (최대 70초)
            task_id = await generate_suno_bgm(bgm_keyword, 70)
            print(f"   태스크 ID: {task_id}")
            print(f"   최대 길이: 70초")
            
            # BGM 생성 완료까지 대기 (최대 3분)
            max_wait_time = 180  # 3분
            wait_interval = 15   # 15초마다 확인
            waited_time = 0
            
            while waited_time < max_wait_time:
                print(f"   ⏰ BGM 생성 확인 중... ({waited_time}초 경과)")
                
                try:
                    result = await check_suno_task_and_download(task_id)
                    if result["success"]:
                        selected_bgm_file = result["bgm_path"]
                        print(f"   ✅ BGM 생성 완료: {result['bgm_filename']}")
                        break
                    else:
                        print(f"   ⏳ BGM 생성 중... ({result.get('message', 'Processing')})")
                except Exception as e:
                    print(f"   ⚠️ BGM 확인 중 오류: {e}")
                
                await asyncio.sleep(wait_interval)
                waited_time += wait_interval
            
            if not selected_bgm_file:
                print(f"   ⚠️ BGM 생성 시간 초과. 기본 BGM 사용.")
                # 기본 BGM 폴더에서 랜덤 선택하도록 None으로 설정
                selected_bgm_file = None
        
        # TTS + 자막 + BGM 합치기
        result = await merge_video_with_tts_and_subtitles(
            video_urls=video_urls,
            tts_scripts=tts_scripts,
            transition_type=transition_type,
            voice_id=voice_id,
            tts_volume=tts_volume,
            video_volume=video_volume,
            add_subtitles=True,
            enable_bgm=True,
            bgm_volume=bgm_volume,
            bgm_file=selected_bgm_file
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "8단계: TTS + 자막 + BGM 합치기 완료",
                "output_file": result["output_file"],
                "video_url": f"http://localhost:8001/static/videos/{os.path.basename(result['output_file'])}",
                "duration": result.get("duration", 0),
                "tts_files": result.get("tts_files", []),
                "subtitle_info": result.get("subtitle_info", {}),
                "bgm_info": {
                    "bgm_file": selected_bgm_file,
                    "bgm_keyword": bgm_keyword,
                    "bgm_volume": bgm_volume
                },
                "processing_details": {
                    "video_count": len(video_urls),
                    "tts_count": len(tts_scripts),
                    "transition_type": transition_type,
                    "voice_id": voice_id
                }
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"TTS + 자막 + BGM 합치기 실패: {result.get('error', '알 수 없는 오류')}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 8단계 TTS + 자막 + BGM 합치기 오류: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"8단계 TTS + 자막 + BGM 합치기 중 오류 발생: {str(e)}"
        )

# SUNO BGM 생성 엔드포인트들
@app.post("/bgm/generate")
async def generate_bgm_endpoint(
    keyword: str = "happy",
    duration: int = 70
):
    """
    SUNO API를 사용한 BGM 생성 (최대 70초)
    """
    try:
        # 최대 70초로 제한
        if duration > 70:
            duration = 70
            print(f"⚠️ BGM 길이가 70초로 제한됩니다.")
        
        print(f"🎵 SUNO BGM 생성 시작: 키워드='{keyword}', 길이={duration}초")
        
        if not os.getenv('SUNO_API_KEY'):
            raise HTTPException(status_code=500, detail="SUNO_API_KEY가 설정되지 않았습니다.")
        
        # SUNO BGM 생성 요청
        task_id = await generate_suno_bgm(keyword, duration)
        
        return {
            "success": True,
            "message": f"SUNO BGM 생성 요청 성공",
            "task_id": task_id,
            "keyword": keyword,
            "duration": duration,
            "max_duration": 70,
            "estimated_time": "2-3분",
            "status_check_url": f"/bgm/status/{task_id}",
            "note": "생성 완료까지 2-3분 소요됩니다. BGM은 최대 70초로 제한됩니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ BGM 생성 오류: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"BGM 생성 중 오류 발생: {str(e)}"
        )

@app.get("/bgm/status/{task_id}")
async def check_bgm_status(task_id: str):
    """
    SUNO BGM 생성 상태 확인 및 다운로드
    """
    try:
        print(f"🔍 SUNO BGM 상태 확인: {task_id}")
        
        if not os.getenv('SUNO_API_KEY'):
            raise HTTPException(status_code=500, detail="SUNO_API_KEY가 설정되지 않았습니다.")
        
        # 태스크 상태 확인 및 다운로드
        result = await check_suno_task_and_download(task_id)
        
        if result["success"]:
            return {
                "success": True,
                "status": "completed",
                "message": "BGM 생성 완료 및 다운로드 성공",
                "task_id": task_id,
                "bgm_file": result["bgm_filename"],
                "bgm_url": f"http://localhost:8001/static/audio/{result['bgm_filename']}",
                "duration": result["duration"],
                "title": result["title"],
                "tags": result["tags"],
                "file_path": result["bgm_path"]
            }
        else:
            return {
                "success": False,
                "status": result.get("status", "processing"),
                "message": result.get("message", "BGM 생성 중입니다..."),
                "task_id": task_id,
                "retry_after": 30
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ BGM 상태 확인 오류: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"BGM 상태 확인 중 오류 발생: {str(e)}"
        )

def start_video_server():
    """비디오 서버 시작 함수"""
    print("🚀 비디오 서버를 시작합니다...")
    print("📡 서버 정보:")
    print("   - 호스트: 0.0.0.0")
    print("   - 포트: 8001")
    print("   - 모드: 프로덕션")
    print("📱 브라우저에서 http://localhost:8001/video/status 에 접속하여 상태를 확인하세요.")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    start_video_server()
