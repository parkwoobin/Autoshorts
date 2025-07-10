"""
페르소나 생성 및 LLM 관련 유틸리티 함수들 - 정리된 LangChain 통합 버전
비용 효율성과 코드 간소화에 중점을 둔 리팩토링
"""
from typing import List,Dict
from models import (
    TargetCustomer, PersonaData, ReferenceImageWithDescription,
    ReferenceImage, SceneImagePrompt, StoryboardOutput
)
import os
from dotenv import load_dotenv
import asyncio
import httpx

# LangChain imports
# 
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 가져오기
OpenAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 비용 효율적인 LLM 설정
# 텍스트 생성용 - 사용자가 요청한 모델로 변경
text_llm = ChatOpenAI(
    model="gpt-4.1-nano-2025-04-14",  # 비용 효율적인 모델
    openai_api_key=OpenAI_API_KEY,
    temperature=0.7
)

# 이미지 분석용 모델 설정
vision_llm = ChatOpenAI(
    model="gpt-4o",  # 이미지 분석 전용
    openai_api_key=OpenAI_API_KEY,
    temperature=0.2  # 낮은 온도는 이미지처럼 객관적인 묘사에 유리 -> 온도가 높으면 창의적이지만 주관적인 해석이 섞인 답변이 나올 수 있음
)

# 외부 트렌드 데이터베이스 연동 인터페이스
# ==================================================================================
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
    1. 외부 트렌드 데이터베이스에서 데이터 조회 - 추후 구현
    2. LangChain OutputParser로 구조화된 페르소나 생성
    3. 트렌드 데이터 없을 시 LLM이 자체 판단으로 페르소나 생성
"""
async def generate_persona(customer: TargetCustomer) -> PersonaData:
    # LLM에게 리스트형태로 전달하는것보다는 문자열로 전달하는 것이 더 효율적임
    age_ranges_str = ", ".join(customer.age_range)
    interests_str = ", ".join(customer.interests) if customer.interests else "없음"
    
    # 외부 트렌드 데이터베이스에서 데이터 조회
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
        trend_data_str = "트렌드 데이터가 없습니다. 전문 지식을 바탕으로 분석해주세요."
        print("📈 트렌드 데이터 없음 - LLM 자체 판단으로 진행")
    
    # LangChain OutputParser 설정했더니 됐다가 안됐다가 함 프롬프트 템플릿 안에 출력 구조 지침과 지시사항을 같이 입력하다보니 헷갈려서 비어있는 출력 포맷으로 답변할 때가 있음
    # OutputParser 대신 with_structured_output()사용이 권장됨
    # LLM의 응답을 PersonaData 모델 형식으로 구조화
    # parser = PydanticOutputParser(pydantic_object=PersonaData)
    
    # LLM에게 전달할 프롬프트 템플릿 정의
    # 시스템 메시지: AI의 역할과 핵심 지시사항 정의
    system_template = """
    당신은 최신 트렌드에 정통한 전문 마케터이자 소비자 심리 분석가입니다.
    주어진 타겟 고객 정보와 트렌드 데이터를 종합 분석하여, 광고 숏폼 기획에 직접 활용할 수 있는 구체적이고 살아있는 페르소나를 생성해주세요.

    ### 생성 지침
    **중요**: 트렌드 데이터가 비어있거나 부족한 경우, 당신의 전문 지식을 바탕으로 해당 타겟 고객층의 일반적인 특성을 분석하여 페르소나를 구성하세요.
    응답은 다음 세 부분으로 명확히 분리해서 작성해주세요:
    1. **target_customer**: 입력받은 타겟 고객 정보 그대로 반영
    2. **persona_description**: 구체적인 페르소나 설명 (이름, 나이, 직업, 라이프스타일, 소비 패턴 등)
    3. **marketing_insights**: 이 페르소나를 대상으로 한 마케팅 전략 (효과적인 메시지, 선호 광고 형식 등)
    """
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)

     # 변하는 실제 데이터 부분 정의
    human_template = """
    ### 타겟 고객 정보
    - 국가/문화: {country}
    - 연령대: {age_ranges}
    - 성별: {gender}
    - 언어/문화권: {language}
    - 관심사: {interests}

    ### 트렌드 데이터
    {trend_data}
    """
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    # 3. ChatPromptTemplate으로 시스템과 사용자 메시지를 조합
    prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

    # Pydantic 모델(PersonaData)을 LLM에 직접 바인딩하여 JSON 모드 활성화 (Tool Calling 기능)
    # 체인의 최종 출력 구조는 PersonaData가 됨
    structured_llm = text_llm.with_structured_output(PersonaData)

    # LangChain 체인 재구성 
    chain = prompt | structured_llm

    print("🤖 LangChain을 통한 페르소나 생성 중...")
    # ainvoke는 비동기 호출
    result = await chain.ainvoke({
    "country": customer.country,
    "age_ranges": age_ranges_str,
    "gender": customer.gender,
    "language": customer.language,
    "interests": interests_str,
    "trend_data": trend_data_str
    })

    return result

# ==================================================================================
""" 
    페르소나, 마케팅 인사이트, 참조 이미지를 바탕으로 LLM이 광고 컨셉 생성
    이 단계의 목적 : 생성된 광고 예시 템플릿에 맞춰 사용자가 손쉽게 수정·확장할 수 있는 가이드라인을 제공
