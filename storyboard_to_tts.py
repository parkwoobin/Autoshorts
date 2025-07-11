"""
스토리보드 기반 OpenAI LLM TTS 대본 생성 및 음성 변환
"""
from dotenv import load_dotenv
load_dotenv()
import os
import json
import asyncio
import httpx
import random
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime

@dataclass
class StoryboardScene:
    """스토리보드 장면 데이터 클래스"""
    scene_number: int
    description: str
    image_prompt: str
    duration: float = 5.0
    emotion: str = "neutral"
    action: str = ""

@dataclass
class TTSScript:
    """TTS 스크립트 데이터 클래스"""
    scene_number: int
    text: str
    duration: float
    emotion: str
    voice_style: str = "natural"

@dataclass
class TTSResult:
    """TTS 생성 결과 데이터 클래스"""
    success: bool
    audio_file_path: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None
    error: Optional[str] = None

class StoryboardToTTSGenerator:
    """스토리보드 → OpenAI LLM → TTS 변환기"""
    
    # ElevenLabs 사용 가능한 음성 ID 리스트
    VOICE_IDS = [
        "21m00Tcm4TlvDq8ikWAM",  # Rachel (영어, 여성)
        "AZnzlk1XvdvUeBnXmlld",  # Domi (영어, 여성)
        "EXAVITQu4vr4xnSDxMaL",  # Bella (영어, 여성)
        "ErXwobaYiN019PkySvjV",  # Antoni (영어, 남성)
        "MF3mGyEYCl7XYWbV9V6O",  # Elli (영어, 여성)
        "TxGEqnHWrfWFTfGW9XjX",  # Josh (영어, 남성)
        "VR6AewLTigWG4xSOukaG",  # Arnold (영어, 남성)
        "pNInz6obpgDQGcFmaJgB",  # Adam (영어, 남성)
        "yoZ06aMxZJJ28mfd3POQ",  # Sam (영어, 남성)
        "29vD33N1CtxCmqQRPOHJ",  # Drew (영어, 남성)
        "IKne3meq5aSn9XLyUdCD",  # Bill (영어, 남성)
        "JBFqnCBsd6RMkjVDRZzb",  # George (영어, 남성)
    ]
    
    def __init__(self):
        """초기화: API 키 확인"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        
        if not self.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY 환경변수가 설정되지 않았습니다.")
    
    @classmethod
    def get_random_voice_id(cls) -> str:
        """랜덤 음성 ID 선택"""
        return random.choice(cls.VOICE_IDS)
    
    def parse_storyboard_data(self, storyboard_data: Dict) -> List[StoryboardScene]:
        """스토리보드 데이터를 파싱하여 StoryboardScene 객체 리스트로 변환"""
        scenes = []
        
        # 다양한 스토리보드 데이터 형식 지원
        if isinstance(storyboard_data, dict):
            # 형식 1: {"scenes": [...]} 또는 {"storyboard_scenes": [...]}
            scene_list = (storyboard_data.get("scenes") or 
                         storyboard_data.get("storyboard_scenes") or 
                         storyboard_data.get("images") or [])
            
            # 형식 2: 직접 장면 정보가 포함된 경우
            if not scene_list and "scene_number" in storyboard_data:
                scene_list = [storyboard_data]
        
        elif isinstance(storyboard_data, list):
            # 형식 3: 직접 리스트로 제공된 경우
            scene_list = storyboard_data
        
        else:
            raise ValueError("지원하지 않는 스토리보드 데이터 형식입니다.")
        
        for i, scene_data in enumerate(scene_list):
            if isinstance(scene_data, dict):
                scene = StoryboardScene(
                    scene_number=scene_data.get("scene_number", i + 1),
                    description=scene_data.get("description", scene_data.get("prompt", "")),
                    image_prompt=scene_data.get("image_prompt", scene_data.get("prompt", "")),
                    duration=float(scene_data.get("duration", 5.0)),
                    emotion=scene_data.get("emotion", "neutral"),
                    action=scene_data.get("action", "")
                )
                scenes.append(scene)
            elif isinstance(scene_data, str):
                # 문자열인 경우 description으로 사용
                scene = StoryboardScene(
                    scene_number=i + 1,
                    description=scene_data,
                    image_prompt=scene_data,
                    duration=5.0
                )
                scenes.append(scene)
        
        print(f"✅ 스토리보드 파싱 완료: {len(scenes)}개 장면")
        return scenes
    
    async def generate_tts_script_with_llm(
        self, 
        scenes: List[StoryboardScene],
        product_name: str = "상품",
        brand_name: str = "브랜드",
        target_audience: Union[str, Dict, List] = "일반 소비자",
        ad_concept: Union[str, Dict, List] = "매력적인 광고",
        script_style: Union[str, Dict, List] = "친근하고 자연스러운"
    ) -> List[TTSScript]:
        """OpenAI LLM을 사용하여 스토리보드에서 TTS 스크립트 생성"""
        
        print(f"🤖 OpenAI LLM으로 TTS 스크립트 생성 시작...")
        print(f"   장면 수: {len(scenes)}개")
        print(f"   상품명: {product_name}")
        print(f"   브랜드명: {brand_name}")
        
        # 구조화된 데이터를 JSON 형태로 프롬프트에 포함
        import json
        
        # 1~4단계 정보를 JSON으로 변환 (구조화된 데이터인 경우 그대로, 문자열인 경우도 처리)
        if isinstance(target_audience, (dict, list)):
            persona_json = json.dumps(target_audience, ensure_ascii=False, indent=2)
        else:
            persona_json = f'"{target_audience}"'
        
        if isinstance(ad_concept, (dict, list)):
            insight_json = json.dumps(ad_concept, ensure_ascii=False, indent=2)
        else:
            insight_json = f'"{ad_concept}"'
        
        if isinstance(script_style, (dict, list)):
            concept_json = json.dumps(script_style, ensure_ascii=False, indent=2)
        else:
            concept_json = f'"{script_style}"'
        
        storyboard_json = json.dumps([scene.__dict__ for scene in scenes], ensure_ascii=False, indent=2)
        
        # LLM 프롬프트 구성
        llm_prompt = f"""
