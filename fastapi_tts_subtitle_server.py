"""
FastAPI 서버 - 0.1초 정밀도 Whisper AI TTS + 자막 통합 서비스
"""
from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import shutil
import tempfile
from typing import Optional
from video_tts_subtitle_api import api_create_enhanced_video

app = FastAPI(title="TTS + Whisper AI 자막 통합 서비스", version="1.0.0")

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {
        "message": "TTS + Whisper AI 자막 통합 서비스",
        "version": "1.0.0",
        "features": [
            "0.1초 정밀도 Whisper AI 자막",
            "ElevenLabs TTS 음성",
            "배경음악 통합",
            "30pt 한글 최적화 폰트"
        ]
    }

@app.post("/create_video_with_tts_subtitles")
async def create_video_with_tts_subtitles(
    video_file: UploadFile = File(..., description="비디오 파일"),
    tts_text: str = Form(..., description="TTS로 변환할 텍스트"),
    voice_id: Optional[str] = Form("21m00Tcm4TlvDq8ikWAM", description="ElevenLabs 음성 ID"),
    font_size: int = Form(30, description="자막 폰트 크기"),
    enable_bgm: bool = Form(True, description="배경음악 사용 여부")
):
    """
    비디오 파일에 TTS 음성과 0.1초 정밀도 Whisper AI 자막을 추가
    """
    try:
        # 임시 파일로 업로드된 비디오 저장
        temp_dir = tempfile.mkdtemp()
        temp_video_path = os.path.join(temp_dir, video_file.filename)
        
        with open(temp_video_path, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        
        # TTS + 자막 통합 처리
        result = await api_create_enhanced_video(
            video_path=temp_video_path,
            text=tts_text,
            voice_id=voice_id,
            font_size=font_size,
            enable_bgm=enable_bgm
        )
        
        # 임시 파일 정리
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        
        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "message": "비디오 생성 완료",
                "output_filename": result["output_filename"],
                "server_url": result["server_url"],
                "file_size": result["file_size"],
                "tts_duration": result["tts_duration"],
                "subtitle_method": result["subtitle_method"],
                "subtitle_count": result["subtitle_count"],
                "mode": result["mode"]
            })
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류 발생: {str(e)}")

@app.post("/create_video_with_existing_video")
async def create_video_with_existing_video(
    video_filename: str = Form(..., description="기존 비디오 파일명 (static/videos/ 디렉토리)"),
    tts_text: str = Form(..., description="TTS로 변환할 텍스트"),
    voice_id: Optional[str] = Form("21m00Tcm4TlvDq8ikWAM", description="ElevenLabs 음성 ID"),
    font_size: int = Form(48, description="자막 폰트 크기"),
    enable_bgm: bool = Form(True, description="배경음악 사용 여부")
):
    """
    서버에 있는 기존 비디오 파일로 TTS + 자막 생성
    """
    try:
        video_path = os.path.join("static", "videos", video_filename)
        
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail=f"비디오 파일을 찾을 수 없습니다: {video_filename}")
        
        # TTS + 자막 통합 처리
        result = await api_create_enhanced_video(
            video_path=video_path,
            text=tts_text,
            voice_id=voice_id,
            font_size=font_size,
            enable_bgm=enable_bgm
        )
        
        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "message": "비디오 생성 완료",
                "output_filename": result["output_filename"],
                "server_url": result["server_url"],
                "file_size": result["file_size"],
                "tts_duration": result["tts_duration"],
                "subtitle_method": result["subtitle_method"],
                "subtitle_count": result["subtitle_count"],
                "mode": result["mode"]
            })
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류 발생: {str(e)}")

@app.get("/download/{filename}")
async def download_file(filename: str):
    """생성된 비디오 파일 다운로드"""
    file_path = os.path.join("static", "videos", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    
    return FileResponse(
        file_path,
        media_type='video/mp4',
        filename=filename
    )

@app.get("/list_videos")
async def list_videos():
    """사용 가능한 비디오 파일 목록"""
    try:
        video_dir = os.path.join("static", "videos")
        if not os.path.exists(video_dir):
            return {"videos": []}
        
        videos = []
        for filename in os.listdir(video_dir):
            if filename.endswith(('.mp4', '.avi', '.mov')):
                file_path = os.path.join(video_dir, filename)
                file_size = os.path.getsize(file_path)
                videos.append({
                    "filename": filename,
                    "size": file_size,
                    "url": f"/static/videos/{filename}"
                })
        
        return {"videos": videos}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"비디오 목록 조회 중 오류: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 FastAPI 서버 시작 중...")
    print("   - 0.1초 정밀도 Whisper AI 자막")
    print("   - 48pt 한글 최적화 폰트")
    print("   - ElevenLabs TTS 통합")
    print("   - 자동 배경음악")
    print("\n📡 서버 주소: http://localhost:8000")
    print("📋 API 문서: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
