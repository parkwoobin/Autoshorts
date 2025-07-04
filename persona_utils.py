"""
페르소나 생성 및 LLM 관련 유틸리티 함수들
"""
from typing import List
from openai import OpenAI
from models import (
    TargetCustomer, PersonaData, UserVideoInput,
    ReferenceImage, SceneImagePrompt, StoryboardScene, StoryboardOutput
)
import os
from dotenv import load_dotenv
import asyncio

# LangChain imports
# 출력 구조 정확하게 나오게 하기 위한 outputparser
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 가져오기
OpenAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OpenAI 클라이언트 초기화 (기존 호환성용)
client = OpenAI(api_key=OpenAI_API_KEY)
# LangChain ChatOpenAI 초기화
llm = ChatOpenAI(
    model="gpt-4.1-nano-2025-04-14",
    temperature=0.7,
    openai_api_key=OpenAI_API_KEY
)

# 다 구현하고 나중에 수정 -> 트렌드 데이터 API 호출 부분
async def trend_data_api(country: str) -> dict:
    """
    외부 API를 통해 특정 국가,문화 등의 최신 트렌드 데이터를 가져옴
    실제 구현 시에는 외부 API 호출 로직으로 구현
    """
# ==================================================================================

# 1단계: 타겟 고객 정보로 페르소나 생성
async def generate_persona_with_llm(customer: TargetCustomer) -> PersonaData:
    """LLM을 사용해 타겟 고객의 페르소나를 생성"""
    age_ranges_str = ", ".join(customer.age_range)
    interests_str = ", ".join(customer.interests)
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 마케팅 전문가이자 소비자 행동 분석가입니다. 제공된 타겟 고객 정보에만 기반하여, 상세한 페르소나를 제안해주세요."
                },
                {
                    "role": "user", 
                    "content": f"""
다음 타겟 고객 정보를 분석해주세요:
- 국가: {customer.country}
- 연령대: {age_ranges_str}
- 성별: {customer.gender}
- 언어: {customer.language}
- 관심사: {interests_str}

다음 형식으로 답변해주세요:

**페르소나 프로필:**
(이 타겟의 라이프스타일, 가치관, 소비 패턴, 미디어 소비 습관 등을 상세히 설명)

한국어로 작성해주세요.
"""
                }
            ]
        )
        # LLM 응답에서 답변만 추출
        llm_response = completion.choices[0].message.content
        
        return PersonaData(
            target_customer=customer,
            persona_description=llm_response,
            marketing_insights=""  # 마케팅 인사이트는 트렌드 데이터와 결합하여 생성할 예정
        )
        
    except Exception as e:
        print(f"⚠️ OpenAI API 호출 실패 (페르소나 생성): {e}")

# ==================================================================================
# LLM 기반 광고 영상 예시 프롬프트 생성 함수
async def create_ad_example(persona: PersonaData) -> str:
    """페르소나를 기반으로 LLM이 전문적인 광고 기획을 생성 (이미지 프롬프트 제외)"""
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": """
당신은 페르소나 분석에 기반하여 광고 전략을 수립하는 '광고 기획 전문가'입니다.
주어진 타겟 페르소나 정보를 깊이 있게 분석하여, 효과적인 광고 기획안을 작성해주세요.

**[작업 목표]**
페르소나 맞춤형 광고 컨셉과 전략을 기획하는 것입니다. (이미지 생성은 제외)

**[작업 수행 단계]**

**1단계: 페르소나 분석**
- 주어진 페르소나의 라이프스타일, 가치관, 소비 패턴, 고민(Pain Point)을 파악합니다.
- 이 페르소나가 어떤 메시지와 콘텐츠에 가장 크게 반응할지 예측합니다.

**2단계: 광고 컨셉 기획**
- 1단계 분석을 바탕으로, 아래 형식에 맞춰 광고 영상 컨셉을 구체적으로 작성합니다.
    - **[핵심 메시지]**: 페르소나의 마음을 사로잡을 단 한 줄의 매력적인 문장.
    - **[광고 컨셉]**: 제품/서비스가 페르소나의 일상에 어떻게 긍정적인 변화를 주는지 구체적인 스토리라인으로 설명.
    - **[영상 분위기]**: 영상의 전체적인 색감, 조명, 음악, 편집 스타일 등을 그려지듯 묘사.
    - **[타겟 반응 전략]**: 이 페르소나가 광고를 보고 어떤 감정을 느끼고, 어떤 행동을 하기를 기대하는지 명시.
    - **[차별화 포인트]**: 경쟁사 대비 우리만의 독특한 어필 포인트.

