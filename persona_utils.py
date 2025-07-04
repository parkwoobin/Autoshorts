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
# OpenAI 채팅 모델용 Runnable 블록 - Runnable 규격 덕분에 invoke / ainvoke / batch / stream이 기본 탑재되어, 다른 LangChain 구성요소와 바로 이어 붙여 쓸 수 있음
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
    openai_api_key=OpenAI_API_KEY
)

# 외부 트렌드 데이터베이스 연동 인터페이스
async def get_trend_data(country: str, gender: str, age_range: List[str], interests: List[str]) -> dict:
    """
    외부 트렌드 데이터베이스에서 타겟 고객에 맞는 트렌드 데이터를 가져오는 인터페이스
    
    Args:
        country: 국가 정보
        gender: 성별
        age_range: 연령대 리스트 
        interests: 관심사 리스트
        
    Returns:
        dict: 트렌드 데이터베이스에서 가져온 트렌드 데이터
        
    Note:
        현재는 빈 dict 반환. 외부 트렌드 데이터베이스 API 연동 시 이 함수 내용만 교체하면 됨.
    """
    print(f"📊 트렌드 데이터베이스 연동 대기 중... (타겟: {country} {gender} {age_range} {interests})")
    
    # TODO: 외부 트렌드 데이터베이스 API 호출 로직으로 교체
    # 예시: 
    # async with httpx.AsyncClient() as client:
    #     response = await client.post("https://trend-db-api.com/query", json={
    #         "country": country, "gender": gender, "age_range": age_range, "interests": interests
    #     })
    #     return response.json()
    
    # 현재는 빈 데이터 반환 (LLM이 자체 판단으로 페르소나 생성하도록)
    return {}
# ==================================================================================

"""
    사용자 입력 1단계 : LangChain과 트렌드 데이터를 활용한 정교한 타겟 페르소나 생성
    1. 외부 트렌드 데이터베이스에서 데이터 조회
    2. LangChain OutputParser로 구조화된 페르소나 생성
    3. 트렌드 데이터 없을 시 LLM이 자체 판단으로 페르소나 생성
"""
async def generate_persona(customer: TargetCustomer) -> PersonaData:
    age_ranges_str = ", ".join(customer.age_range)
    interests_str = ", ".join(customer.interests)
    
    # 1단계: 외부 트렌드 데이터베이스에서 데이터 조회
    print("📊 트렌드 데이터베이스에서 데이터를 조회합니다...") # 디버깅용
    trend_data = await get_trend_data(
        country=customer.country,
        gender=customer.gender,
        age_range=customer.age_range,
        interests=customer.interests
    )
    
    # 트렌드 데이터를 문자열로 포매팅 (빈 데이터인 경우 "데이터 없음" 표시)
    import json
    if trend_data:
        trend_data_str = json.dumps(trend_data, indent=2, ensure_ascii=False)
        print("📈 트렌드 데이터 조회 완료")
    else:
        trend_data_str = "현재 트렌드 데이터가 없습니다. 전문 지식을 바탕으로 분석해주세요."
        print("📈 트렌드 데이터 없음 - LLM 자체 판단으로 진행")
    
    # 2단계: LangChain OutputParser 설정
    parser = PydanticOutputParser(pydantic_object=PersonaData)
    
    # 3단계: 프롬프트 템플릿 정의
    prompt = PromptTemplate(
        template="""
당신은 최신 트렌드에 정통한 전문 마케터이자 소비자 심리 분석가입니다.
주어진 타겟 고객 정보와 트렌드 데이터를 종합 분석하여, 광고 캠페인에 직접 활용할 수 있는 구체적이고 살아있는 페르소나를 생성해주세요.

### 타겟 고객 정보
- 국가/문화: {country}
- 연령대: {age_ranges}
- 성별: {gender}
- 언어/문화권: {language}
- 관심사: {interests}

### 트렌드 데이터
{trend_data}

### 생성 지침
**중요**: 트렌드 데이터가 비어있거나 부족한 경우, 당신의 전문 지식을 바탕으로 해당 타겟 고객층의 일반적인 특성을 분석하여 페르소나를 구성하세요.

응답은 다음 두 부분으로 명확히 분리해서 작성해주세요:

1. **persona_description**: 구체적인 페르소나 설명
   - 이름, 나이, 직업 등 기본 정보
   - 라이프스타일과 가치관
   - 소비 패턴과 미디어 이용 습관
   - 일상적인 행동과 관심사

2. **marketing_insights**: 이 페르소나를 대상으로 한 마케팅 전략
   - 효과적인 광고 메시지 방향성
   - 선호하는 광고 형식
   - 구매 결정 요인과 동기
   - 주의해야 할 마케팅 포인트

{format_instructions}
        """,
        input_variables=["country", "age_ranges", "gender", "language", "interests", "trend_data"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # 4단계: LangChain 체인 구성 및 실행
    chain = prompt | llm | parser
    
    print("🤖 LangChain을 통한 페르소나 생성 중...")
    result = await chain.ainvoke({
        # 타겟 고객 정보 전달
        "country": customer.country,
        "age_ranges": age_ranges_str,
        "gender": customer.gender,
        "language": customer.language,
        "interests": interests_str,
        "trend_data": trend_data_str
    })
    
    print("✅ 페르소나 생성 완료")
    return result

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