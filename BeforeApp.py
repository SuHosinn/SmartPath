import streamlit as st
import json
import os
import pandas as pd
from fpdf import FPDF
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(dotenv_path=".env")

st.set_page_config(page_title="스마트패쓰", layout="wide")
st.title("🎓 스마트패쓰 : AI 성적관리 시스템")

DATA_FILE = "student_data.json"
CONFIG_FILE = "exam_config.json"
SUBJECTS = ["국어", "수학", "사회", "과학", "영어", "한국사", "도덕", "한문"]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
vision_model = genai.GenerativeModel("gemini-2.5-pro")
analysis_model = genai.GenerativeModel("gemini-2.5-pro")

# [JSON 관리]
def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if "students" not in st.session_state: st.session_state.students = load_json(DATA_FILE)
if "config" not in st.session_state: st.session_state.config = load_json(CONFIG_FILE)

# [분석 함수] - 여기가 선생님이 원하시는 '시험지 보고 분석하는' 곳입니다.
def analyze_student_with_image(name, data, image_file):
    """학생 데이터와 시험지 이미지를 받아 AI가 직접 파트를 분석하고 피드백을 작성합니다."""
    img = Image.open(image_file)
    prompt = f"""
    이 시험지 이미지를 보고, 현재 학생의 틀린 문제 번호인 {data.get('틀린문제', [])}번 문제들이 각각 어떤 개념이나 파트인지 파악해.
    분석한 내용을 바탕으로 아래 형식으로 피드백을 작성해줘:
    [과목명]
    (문제 파트 기반의 구체적인 학습 조언 5줄 내외)
    """
    result = analysis_model.generate_content([prompt, img])
    return result.text

# [UI 구현]
st.header("학생 등록 및 채점")
# (학생 등록, 정답 입력 코드는 생략 - 기존 코드 그대로 사용)

# [채점 및 분석 화면]
uploaded = st.file_uploader("시험지 업로드", type=["png", "jpg", "jpeg"])
if uploaded and st.button("분석 및 피드백 받기"):
    # 1. 채점 로직 수행 (이미지 인식 및 정답 비교)
    # ... (기존 채점 로직 수행 후 result 딕셔너리 생성) ...
    
    # 2. 분석 실행 (이미지 직접 전달)
    report = analyze_student_with_image(student, result, uploaded)
    st.markdown("### 📊 AI 분석 결과")
    st.write(report)