**3단계: 콘텐츠 구성안**
- 광고 영상의 전체적인 흐름과 구성을 제안합니다.
    - **[도입부]**: 시청자의 관심을 끌 방법
    - **[전개부]**: 문제 제기와 솔루션 제시 방법  
    - **[절정부]**: 가장 임팩트 있는 메시지 전달 방법
    - **[마무리]**: 행동 유도(CTA)와 기억에 남을 엔딩

**[준수 사항]**
- 모든 결과물은 한국어로 작성해야 합니다.
- 각 단계의 결과물은 제목과 함께 명확하게 구분하여 제시해야 합니다.
- 구체적이고 실행 가능한 아이디어를 제공해야 합니다.
"""
                },
                {
                    "role": "user",
                    "content": f"""
다음 타겟 페르소나를 분석하여 광고 기획안을 생성해주세요:

{persona.persona_description}

위 형식을 사용하여 이 페르소나에게 효과적일 구체적이고 창의적인 광고 기획을 제안해주세요.
한국어로 작성해주세요.
"""
                }
            ],
            temperature=0.8,
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        print(f"⚠️ OpenAI API 호출 실패 (광고 기획): {e}")

# ==================================================================================

# 3단계: 사용자 입력을 기반으로 장면별 이미지 생성 프롬프트 생성 (LangChain + Pydantic)
async def generate_scene_image_prompts_with_llm(user_description: str) -> StoryboardOutput:
    """사용자 입력을 기반으로 LLM이 장면을 나누고 각 장면별 이미지 생성 프롬프트를 생성 (LangChain 사용)"""
    
    try:
        # StoryboardOutput용 Pydantic Output Parser 설정
        parser = PydanticOutputParser(pydantic_object=StoryboardOutput)
        
        # 프롬프트 템플릿 생성
        prompt = PromptTemplate(
            template="""당신은 광고 영상 제작 전문가이자 AI 이미지 생성 프롬프트 전문가입니다.

사용자가 제공한 광고 영상 아이디어를 분석하여:
1. 먼저 3~6개의 장면으로 나누어 스토리를 구성
2. 각 장면별로 {SceneImagePrompt} 구조에 맞는 이미지 생성 프롬프트를 작성

프롬프트 작성 원칙:
- 핵심 요소만 명확히, 부차 항목은 필요할 때만 추가
- 큰 틀부터 채우고 세부사항은 점진적으로 작성
- 과도한 상세는 피하고 재현성 높은 키워드 사용

각 장면의 이미지 프롬프트는 다음 순서로 구성:
1. Subject (주체): @user의 상태, 의상, 액션
2. Scene (배경): 구체적인 장소와 환경
3. Composition (구도): 카메라 앵글과 프레이밍 (mid-shot, close-up, wide-shot 등)
4. Lighting (조명): 광원과 분위기 (natural light, warm lighting 등)
5. Style (스타일): 화풍과 매체 (cinematic, commercial photography 등)
6. Mood (무드): 감정과 분위기 (confident, friendly, energetic 등)

사용자 입력: {user_input}