"""
async def create_ad_concept(persona: PersonaData, reference_images: List[ReferenceImage] = None) -> str:
    
    # 참조 이미지 분석 (있는 경우만)
    image_analysis = ""
    analyzed_images = []
    if reference_images:
        print(f"🔍 {len(reference_images)}개의 참조 이미지 분석 중...")
        # 참조 이미지 분석 결과는 리스트안에 딕셔너리로 담겨 있음
        analyzed_images = await analyze_reference_images(reference_images)
        print("✅ 참조 이미지 결과 디버깅")
        print(analyzed_images)  # 디버깅용 출력
        # 참조 이미지 분석 결과를 그대로 프롬프트에 넣을 수 없으므로 문자열로 변환
        image_analysis = "\n### 📸 참조 이미지 분석\n"
        for img in analyzed_images:
            # ex) product : 미니멀한 디자인의 흰색 병. 깨끗하고 고급스러운 느낌을 준다.
            image_analysis += f"**{img['tag']}**: {img['analysis']}\n"
    
    # 시스템 메시지 : AI의 역할과 출력 형식 지시
    system_template = """
    당신은 뛰어난 광고 기획 전문가입니다.
    주어진 데이터를 바탕으로, 타겟 고객을 사로잡을 효과적인 광고 컨셉을 제안해주세요.

    ### 중요 지침
    - '참조 이미지 분석' 섹션이 입력 데이터에 **있는 경우에만**, 해당 내용을 '핵심 활용 전략'에 반영하세요.
    - '참조 이미지 분석' 섹션이 **없다면**, 절대 참조 이미지에 대해 언급하지 마세요.
    
    ### 제안할 광고 컨셉 포맷
    아래 포맷을 반드시 준수하여, 각 항목에 대해 깊이 있는 내용을 제안해주세요.
    **✨ 광고 한 줄 요약 (Catchy One-liner)**
    : 광고 전체를 관통하는, 귀에 꽂히는 한 문장 캐치프레이즈.
    **🎯 핵심 메시지 (Core Message)**
    : 이 광고를 통해 타겟 고객의 어떤 감정이나 욕구를 건드릴 것인지 명확히 서술.
    **🎬 크리에이티브 컨셉 (Creative Concept)**
    : 광고의 구체적인 시나리오나 스토리. 짧지만 강력한 내러티브를 제시.
    **🎨 영상 분위기 (Visual Mood & Tone)**
    : 영상의 색감, 속도, 사운드 등 전체적인 시각적, 청각적 스타일.
    **💡 핵심 활용 전략 (Key Strategy)**
    : (만약 '참조 이미지 분석' 내용이 있다면) 타겟 고객 마케팅 인사이트와 참조 이미지의 강점을 어떻게 결합할지 서술.
    : (만약 '참조 이미지 분석' 내용이 없다면) 오직 페르소나의 특징과 마케팅 인사이트만을 활용한 창의적인 확산 전략을 제안.
    """
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)

    # 사용자 메시지: 분석할 데이터 전달
    human_template = """
    아래 데이터를 바탕으로 광고 컨셉 제안을 시작해주세요.

    ### 타겟 고객 페르소나
    {persona_description}

    ### 타겟 고객 마케팅 인사이트
    {marketing_insights}

    {image_analysis}