당신은 광고 영상용 TTS 내레이션 전문 작가입니다.
아래 1~4단계 정보를 모두 반영하여, 각 장면에 맞는 매력적이고 설득력 있는 TTS 대본을 한국어로 작성해주세요.

1단계: 타겟 고객(페르소나)
{persona_json}

2단계: 마케팅 인사이트
{insight_json}

3단계: 광고 컨셉
{concept_json}

4단계: 스토리보드 장면 정보
{storyboard_json}

**상품/브랜드 정보:**
상품명: {product_name}
브랜드명: {brand_name}

**작성 요구사항:**
1. 각 장면별로 타겟 고객의 특징, 니즈, 상황, 감정, 라이프스타일을 적극적으로 반영할 것
2. 마케팅 인사이트와 광고 컨셉을 반드시 녹여서 설득력 있게 표현할 것
3. 스토리보드의 장면 설명과 액션, 감정 정보를 대본에 반영할 것
4. 자연스럽고 듣기 좋은 문장 구성
5. 각 스크립트는 해당 장면 길이에 맞게 조절
6. 상품/브랜드명을 자연스럽게 포함
7. 전체적으로 일관된 스토리 흐름 유지

**출력 형식:**
각 장면별로 다음과 같이 작성해주세요:

장면 1: [스크립트 내용]
장면 2: [스크립트 내용]
...

예시:
장면 1: 안녕하세요, {brand_name}와 함께하는 특별한 순간입니다.
장면 2: {product_name}로 여러분의 일상이 더욱 풍요로워집니다.