{format_instructions}""",
            input_variables=["user_input"],
            partial_variables={
                "format_instructions": parser.get_format_instructions(),
                "SceneImagePrompt": "SceneImagePrompt"
            }
        )
        
        # 체인 생성 및 실행
        chain = prompt | llm | parser
        # invoke함수는 동기 ,ainvoke는 비동기
        result = await chain.ainvoke({"user_input": user_description})
        
        return result
            
    except Exception as e:
        print(f"⚠️ LangChain LLM 호출 실패 (장면 프롬프트 생성): {e}")
        raise e

# ==================================================================================
# Runway API 관련 import 추가
import httpx
import asyncio
import time
from typing import Optional

# ==================================================================================
# 4단계: Runway API를 활용한 실제 이미지 생성
async def generate_images_with_runway(storyboard: StoryboardOutput) -> StoryboardOutput:
    """Runway API를 사용해서 스토리보드의 각 장면을 실제 이미지로 생성"""
    
    runway_api_key = os.getenv("Runway_API_KEY")
    if not runway_api_key:
        raise ValueError("Runway_API_KEY 환경 변수가 설정되지 않았습니다.")
    
    print(f"🎬 총 {len(storyboard.scenes)} 장면의 이미지를 생성합니다...")
    
    # 각 장면별로 이미지 생성
    updated_scenes = []
    for i, scene in enumerate(storyboard.scenes, 1):
        print(f"\n🖼️ 장면 {i} 이미지 생성 중...")
        
        try:
            # Runway API로 이미지 생성 - SceneImagePrompt의 모든 필드 전달
            image_url = await create_image_with_runway(
                prompt_text=scene.image_prompt.promptText,
                ratio=scene.image_prompt.ratio,
                seed=scene.image_prompt.seed,
                model=scene.image_prompt.model,
                reference_images=[ref.model_dump() for ref in scene.image_prompt.referenceImages],
                public_figure_moderation=scene.image_prompt.publicFigureModeration,
                api_key=runway_api_key
            )
            
            # 생성된 이미지 URL을 장면에 추가
            scene.generated_image_url = image_url
            scene.generation_status = "success"
            print(f"✅ 장면 {i} 이미지 생성 완료: {image_url}")
            
        except Exception as e:
            print(f"❌ 장면 {i} 이미지 생성 실패: {e}")
            scene.generated_image_url = None
            scene.generation_status = "failed"
            scene.error_message = str(e)
        
        updated_scenes.append(scene)
        
        # API 호출 간격 조절 (Rate limiting 방지)
        if i < len(storyboard.scenes):
            await asyncio.sleep(2)
    
    # 업데이트된 장면들로 새 스토리보드 반환
    return StoryboardOutput(
        total_scenes=storyboard.total_scenes,
        estimated_duration=storyboard.estimated_duration,
        video_concept=storyboard.video_concept,
        scenes=updated_scenes
    )

async def create_image_with_runway(
    prompt_text: str,
    ratio: str = "16:9",
    seed: Optional[int] = None,
    model: str = "gen4_image",
    reference_images: List = None,
    public_figure_moderation: str = "auto",
    api_key: str = None
) -> str:
    """Runway API를 사용해서 단일 이미지 생성"""
    
    base_url = "https://api.dev.runwayml.com/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Runway-Version": "2024-11-06"  # API 버전 헤더 추가
    }
    
    # 요청 페이로드 구성
    payload = {
        "promptText": prompt_text,
        "ratio": ratio,
        "model": model
    }
    
    # 선택적 파라미터들 추가
    if seed is not None:
        payload["seed"] = seed
        
    if reference_images:
        payload["referenceImages"] = reference_images
        
    if public_figure_moderation != "auto":
        payload["publicFigureThreshold"] = public_figure_moderation
    
    async with httpx.AsyncClient(timeout=180) as client:  # 3분으로 단축
        # 1. 이미지 생성 작업 요청
        print(f"📤 Runway API 요청 중...")
        print(f"   프롬프트: {prompt_text}...")
        print(f"   비율: {ratio}, 모델: {model}")
        
        response = await client.post(
            f"{base_url}/text_to_image",
            headers=headers,
            json=payload
        )
        
        print(f"📋 API 응답 상태: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API 응답 내용: {response.text}")
            raise Exception(f"Runway API 요청 실패: {response.status_code} - {response.text}")
        
        task_data = response.json()
        task_id = task_data["id"]
        print(f"📋 작업 ID: {task_id}")
        
        # 2. 작업 완료까지 폴링
        max_attempts = 36  # 최대 3분 대기 (5초 * 36)
        for attempt in range(max_attempts):
            print(f"⏳ 이미지 생성 진행 확인 중... ({attempt + 1}/{max_attempts})")
            
            # 작업 상태 확인
            status_response = await client.get(
                f"{base_url}/tasks/{task_id}",
                headers=headers
            )
            
            if status_response.status_code != 200:
                print(f"❌ 상태 확인 실패: {status_response.status_code} - {status_response.text}")
                raise Exception(f"작업 상태 확인 실패: {status_response.status_code}")
            
            status_data = status_response.json()
            status = status_data.get("status")
            progress = status_data.get("progress", 0)
            
            print(f"   상태: {status}, 진행도: {progress}%")
            
            if status == "SUCCEEDED":
                # 성공! 이미지 URL 반환
                image_output = status_data.get("output")
                if not image_output:
                    raise Exception("이미지 URL을 찾을 수 없습니다.")
                
                # Runway API가 리스트로 반환하는 경우 첫 번째 요소 추출
                if isinstance(image_output, list) and len(image_output) > 0:
                    image_url = image_output[0]
                else:
                    image_url = image_output
                
                print(f"✅ 이미지 생성 완료: {image_url}")
                return image_url
                
            elif status == "FAILED":
                error_msg = status_data.get("error", "알 수 없는 오류")
                print(f"❌ 이미지 생성 실패: {error_msg}")
                raise Exception(f"이미지 생성 실패: {error_msg}")
                
            elif status in ["PENDING", "RUNNING"]:
                # 아직 진행 중, 5초 대기 후 재시도
                await asyncio.sleep(5)
                continue
            else:
                print(f"❌ 알 수 없는 상태: {status}")
                raise Exception(f"알 수 없는 작업 상태: {status}")
        
        # 최대 시도 횟수 초과
        print("❌ 이미지 생성 시간 초과")
        raise Exception("이미지 생성 시간 초과 (3분)")

# ==================================================================================