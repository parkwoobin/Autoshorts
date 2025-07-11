"""
스토리보드 → Runway 영상 → TTS → 자막 → 최종 영상 통합 워크플로우
"""
import asyncio
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import tempfile

# 기존 모듈들 import
from workflows import generate_scene_prompts, generate_images_sequentially, generate_persona, create_ad_concept
from models import StoryboardOutput, ReferenceImageWithDescription, TargetCustomer
from tts_utils import create_tts_audio, get_recommended_voice, detect_language, TTSConfig
from subtitle_utils import transcribe_audio_with_whisper, add_subtitles_to_video_ffmpeg, SubtitleResult
from video_merger import VideoTransitionMerger

class FullVideoWorkflow:
    """완전한 비디오 제작 워크플로우 클래스"""
    
    def __init__(self, use_static_dir=True):
        self.use_static_dir = use_static_dir
        self.temp_dir = "./static/videos" if use_static_dir else tempfile.mkdtemp()
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # API 키들 로드
        from dotenv import load_dotenv
        load_dotenv()
        
        self.api_keys = {
            "elevenlabs": os.getenv("ELEVNLABS_API_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "runway": os.getenv("RUNWAY_API_KEY")
        }
        
        print("🎬 완전한 비디오 제작 워크플로우 초기화 완료")

    async def create_complete_video_from_storyboard(
        self,
        storyboard: StoryboardOutput,  # 1-4단계에서 생성된 스토리보드
        tts_scripts: List[str] = None,  # 각 장면별 TTS 스크립트 (선택사항)
        voice_preference: Dict[str, str] = None,  # 음성 선호도
        transition_type: str = "fade",  # 트랜지션 타입
        add_subtitles: bool = True  # 자막 추가 여부
    ) -> Dict[str, Any]:
        """
        스토리보드부터 최종 자막 포함 영상까지 완전한 제작 과정
        
        Args:
            storyboard: 생성된 스토리보드
            tts_scripts: 각 장면별 TTS 스크립트
            voice_preference: {"gender": "male/female", "language": "ko/en"}
            transition_type: 비디오 트랜지션 타입
            add_subtitles: 자막 추가 여부
            
        Returns:
            Dict: 최종 결과 정보
        """
        print(f"\n🎬 완전한 비디오 제작 워크플로우 시작")
        print(f"   장면 수: {len(storyboard.scenes)}")
        print(f"   트랜지션: {transition_type}")
        print(f"   자막 추가: {add_subtitles}")
        
        try:
            # 1단계: Runway API로 스토리보드의 각 장면을 영상으로 생성
            print(f"\n🎥 1단계: Runway API로 {len(storyboard.scenes)}개 장면 영상 생성...")
            video_results = await generate_images_sequentially(
                scenes=storyboard.scenes,
                api_key=self.api_keys["runway"]
            )
            
            # 성공한 영상들만 필터링
            successful_videos = []
            for result in video_results:
                if result.get("status") == "success" and result.get("image_url"):
                    successful_videos.append(result)
            
            if not successful_videos:
                return {"success": False, "error": "영상 생성에 실패했습니다."}
            
            print(f"✅ {len(successful_videos)}/{len(storyboard.scenes)}개 영상 생성 완료")
            
            # 2단계: TTS 스크립트 준비
            print(f"\n🎙️ 2단계: TTS 스크립트 준비...")
            if not tts_scripts:
                # 기본 TTS 스크립트 생성 (장면별 간단한 설명)
                tts_scripts = await self.generate_default_tts_scripts(storyboard)
            
            # TTS 스크립트와 영상 개수 맞추기
            tts_scripts = tts_scripts[:len(successful_videos)]
            
            # 3단계: 음성 선택
            print(f"\n🎤 3단계: 최적 음성 선택...")
            if not voice_preference:
                voice_preference = {"gender": "female", "language": "ko"}
            
            # 첫 번째 스크립트 기반으로 권장 음성 선택
            sample_text = tts_scripts[0] if tts_scripts else "안녕하세요"
            voice_id = get_recommended_voice(sample_text, voice_preference.get("gender"))
            print(f"   선택된 음성: {TTSConfig.VOICES.get(voice_id, voice_id)}")
            
            # 4단계: 각 영상에 TTS 추가
            print(f"\n🔊 4단계: {len(successful_videos)}개 영상에 TTS 음성 추가...")
            videos_with_tts = []
            
            for i, (video_result, tts_script) in enumerate(zip(successful_videos, tts_scripts)):
                scene_num = i + 1
                print(f"   장면 {scene_num}: TTS 추가 중...")
                
                try:
                    # 영상 다운로드
                    merger = VideoTransitionMerger(use_static_dir=True)
                    video_path = merger._download_video(
                        video_result["image_url"],
                        f"scene_{scene_num}_original.mp4"
                    )
                    
                    # TTS 추가
                    video_with_tts_path = await merger.add_tts_to_video(
                        video_path=video_path,
                        text=tts_script,
                        voice_id=voice_id,
                        tts_volume=0.8,
                        video_volume=0.2,
                        api_key=self.api_keys["elevenlabs"],
                        output_filename=f"scene_{scene_num}_with_tts.mp4"
                    )
                    
                    videos_with_tts.append({
                        "scene_number": scene_num,
                        "video_path": video_with_tts_path,
                        "tts_script": tts_script,
                        "original_video_url": video_result["image_url"]
                    })
                    
                    # 원본 비디오 파일 삭제
                    try:
                        os.remove(video_path)
                    except:
                        pass
                    
                    print(f"   ✅ 장면 {scene_num} TTS 추가 완료")
                    
                except Exception as e:
                    print(f"   ❌ 장면 {scene_num} TTS 추가 실패: {e}")
                    continue
            
            if not videos_with_tts:
                return {"success": False, "error": "TTS 추가에 실패했습니다."}
            
            # 5단계: 영상들을 트랜지션과 함께 합치기
            print(f"\n🔗 5단계: {len(videos_with_tts)}개 영상을 트랜지션과 함께 합치기...")
            
            # 파일 경로를 URL로 변환
            video_urls = [f"file://{video['video_path']}" for video in videos_with_tts]
            
            merger = VideoTransitionMerger(use_static_dir=True)
            import time
            merged_filename = f"merged_complete_video_{int(time.time() * 1000)}.mp4"
            merged_video_path = merger.merge_videos(
                video_urls=video_urls,
                transition_type=transition_type,
                output_filename=merged_filename
            )
            
            print(f"✅ 영상 합치기 완료: {os.path.basename(merged_video_path)}")
            
            # 6단계: 자막 추가 (선택사항)
            final_video_path = merged_video_path
            subtitle_info = None
            
            if add_subtitles:
                print(f"\n📝 6단계: 자막 생성 및 추가...")
                
                # 전체 TTS 스크립트를 하나로 합치기
                full_script = " ".join(tts_scripts)
                
                # 첫 번째 장면의 TTS 음성 파일로 자막 생성 (대표)
                try:
                    # 임시 TTS 파일 생성 (자막용)
                    from tts_utils import create_tts_audio
                    temp_tts_result = await create_tts_audio(
                        text=full_script,
                        voice_id=voice_id,
                        api_key=self.api_keys["elevenlabs"],
                        output_dir="./static/audio"
                    )
                    
                    if temp_tts_result.success:
                        # Whisper로 자막 생성
                        subtitle_result = await transcribe_audio_with_whisper(
                            audio_file_path=temp_tts_result.audio_file_path,
                            language=voice_preference.get("language", "ko"),
                            api_key=self.api_keys["openai"],
                            output_format="srt"
                        )
                        
                        if subtitle_result.success:
                            # FFmpeg로 자막 합성
                            final_result = add_subtitles_to_video_ffmpeg(
                                video_file_path=merged_video_path,
                                subtitle_file_path=subtitle_result.subtitle_file_path,
                                language=voice_preference.get("language", "ko")
                            )
                            
                            if final_result.success:
                                final_video_path = final_result.video_with_subtitle_path
                                subtitle_info = {
                                    "subtitle_file": subtitle_result.subtitle_file_path,
                                    "transcription": subtitle_result.transcription
                                }
                                print(f"✅ 자막 추가 완료")
                            else:
                                print(f"⚠️ 자막 합성 실패: {final_result.error}")
                        else:
                            print(f"⚠️ 자막 생성 실패: {subtitle_result.error}")
                        
                        # 임시 TTS 파일 삭제
                        try:
                            os.remove(temp_tts_result.audio_file_path)
                        except:
                            pass
                    else:
                        print(f"⚠️ 자막용 TTS 생성 실패: {temp_tts_result.error}")
                        
                except Exception as e:
                    print(f"⚠️ 자막 처리 중 오류: {e}")
            
            # 7단계: 임시 파일 정리
            print(f"\n🧹 7단계: 임시 파일 정리...")
            cleanup_count = 0
            for video_info in videos_with_tts:
                try:
                    os.remove(video_info["video_path"])
                    cleanup_count += 1
                except:
                    pass
            
            # 자막이 추가된 경우 원본 합친 비디오도 삭제
            if add_subtitles and final_video_path != merged_video_path:
                try:
                    os.remove(merged_video_path)
                    cleanup_count += 1
                except:
                    pass
            
            print(f"✅ {cleanup_count}개 임시 파일 정리 완료")
            
            # 최종 결과 반환
            final_video_url = f"http://localhost:8000/static/videos/{os.path.basename(final_video_path)}"
            
            result = {
                "success": True,
                "final_video_path": final_video_path,
                "final_video_url": final_video_url,
                "video_concept": storyboard.video_concept,
                "total_scenes": len(successful_videos),
                "tts_scripts": tts_scripts,
                "voice_used": TTSConfig.VOICES.get(voice_id, voice_id),
                "transition_type": transition_type,
                "has_subtitles": add_subtitles and subtitle_info is not None,
                "processing_summary": {
                    "scenes_generated": len(successful_videos),
                    "scenes_with_tts": len(videos_with_tts),
                    "final_video_created": True,
                    "subtitles_added": subtitle_info is not None
                }
            }
            
            if subtitle_info:
                result["subtitle_info"] = subtitle_info
            
            print(f"\n🎉 완전한 비디오 제작 워크플로우 완료!")
            print(f"   최종 영상: {final_video_url}")
            
            return result
            
        except Exception as e:
            error_msg = f"비디오 제작 워크플로우 중 오류 발생: {e}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    async def generate_default_tts_scripts(self, storyboard: StoryboardOutput) -> List[str]:
        """스토리보드 기반으로 기본 TTS 스크립트 생성"""
        print("📝 기본 TTS 스크립트 생성 중...")
        
        # 간단한 템플릿 기반 스크립트 생성
        scripts = []
        for i, scene in enumerate(storyboard.scenes, 1):
            if i == 1:
                script = f"안녕하세요! 놀라운 AI 영상을 소개합니다."
            elif i == len(storyboard.scenes):
                script = f"지금 바로 확인해보세요!"
            else:
                script = f"다음 장면을 계속 확인해주세요."
            
            scripts.append(script)
        
        print(f"✅ {len(scripts)}개 기본 TTS 스크립트 생성 완료")
        return scripts

    def get_workflow_status(self) -> Dict[str, Any]:
        """워크플로우 상태 정보 반환"""
        return {
            "api_keys_status": {
                "elevenlabs": bool(self.api_keys["elevenlabs"]),
                "openai": bool(self.api_keys["openai"]),
                "runway": bool(self.api_keys["runway"])
            },
            "temp_dir": self.temp_dir,
            "use_static_dir": self.use_static_dir,
            "available_voices": len(TTSConfig.VOICES),
            "supported_languages": ["ko", "en", "multilingual"]
        }

# 워크플로우 인스턴스 생성을 위한 헬퍼 함수
def create_video_workflow(use_static_dir=True) -> FullVideoWorkflow:
    """비디오 워크플로우 인스턴스 생성"""
    return FullVideoWorkflow(use_static_dir=use_static_dir)

# 간편 사용을 위한 래퍼 함수
async def create_complete_video(
    storyboard: StoryboardOutput,
    tts_scripts: List[str] = None,
    voice_gender: str = "female",
    voice_language: str = "ko",
    transition_type: str = "fade",
    add_subtitles: bool = True
) -> Dict[str, Any]:
    """
    스토리보드를 최종 자막 포함 영상으로 변환하는 간편 함수
    
    Args:
        storyboard: 생성된 스토리보드
        tts_scripts: TTS 스크립트 리스트
        voice_gender: 음성 성별 ("male", "female")
        voice_language: 음성 언어 ("ko", "en")
        transition_type: 트랜지션 타입
        add_subtitles: 자막 추가 여부
        
    Returns:
        Dict: 처리 결과
    """
    workflow = create_video_workflow()
    
    voice_preference = {
        "gender": voice_gender,
        "language": voice_language
    }
    
    return await workflow.create_complete_video_from_storyboard(
        storyboard=storyboard,
        tts_scripts=tts_scripts,
        voice_preference=voice_preference,
        transition_type=transition_type,
        add_subtitles=add_subtitles
    )