스크립트만 작성해주세요:
"""
        
        # OpenAI API 호출
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 광고 내레이션 전문 작가입니다. 스토리보드에 맞는 매력적이고 자연스러운 한국어 TTS 스크립트를 작성합니다."
                },
                {
                    "role": "user", 
                    "content": llm_prompt
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.7
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    raise Exception(f"OpenAI API 요청 실패: {response.status_code} - {response.text}")
                
                response_data = response.json()
                generated_script = response_data["choices"][0]["message"]["content"]
                
                print(f"✅ OpenAI LLM 스크립트 생성 완료 ({len(generated_script)}자)")
                
        except Exception as llm_error:
            print(f"⚠️ OpenAI LLM 호출 실패: {llm_error}")
            # LLM 실패 시 기본 스크립트 생성
            generated_script = self._generate_fallback_script(scenes, product_name, brand_name)
            print(f"🔄 기본 스크립트로 대체")
        
        # 생성된 스크립트를 장면별로 파싱
        tts_scripts = self._parse_generated_script(generated_script, scenes)
        
        print(f"✅ 총 {len(tts_scripts)}개의 TTS 스크립트 생성 완료")
        return tts_scripts
    
    def _generate_fallback_script(self, scenes: List[StoryboardScene], product_name: str, brand_name: str) -> str:
        """LLM 실패 시 사용할 기본 스크립트 생성"""
        fallback_scripts = []
        
        for i, scene in enumerate(scenes, 1):
            if i == 1:
                script = f"안녕하세요, {brand_name}와 함께합니다."
            elif i == len(scenes):
                script = f"지금 바로 {product_name}를 만나보세요."
            else:
                script = f"{product_name}와 함께하는 특별한 순간입니다."
            
            fallback_scripts.append(f"장면 {i}: {script}")
        
        return "\n".join(fallback_scripts)
    
    def _parse_generated_script(self, generated_script: str, scenes: List[StoryboardScene]) -> List[TTSScript]:
        """생성된 스크립트를 장면별로 파싱"""
        tts_scripts = []
        
        # "장면 X:" 패턴으로 스크립트 분할
        import re
        scene_pattern = r'장면\s*(\d+)\s*:\s*([^\n장]+)'
        matches = re.findall(scene_pattern, generated_script)
        
        if matches:
            for scene_num_str, script_text in matches:
                scene_num = int(scene_num_str)
                clean_text = script_text.strip()
                
                # 해당 장면 정보 찾기
                scene_info = None
                for scene in scenes:
                    if scene.scene_number == scene_num:
                        scene_info = scene
                        break
                
                if scene_info and clean_text:
                    tts_script = TTSScript(
                        scene_number=scene_num,
                        text=clean_text,
                        duration=scene_info.duration,
                        emotion=scene_info.emotion,
                        voice_style="natural"
                    )
                    tts_scripts.append(tts_script)
        
        # 파싱이 실패하거나 부족한 경우 문장 단위로 분할
        if len(tts_scripts) < len(scenes):
            print(f"⚠️ 스크립트 파싱 부족 ({len(tts_scripts)}/{len(scenes)}), 문장 단위로 재분할")
            tts_scripts = self._split_by_sentences(generated_script, scenes)
        
        return tts_scripts
    
    def _split_by_sentences(self, text: str, scenes: List[StoryboardScene]) -> List[TTSScript]:
        """문장 단위로 스크립트 분할"""
        # 문장 분할
        import re
        sentences = re.split(r'[.!?]\s+', text)
        clean_sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
        
        tts_scripts = []
        for i, scene in enumerate(scenes):
            if i < len(clean_sentences):
                script_text = clean_sentences[i]
            else:
                script_text = f"장면 {scene.scene_number}에 대한 내용입니다."
            
            tts_script = TTSScript(
                scene_number=scene.scene_number,
                text=script_text,
                duration=scene.duration,
                emotion=scene.emotion,
                voice_style="natural"
            )
            tts_scripts.append(tts_script)
        
        return tts_scripts
    
    async def generate_tts_audio(
        self, 
        tts_scripts: List[TTSScript],
        voice_id: str = None,  # None이면 랜덤 선택
        output_dir: str = "./static/audio"
    ) -> List[TTSResult]:
        """TTS 스크립트를 오디오 파일로 변환"""
        
        # voice_id가 None이면 랜덤 선택
        if voice_id is None:
            voice_id = self.get_random_voice_id()
        
        print(f"🎤 {len(tts_scripts)}개 스크립트를 TTS 오디오로 변환 시작...")
        print(f"   음성 ID: {voice_id} (랜덤 선택)" if voice_id in self.VOICE_IDS else f"   음성 ID: {voice_id}")
        print(f"   출력 디렉토리: {output_dir}")
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        results = []
        
        for i, script in enumerate(tts_scripts, 1):
            print(f"🎤 [{i}/{len(tts_scripts)}] 장면 {script.scene_number} TTS 생성 중...")
            print(f"   텍스트: {script.text[:50]}{'...' if len(script.text) > 50 else ''}")
            
            try:
                # ElevenLabs API 호출
                result = await self._create_single_tts(
                    text=script.text,
                    voice_id=voice_id,
                    output_dir=output_dir,
                    scene_number=script.scene_number
                )
                results.append(result)
                
                if result.success:
                    print(f"   ✅ 생성 완료: {os.path.basename(result.audio_file_path)}")
                else:
                    print(f"   ❌ 생성 실패: {result.error}")
            
            except Exception as e:
                print(f"   ❌ TTS 생성 중 오류: {e}")
                error_result = TTSResult(success=False, error=str(e))
                results.append(error_result)
        
        # 통계 출력
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        print(f"✅ TTS 변환 완료: {len(successful)}개 성공, {len(failed)}개 실패")
        
        return results
    
    async def _create_single_tts(self, text: str, voice_id: str, output_dir: str, scene_number: int) -> TTSResult:
        """단일 TTS 오디오 생성"""
        try:
            # ElevenLabs API 호출
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=data, headers=headers)
                
                if response.status_code == 200:
                    # 오디오 파일 저장
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"scene_{scene_number:02d}_{timestamp}.mp3"
                    file_path = os.path.join(output_dir, filename)
                    
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    
                    # 파일 정보 확인
                    file_size = os.path.getsize(file_path)
                    
                    # 웹 접근 가능한 URL 생성
                    audio_url = f"/static/audio/{filename}"
                    
                    return TTSResult(
                        success=True,
                        audio_file_path=file_path,
                        audio_url=audio_url,
                        duration=len(text) * 0.1,  # 대략적인 길이 추정
                        file_size=file_size
                    )
                else:
                    error_msg = f"ElevenLabs API 오류: {response.status_code} - {response.text}"
                    return TTSResult(success=False, error=error_msg)
        
        except Exception as e:
            return TTSResult(success=False, error=str(e))
    
    async def process_storyboard_to_tts(
        self,
        storyboard_data: Dict,
        product_name: str = "상품",
        brand_name: str = "브랜드", 
        target_audience: Union[str, Dict, List] = "일반 소비자",
        ad_concept: Union[str, Dict, List] = "매력적인 광고",
        script_style: Union[str, Dict, List] = "친근하고 자연스러운",
        voice_id: str = None,  # None이면 랜덤 선택
        output_dir: str = "./static/audio"
    ) -> Dict:
        """전체 프로세스: 스토리보드 → LLM 스크립트 → TTS 오디오"""
        
        try:
            print(f"🎬 스토리보드 → OpenAI LLM → TTS 전체 프로세스 시작")
            
            # 1단계: 스토리보드 데이터 파싱
            scenes = self.parse_storyboard_data(storyboard_data)
            
            # 2단계: OpenAI LLM으로 TTS 스크립트 생성
            tts_scripts = await self.generate_tts_script_with_llm(
                scenes=scenes,
                product_name=product_name,
                brand_name=brand_name,
                target_audience=target_audience,
                ad_concept=ad_concept,
                script_style=script_style
            )
            
            # 3단계: TTS 오디오 생성
            tts_results = await self.generate_tts_audio(
                tts_scripts=tts_scripts,
                voice_id=voice_id,
                output_dir=output_dir
            )
            
            # 4단계: 결과 정리
            successful_tts = [r for r in tts_results if r.success]
            failed_tts = [r for r in tts_results if not r.success]
            
            # 스크립트와 결과 매칭
            final_results = []
            for script, result in zip(tts_scripts, tts_results):
                final_result = {
                    "scene_number": script.scene_number,
                    "text": script.text,
                    "duration": script.duration,
                    "emotion": script.emotion,
                    "voice_style": script.voice_style
                }
                
                if result.success:
                    final_result.update({
                        "success": True,
                        "audio_url": result.audio_url,
                        "audio_file_path": result.audio_file_path,
                        "file_size": result.file_size
                    })
                else:
                    final_result.update({
                        "success": False,
                        "error": result.error
                    })
                
                final_results.append(final_result)
            
            print(f"🎉 전체 프로세스 완료!")
            print(f"   총 장면: {len(scenes)}개")
            print(f"   성공한 TTS: {len(successful_tts)}개")
            print(f"   실패한 TTS: {len(failed_tts)}개")
            
            return {
                "success": True,
                "message": f"스토리보드 → LLM → TTS 변환 완료! {len(successful_tts)}개 오디오 생성",
                "scenes": [scene.__dict__ for scene in scenes],
                "tts_scripts": [script.__dict__ for script in tts_scripts],
                "results": final_results,
                "successful_count": len(successful_tts),
                "failed_count": len(failed_tts),
                "success_rate": f"{(len(successful_tts) / len(tts_scripts)) * 100:.1f}%" if tts_scripts else "0%",
                "processing_info": {
                    "product_name": product_name,
                    "brand_name": brand_name,
                    "target_audience": target_audience,
                    "ad_concept": ad_concept,
                    "script_style": script_style,
                    "voice_id": voice_id,
                    "output_dir": output_dir
                }
            }
            
        except Exception as e:
            print(f"❌ 전체 프로세스 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"스토리보드 → LLM → TTS 변환 실패: {str(e)}"
            }
    
    async def process_storyboard_to_tts_api_compatible(
        self,
        storyboard_data: Dict,
        persona_description: str,
        marketing_insights: str,
        ad_concept: str,
        voice_id: str,
        output_dir: str = "tts_outputs"
    ) -> Dict:
        """client.py API와 호환되는 스토리보드 → TTS 변환 메서드"""
        
        try:
            print(f"📋 API 호환 스토리보드 → TTS 변환 시작")
            print(f"   출력 디렉토리: {output_dir}")
            print(f"   음성 ID: {voice_id}")
            
            # 스토리보드 데이터에서 장면 추출
            scenes_data = storyboard_data.get("scenes", [])
            if not scenes_data:
                raise ValueError("스토리보드에 장면 데이터가 없습니다")
            
            # StoryboardScene 객체 생성
            scenes = []
            for scene_data in scenes_data:
                scene = StoryboardScene(
                    scene_number=scene_data.get("scene_number", 1),
                    description=scene_data.get("description", ""),
                    image_prompt=scene_data.get("image_prompt", ""),
                    duration=scene_data.get("duration", 5.0),
                    emotion=scene_data.get("emotion", "confident"),
                    action=scene_data.get("action", "showcase")
                )
                scenes.append(scene)
            
            print(f"✅ {len(scenes)}개 장면 로드 완료")
            
            # OpenAI LLM으로 TTS 대본 생성
            print(f"🤖 OpenAI LLM TTS 대본 생성 중...")
            tts_scripts = await self.generate_tts_scripts_from_scenes_api_compatible(
                scenes=scenes,
                persona_description=persona_description,
                marketing_insights=marketing_insights,
                ad_concept=ad_concept
            )
            
            print(f"✅ {len(tts_scripts)}개 TTS 대본 생성 완료")
            
            # TTS 오디오 생성
            print(f"🎵 ElevenLabs TTS 오디오 생성 중...")
            tts_results = await self.generate_tts_audio_batch(
                scripts=tts_scripts,
                voice_id=voice_id,
                output_dir=output_dir
            )
            
            # 결과 정리
            successful_tts = [r for r in tts_results if r.success]
            failed_tts = [r for r in tts_results if not r.success]
            
            # 스크립트와 결과 매칭
            final_results = []
            for script, result in zip(tts_scripts, tts_results):
                final_result = {
                    "scene_number": script.scene_number,
                    "text": script.text,
                    "duration": script.duration,
                    "emotion": script.emotion,
                    "voice_style": script.voice_style
                }
                
                if result.success:
                    final_result.update({
                        "success": True,
                        "audio_url": result.audio_url,
                        "audio_file_path": result.audio_file_path,
                        "file_size": result.file_size
                    })
                else:
                    final_result.update({
                        "success": False,
                        "error": result.error
                    })
                
                final_results.append(final_result)
            
            print(f"🎉 API 호환 프로세스 완료!")
            print(f"   총 장면: {len(scenes)}개")
            print(f"   성공한 TTS: {len(successful_tts)}개")
            print(f"   실패한 TTS: {len(failed_tts)}개")
            
            return {
                "success": True,
                "message": f"API 호환 TTS 변환 완료! {len(successful_tts)}개 오디오 생성",
                "scenes": [scene.__dict__ for scene in scenes],
                "tts_scripts": [script.__dict__ for script in tts_scripts],
                "results": final_results,
                "successful_count": len(successful_tts),
                "failed_count": len(failed_tts),
                "success_rate": f"{(len(successful_tts) / len(tts_scripts)) * 100:.1f}%" if tts_scripts else "0%",
                "processing_info": {
                    "persona_description": persona_description[:100] + "...",
                    "marketing_insights": marketing_insights[:100] + "...",
                    "ad_concept": ad_concept[:100] + "...",
                    "voice_id": voice_id,
                    "output_dir": output_dir
                }
            }
            
        except Exception as e:
            print(f"❌ API 호환 프로세스 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"API 호환 TTS 변환 실패: {str(e)}"
            }

    async def generate_tts_scripts_from_scenes_api_compatible(
        self,
        scenes: List[StoryboardScene],
        persona_description: str,
        marketing_insights: str,
        ad_concept: str
    ) -> List[TTSScript]:
        """API 호환성을 위한 TTS 스크립트 생성"""
        
        try:
            # API 키 확인
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
            
            # 장면 정보를 JSON으로 변환
            scenes_info = []
            for scene in scenes:
                scenes_info.append({
                    "scene_number": scene.scene_number,
                    "description": scene.description,
                    "image_prompt": scene.image_prompt,
                    "duration": scene.duration,
                    "emotion": scene.emotion,
                    "action": scene.action
                })
            
            scenes_json = json.dumps(scenes_info, ensure_ascii=False, indent=2)
            
            # OpenAI LLM 프롬프트 구성
            prompt = f"""