"""
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    # ChatPromptTemplate으로 조합
    concept_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
    # Pydantic 모델 정의 안하고 출력 구조를 명시하지 않아서 LLM이 자유롭게 답변할 수 있도록 함
    # 체인의 최종 출려 구조는 LLM의 답변이 됨 
    concept_chain = concept_prompt | text_llm
    
    print("💡 광고 컨셉 생성 중...")
    result = await concept_chain.ainvoke({
        "persona_description": persona.persona_description,
        "marketing_insights": persona.marketing_insights,
        "image_analysis": image_analysis
    })
    
    print("✅ 광고 컨셉 생성 완료")
    #LLM의 답변만 가져오기 위해 content 속성 사용
    return {
        "ad_concept": result.content,
        "image_analyses": analyzed_images
    }

# ==================================================================================
"""
    사용자가 앞선 단계에서 생성된 광고 컨셉 프롬프트를 기반으로 광고 제작 아이디어를 작성
    사용자의 광고 아이디어를 기반으로 LLM이 장면별 프롬프트 생성
"""
# Dict[str,str] 타입힌트 사용 -> 참조 이미지 분석 결과를 딕셔너리 형태로 전달
async def generate_scene_prompts(user_description: str, enriched_images: List[ReferenceImageWithDescription]) -> StoryboardOutput:

    # AI 분석 결과를 바탕으로 프롬프트에 포함시킬 문자열 준비
    reference_info = ""
    if enriched_images:
        reference_info = "\n### 📸 사용 가능한 참조 이미지 정보 (JSON 형식)\n"
        for ref_img in enriched_images:
            # model_dump_json을 사용해 Pydantic 객체를 읽기 좋은 JSON 문자열로 변환
            reference_info += f"- @{ref_img.tag}: {ref_img.model_dump_json(indent=2)}\n"
        reference_info += "\n"

    # 시스템 메시지: AI의 역할과 데이터 '변환' 지시사항 강화
    # persona_utils.py 파일의 generate_scene_prompts 함수 내부

    system_template = """
    당신은 AI 스토리보드 생성 전문가이자, AI 이미지 생성 프롬프트 엔지니어입니다.
    사용자의 아이디어와 아래 JSON 형식으로 제공된 참조 이미지 정보를 분석하여, 3개의 장면으로 구성된 완전한 `StoryboardOutput` JSON 객체를 생성해야 합니다.

    ### ⭐ 가장 중요한 작성 원칙
    - **`prompt_text`는 영어로 작성**: `scenes` 안의 모든 `prompt_text` 필드는 이미지 생성 AI가 더 잘 이해할 수 있도록 **반드시 영어로 작성**해주세요.
    - **나머지 필드는 한국어로 작성**: `video_concept`과 같은 다른 모든 텍스트 필드는 한국어로 작성합니다.

    ### 🚨 가장 중요한 규칙: 참조 이미지 처리 방법

    **1. 창의적 판단 우선 (Creative Judgment First):**
    - 참조 이미지 사용은 **선택 사항**이며, 필수가 아닙니다.
    - 오직 해당 장면의 아이디어를 **더욱 강화하거나 명확하게 전달**하는 데 도움이 된다고 판단될 때만 이미지를 사용하세요.
    - 만약 참조 이미지를 사용하는 것보다 텍스트 프롬프트만으로 장면을 묘사하는 것이 더 창의적이거나 효과적이라면, **과감하게 사용하지 마세요.** 이 경우 **`reference_images` 키를 아예 포함하지 마세요**(빈 리스트도 금지).

    **2. 참조 이미지 사용 시 준수 사항 (Rules for When You *Do* Use an Image):**
    - **두 가지 작업(`prompt_text`에 @태그 포함, `reference_images` 리스트 채우기)을 한 세트로 반드시 수행**해야 합니다.
    - 최종 `reference_images` 리스트에는 `analysis` 필드를 제외하고 `uri`와 `tag`만 포함시켜야 합니다.

    **3. 참조 이미지가 처음부터 없는 경우 (When No Images are Provided at All):**
    - '사용 가능한 참조 이미지 정보'가 비어있다면, 모든 장면에서 `reference_images` 키를 넣지 마세요.

    ### 📝 최종 출력 구조 (StoryboardOutput)
    당신은 반드시 아래 설명된 `StoryboardOutput` 전체 구조에 맞는 JSON 객체 하나만 출력해야 합니다. 다른 텍스트는 절대 추가하지 마세요.

    - `scenes` (필수): `SceneImagePrompt` 구조를 따르는 장면 객체들의 목록.
    - `total_scenes` (필수): 생성된 총 장면의 수 3.
    - `estimated_duration` (필수): 전체 영상의 예상 길이 (초 단위 정수, 장면당 5초로 계산).
    - `video_concept` (필수): 광고 영상의 핵심 컨셉을 1~2문장으로 요약.

    #### 전체 출력 예시 (이 구조와 필드 이름을 반드시 따르세요):
    {{
    "scenes": [
        {{
        "model": "gen4_image",
        "prompt_text": "A modern, minimalist cafe exterior with natural sunlight.@background",
        "ratio": "1280:720",
        "reference_images": [
            {{
            "uri": "https://...",
            "tag": "background"
            }}
        ],
        "seed": 42,
        }},
        {{
        "model": "gen4_image",
        "prompt_text": "A close-up shot of @product, a delicious-looking jokbal dish.",
        "ratio": "1280:720",
        "seed": 42
        }}
    ],
    "total_scenes": 2,
    "estimated_duration": 10,
    "video_concept": "바쁜 일상 속, 맛있는 음식과 함께하는 여유로운 순간을 통해 얻는 행복을 표현합니다."
    }}

    [최종 확인 지시]
    출력하기 전, 당신이 생성한 JSON이 `scenes`, `total_scenes`, `estimated_duration`, `video_concept` 필드를 모두 포함하고 있는지 반드시 다시 한번 확인하십시오.
    - `reference_images` 리스트에 객체가 있다면, 같은 장면의 `prompt_text`에 해당 `@태그`가 반드시 포함되어 있습니까?
    - 참조 이미지를 사용하지 않는 장면에는 `reference_images` 키가 없는지 확인했습니까?
    """
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)

    # 사용자 메시지 템플릿
    human_template = """
    ### 💬 사용자의 광고 아이디어
    {user_description}
    {reference_info}
    ---
    위 아이디어와 참조 이미지 정보를 바탕으로, 지침에 따라 완전한 스토리보드 JSON 객체를 생성해주십시오.
    """
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
    
    # 체인 구성
    storyboard_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
    structured_llm = text_llm.with_structured_output(StoryboardOutput)
    storyboard_chain = storyboard_prompt | structured_llm

    print("🎬 장면별 프롬프트 생성 중...")
    
    result = await storyboard_chain.ainvoke({
        "user_description": user_description,
        "reference_info": reference_info,
    })

    print("✅ 장면별 프롬프트 생성 완료")
    return result

# ==================================================================================
"""스토리보드 장면 이미지를 Runway API로 생성"""
async def generate_images_sequentially(
    scenes: List[SceneImagePrompt],
    api_key: str
) -> List[Dict]:
    """여러 장면 프롬프트를 받아 '직렬'로 이미지 생성을 요청하고 모든 결과를 반환합니다."""
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json","X-Runway-Version": "2024-11-06"}
    base_url = "https://api.dev.runwayml.com/v1"
    
    generated_images = []
    total_scenes = len(scenes)
    
    print(f"\n🚀 총 {total_scenes}개의 이미지 생성을 직렬로 시작합니다...")

    for i, scene in enumerate(scenes):
        print(f"\n--- [장면 {i+1}/{total_scenes}] 생성 시작 ---")
        
        payload = scene.model_dump(by_alias=True, exclude_none=True)
        
        if payload.get("referenceImages"):
            for ref_img_dict in payload["referenceImages"]:
                ref_img_dict["weight"] = 0.5

        async with httpx.AsyncClient(timeout=180) as client:
            try:
                # 1. 작업 요청
                print(f"📤 Runway API 요청: {scene.prompt_text[:40]}...")
                response = await client.post(f"{base_url}/text_to_image", headers=headers, json=payload)
                
                if response.status_code != 200:
                    raise Exception(f"API 요청 실패: {response.text}")
                
                task_id = response.json()["id"]
                print(f"  -> 작업 ID: {task_id}")

                # 2. 작업 완료까지 폴링
                for attempt in range(36):
                    print(f"⏳ 이미지 생성 진행 확인 중... ({attempt + 1}/{36})")
                    status_response = await client.get(f"{base_url}/tasks/{task_id}", headers=headers)
                    status_data = status_response.json()
                    status = status_data.get("status")
                    progress = status_data.get("progress", 0)
                    print(f"   상태: {status}, 진행도: {progress}%")

                    if status == "SUCCEEDED":
                        print(f"✅ [장면 {i+1}] 이미지 생성 완료!")
                        generated_images.append({
                            "scene_index": i + 1,
                            "status": "success",
                            "image_url": status_data.get("output", [None])[0],
                            "prompt": scene.prompt_text
                        })
                        break
                    elif status == "FAILED":
                        error_msg = status_data.get("error", "알 수 없는 오류")
                        print(f"❌ [장면 {i+1}] 이미지 생성 실패: {error_msg}")
                        generated_images.append({"scene_index": i + 1, "status": "failed", "error": error_msg, "prompt": scene.prompt_text})
                        break
                    
                    await asyncio.sleep(5)
                else:
                    raise Exception("이미지 생성 시간 초과")

            except Exception as e:
                print(f"❌ [장면 {i+1}] 처리 중 오류 발생: {e}")
                generated_images.append({"scene_index": i + 1, "status": "error", "error": str(e), "prompt": scene.prompt_text})

    print("\n🎉 모든 이미지 생성 작업 완료!")
    return generated_images
# ==================================================================================

"""참조 이미지 분석 : 참조 이미지를 분석해 광고 콘셉트 및 크리에이티브 방향성을 도출"""
async def analyze_reference_images(reference_images: List[ReferenceImage]) -> List[dict]:
    if not reference_images:
        return []
    # 분석 결과 저장할 변수
    analyzed_result = []
    
    for ref_image in reference_images:
        try:
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": f"""이 이미지를 {ref_image.tag}로 광고에 활용하려고 합니다.
                        주요 특징과 광고 활용 포인트를 분석해주세요"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": ref_image.uri,
                            "detail": "auto"  # low와 high가 있음 , 핵심은 이미지의 세부적인 부분까지 분석이 가능하냐마냐의 차이
                        }
                    }
                ]
            )
            # LLM에 이미지 분석 요청
            result = await vision_llm.ainvoke([message])
            
            analyzed_result.append({
                "tag": ref_image.tag,
                "uri": ref_image.uri,
                "analysis": result.content
            })
            print(f"✅ @{ref_image.tag} 분석 완료")
            
        except Exception as e:
            print(f"⚠️ @{ref_image.tag} 분석 실패: {e}")
            analyzed_result.append({
                "tag": ref_image.tag,
                "uri": ref_image.uri,
                "analysis": "이미지 분석을 수행할 수 없습니다."
            })
    
    return analyzed_result

# ==================================================================================