당신은 광고 영상 TTS 대본 작성 전문가입니다.
아래 정보를 바탕으로 각 장면별로 효과적인 TTS 대본을 작성해주세요.

**페르소나 정보:**
{persona_description}

**마케팅 인사이트:**
{marketing_insights}

**광고 컨셉:**
{ad_concept}

**스토리보드 장면들:**
{scenes_json}

**요구사항:**
1. 각 장면의 감정(emotion)과 액션(action)에 맞는 톤으로 작성
2. 페르소나의 특성을 반영한 언어 스타일 사용
3. 마케팅 인사이트의 핵심 메시지 포함
4. 광고 컨셉의 톤앤매너 반영
5. 각 장면당 5초 내외로 읽을 수 있는 분량

**출력 형식 (JSON):**
{{
  "scripts": [
    {{
      "scene_number": 1,
      "text": "실제 TTS로 읽힐 대본 텍스트",
      "duration": 5.0,
      "emotion": "confident",
      "voice_style": "natural"
    }}
  ]
}}

JSON 형식으로만 응답해주세요:
"""
            
            # OpenAI API 호출
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    raise Exception(f"OpenAI API 오류 (상태코드: {response.status_code}): {error_text}")
                
                response_data = response.json()
                llm_response = response_data["choices"][0]["message"]["content"]
                
                print(f"🤖 OpenAI LLM 응답 받음")
                print(f"응답 길이: {len(llm_response)} 글자")
                
                # JSON 파싱
                try:
                    # JSON 부분만 추출 (```json과 ```사이의 내용)
                    if "```json" in llm_response:
                        json_start = llm_response.find("```json") + 7
                        json_end = llm_response.find("```", json_start)
                        json_content = llm_response[json_start:json_end].strip()
                    elif "{" in llm_response:
                        json_start = llm_response.find("{")
                        json_end = llm_response.rfind("}") + 1
                        json_content = llm_response[json_start:json_end]
                    else:
                        raise ValueError("응답에서 JSON 형식을 찾을 수 없습니다")
                    
                    script_data = json.loads(json_content)
                    
                    # TTSScript 객체 리스트 생성
                    tts_scripts = []
                    for script_info in script_data.get("scripts", []):
                        script = TTSScript(
                            scene_number=script_info.get("scene_number", 1),
                            text=script_info.get("text", ""),
                            duration=script_info.get("duration", 5.0),
                            emotion=script_info.get("emotion", "confident"),
                            voice_style=script_info.get("voice_style", "natural")
                        )
                        tts_scripts.append(script)
                    
                    print(f"✅ {len(tts_scripts)}개 TTS 스크립트 파싱 완료")
                    return tts_scripts
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON 파싱 오류: {e}")
                    print(f"원본 응답: {llm_response}")
                    raise Exception(f"LLM 응답 JSON 파싱 실패: {e}")
                
        except Exception as e:
            print(f"❌ API 호환 TTS 스크립트 생성 실패: {e}")
            raise e

# 사용 예시 함수들
async def generate_complete_tts_from_scratch(
    persona_description: str,
    marketing_insights: str,
    ad_concept: str,
    storyboard_scenes: List[Dict],
    voice_id: str = None,  # None이면 랜덤 선택
    output_dir: str = "tts_outputs"
) -> Dict:
    """client.py API와 호환되는 TTS 완전 생성 함수"""
    
    print(f"🚀 API 호환 TTS 생성 시작")
    print(f"   페르소나: {persona_description[:100]}...")
    print(f"   마케팅 인사이트: {marketing_insights[:100]}...")
    print(f"   광고 컨셉: {ad_concept[:100]}...")
    print(f"   스토리보드 장면 수: {len(storyboard_scenes)}")
    
    # 생성기 인스턴스 생성
    generator = StoryboardToTTSGenerator()
    
    # voice_id가 None이면 랜덤 선택
    if voice_id is None:
        voice_id = generator.get_random_voice_id()
        print(f"   🎲 랜덤 음성 선택: {voice_id}")
    
    # 스토리보드 데이터 구조 변환
    storyboard_data = {
        "scenes": []
    }
    
    for i, scene in enumerate(storyboard_scenes):
        storyboard_data["scenes"].append({
            "scene_number": i + 1,
            "description": scene.get("description", ""),
            "image_prompt": scene.get("prompt_text", ""),
            "duration": 5.0,
            "emotion": "confident",
            "action": "product showcase"
        })
    
    # TTS 대본 및 오디오 생성
    result = await generator.process_storyboard_to_tts_api_compatible(
        storyboard_data=storyboard_data,
        persona_description=persona_description,
        marketing_insights=marketing_insights,
        ad_concept=ad_concept,
        voice_id=voice_id,
        output_dir=output_dir
    )
    
    return result

async def generate_storyboard_from_workflow_data(
    product_name: str,
    brand_name: str,
    target_customer: Dict,
    marketing_insights: Dict,
    ad_concept: Dict
) -> Dict:
    """1~4단계 워크플로우 데이터를 기반으로 스토리보드 생성"""
    
    print(f"📋 1~4단계 데이터 기반 스토리보드 생성 중...")
    
    # OpenAI LLM으로 스토리보드 생성
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # 1~4단계 정보를 JSON으로 변환
    import json
    target_json = json.dumps(target_customer, ensure_ascii=False, indent=2)
    insights_json = json.dumps(marketing_insights, ensure_ascii=False, indent=2)
    concept_json = json.dumps(ad_concept, ensure_ascii=False, indent=2)
    
    # 스토리보드 생성을 위한 LLM 프롬프트
    storyboard_prompt = f"""
당신은 광고 영상 기획 전문가입니다. 
아래 1~4단계 정보를 바탕으로 효과적인 광고 스토리보드를 생성해주세요.

1단계: 타겟 고객(페르소나)
{target_json}

2단계: 마케팅 인사이트
{insights_json}

3단계: 광고 컨셉
{concept_json}

**상품/브랜드 정보:**
상품명: {product_name}
브랜드명: {brand_name}

**요구사항:**
1. 타겟 고객의 pain point와 needs를 반영한 스토리 구성
2. 마케팅 인사이트의 emotional trigger를 활용한 감정적 어필
3. 광고 컨셉의 톤앤매너와 메시지 반영
4. 3-5개 장면으로 구성 (도입-전개-절정-결말 구조)
5. 각 장면별로 명확한 시각적 설명과 감정 표현

**출력 형식 (JSON):**
{{
  "scenes": [
    {{
      "scene_number": 1,
      "description": "장면에 대한 상세한 설명",
      "image_prompt": "영상 생성을 위한 영어 프롬프트",
      "duration": 5.0,
      "emotion": "happy/sad/confident/neutral 등",
      "action": "scene의 주요 액션이나 목적"
    }}
  ]
}}

JSON 형식으로만 응답해주세요:
"""
    
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "당신은 광고 스토리보드 기획 전문가입니다. 주어진 정보를 바탕으로 효과적인 광고 스토리보드를 JSON 형식으로 생성합니다."
            },
            {
                "role": "user", 
                "content": storyboard_prompt
            }
        ],
        "max_tokens": 1500,
        "temperature": 0.8
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API 요청 실패: {response.status_code} - {response.text}")
            
            response_data = response.json()
            generated_content = response_data["choices"][0]["message"]["content"]
            
            # JSON 파싱 시도
            try:
                # ```json ``` 블록 제거
                if "```json" in generated_content:
                    json_start = generated_content.find("```json") + 7
                    json_end = generated_content.rfind("```")
                    generated_content = generated_content[json_start:json_end].strip()
                elif "```" in generated_content:
                    json_start = generated_content.find("```") + 3
                    json_end = generated_content.rfind("```")
                    generated_content = generated_content[json_start:json_end].strip()
                
                storyboard_data = json.loads(generated_content)
                print(f"✅ 스토리보드 생성 완료: {len(storyboard_data.get('scenes', []))}개 장면")
                return storyboard_data
                
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON 파싱 실패: {e}")
                # 기본 스토리보드 생성
                return generate_fallback_storyboard(product_name, brand_name)
                
    except Exception as llm_error:
        print(f"⚠️ 스토리보드 생성 실패: {llm_error}")
        # 기본 스토리보드 생성
        return generate_fallback_storyboard(product_name, brand_name)

def generate_fallback_storyboard(product_name: str, brand_name: str) -> Dict:
    """기본 스토리보드 생성"""
    return {
        "scenes": [
            {
                "scene_number": 1,
                "description": f"{product_name}를 소개하는 매력적인 장면",
                "image_prompt": f"attractive product introduction scene for {product_name}",
                "duration": 5.0,
                "emotion": "happy",
                "action": "product_introduction"
            },
            {
                "scene_number": 2,
                "description": f"{product_name} 사용으로 얻는 혜택을 보여주는 장면",
                "image_prompt": f"person benefiting from using {product_name}",
                "duration": 6.0,
                "emotion": "satisfied",
                "action": "benefit_demonstration"
            },
            {
                "scene_number": 3,
                "description": f"{brand_name} 로고와 함께하는 마무리 장면",
                "image_prompt": f"{brand_name} logo with call to action",
                "duration": 4.0,
                "emotion": "confident",
                "action": "brand_closing"
            }
        ]
    }


if __name__ == "__main__":
    # 모듈이 직접 실행될 때만 실행되는 부분
    pass
