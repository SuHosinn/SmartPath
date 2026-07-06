import streamlit as st
import json
import os
import pandas as pd
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai
from pdf2image import convert_from_bytes
from fpdf import FPDF

load_dotenv(dotenv_path=".env")

st.set_page_config(page_title="스마트패쓰", layout="wide")
st.title("🎓 스마트패쓰 : AI 성적관리 시스템")

DATA_FILE = "student_data.json"
CONFIG_FILE = "exam_config.json"
SUBJECTS = ["국어", "수학", "사회", "과학", "영어", "한국사", "도덕", "한문"]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
# 이미지 분석을 위해 Pro 모델 사용
model = genai.GenerativeModel("gemini-2.5-flash")

def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if "students" not in st.session_state: st.session_state.students = load_json(DATA_FILE)
if "config" not in st.session_state: st.session_state.config = load_json(CONFIG_FILE)

# 1. 시험지 업로드 및 자동 파트 분석
st.header("📋 1. 시험지 분석 및 정답 등록")
subject = st.selectbox("과목 선택", SUBJECTS, key="subject_select")

# 여기서 변수명을 통일했습니다 (exam_file)
exam_file = st.file_uploader("시험지 업로드 (이미지 또는 PDF)", type=["png", "jpg", "jpeg", "pdf"], key="exam_upload")

if exam_file and st.button("시험지 파트 분석"):
    with st.spinner("AI가 파일을 분석 중입니다..."):
        try:
            # 1. PDF인 경우 fitz(PyMuPDF)로 이미지 변환
            if exam_file.type == "application/pdf":
                import fitz  # PyMuPDF
                doc = fitz.open(stream=exam_file.read(), filetype="pdf")
                page = doc.load_page(0)  # 첫 페이지
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            # 2. 이미지인 경우
            else:
                img = Image.open(exam_file)
            
            # 3. AI 분석 요청
            prompt = "이 시험지의 문제 번호별 파트(유형)를 분석해. JSON 형식으로만 답해 예를 들면 다음과 같이 해줘 수학 : {'1': '도형', '2': '다항식'}"
            response = model.generate_content([prompt, img])
            
            # 4. 저장
            map_data = json.loads(response.text.replace("```json", "").replace("```", ""))
            if subject not in st.session_state.config: 
                st.session_state.config[subject] = {"ans": [], "map": {}}
            st.session_state.config[subject]["map"] = map_data
            save_json(CONFIG_FILE, st.session_state.config)
            st.success("파트 분석 및 저장 완료!")
            
        except Exception as e:
            st.error(f"분석 중 오류 발생: {e}")


# 2. 학생 등록
st.header("학생 등록")
new_student = st.text_input("학생 이름")
if st.button("학생 추가"):
    if new_student and new_student not in st.session_state.students:
        st.session_state.students[new_student] = {}
        save_json(DATA_FILE, st.session_state.students)
        st.rerun()


# 3. 문제 정답 세팅
st.markdown("---")
st.header("✅ 채점 및 리포트 생성")
st.subheader("정답지를 입력하세요")
col1, col2 = st.columns(2)
with col1:
    num_questions = st.number_input("문제 개수", min_value=1, value=5)
# 문제 번호별 정답 입력 (동적으로 생성)
answer_key = {}
for i in range(num_questions):
    answer_key[str(i+1)] = st.selectbox(f"{i+1}번 정답", ["1","2","3","4","5"], key=f"key_{i}")

# 2. 채점하기 버튼
if st.button("채점하기"):
    # 수정된 답안은 이미 st.session_state에 들어있다고 가정 (key: edit_0, edit_1...)
    # AI가 인식한 답안과 비교하여 결과 생성
    score = 0
    report_lines = ["채점 리포트", "-----------"]
    
    for i in range(num_questions):
        q_num = str(i+1)
        # 사용자가 수정한 답안(selectbox)을 가져옴
        user_ans = st.session_state[f"edit_{i}"] 
        correct = answer_key[q_num]
        
        if user_ans == correct:
            score += 1
            result_str = f"{q_num}번: {user_ans} (정답) - O"
        else:
            result_str = f"{q_num}번: {user_ans} (오답, 정답:{correct}) - X"
        report_lines.append(result_str)
    
    report_lines.append(f"\n최종 점수: {score}/{num_questions}")
    
    # 리포트 저장
    st.session_state["report"] = "\n".join(report_lines)
    st.success(f"채점 완료! 점수: {score}/{num_questions}")

# 3. 리포트가 있으면 다운로드 버튼 표시
if "report" in st.session_state:
    st.text_area("결과 확인", st.session_state["report"], height=200)
    # ... (여기에 아까 만든 PDF 다운로드 버튼 코드 넣기) ...






# 4. 채점 (기존 로직 유지)
st.header("✅ 2. 학생 답안 채점 및 수정")

# 1. 데이터가 비어있을 경우 대비해서 예외 처리
if not st.session_state.students:
    st.warning("등록된 학생이 없습니다. 먼저 학생을 추가해주세요.")
    # 학생 추가하는 로직이 있다면 여기로 연결하거나, 학생 추가 섹션을 먼저 보여주세요.
else:
    # 2. key="student_select"를 추가하여 고유성 보장
    student = st.selectbox("학생 선택", list(st.session_state.students.keys()), key="student_select")
    student_img = st.file_uploader("학생 답안지 업로드", type=["png", "jpg", "jpeg"], key="student_upload")

    if student_img and st.button("AI 답안 인식"):
        img = Image.open(student_img)
        prompt = "이 답안지의 번호별 체크된 답을 읽어줘. 정답은 ① ② ③ ④ 중에 하나이고 답안지에는 V표시로 체크가 되어 있을거야. JSON 예시: {'answers': ['1', '2', '3']}"
        res = model.generate_content([prompt, img])
        
        # 인식값 세션 저장
        st.session_state["recognized"] = json.loads(res.text.replace("```json", "").replace("```", ""))["answers"]
        st.rerun() # 인식 후 바로 화면 갱신


# 5. 채점 및 수정
st.header("✅ 2. 학생 답안 채점 및 수정")
student = st.selectbox("학생 선택", list(st.session_state.students.keys()))
student_img = st.file_uploader("학생 답안지 업로드", type=["png", "jpg", "jpeg"], key="student")

if student_img and st.button("AI 답안 인식"):
    img = Image.open(student_img)
    prompt = "이 OMR 답안지의 번호별 체크된 답을 읽어줘. JSON 예시: {'answers': ['1', '2', '3']}"
    res = model.generate_content([prompt, img])
    st.session_state["recognized"] = json.loads(res.text.replace("```json", "").replace("```", ""))["answers"]

if "recognized" in st.session_state:
    st.subheader("인식 결과 수정")
    edited = []
    cols = st.columns(5)
    for i, ans in enumerate(st.session_state["recognized"]):
        with cols[i % 5]:
            val = st.selectbox(f"{i+1}번", ["1","2","3","4","5"], index=int(ans)-1, key=f"edit_{i}")
            edited.append(val)
    
    if st.button("최종 채점 및 결과 저장"):
        master = st.session_state.config[subject]["ans"]
        wrong_list = [i+1 for i, (s, m) in enumerate(zip(edited, master)) if s != m]
        st.session_state.students[student][subject] = {"wrong_qs": wrong_list, "answers": edited}
        save_json(DATA_FILE, st.session_state.students)
        st.success(f"채점 완료! 틀린 문제: {wrong_list}")
        st.session_state["last_result"] = {"wrong": wrong_list}


# 6. 상세 분석 로직
st.header("📊 AI 상세 성적 분석")

if st.button("상세 피드백 받기"):
    # 1. 데이터 가져오기
    student_data = st.session_state.students.get(student, {}).get(subject, {})
    wrong_qs = student_data.get("wrong_qs", [])
    map_data = st.session_state.config.get(subject, {}).get("map", {})
    wrong_parts = [map_data.get(str(q), "기타") for q in wrong_qs]
    
    # 2. AI 분석 요청 (선생님 요청 양식 강조)
    prompt = f"""
    [과목명]: {subject}
    틀린 문제의 파트들: {', '.join(wrong_parts)}
    위 정보를 바탕으로 학생에게 줄 따뜻하고 구체적인 학습 조언을 작성해줘.
    반드시 아래 형식을 지켜:
    
    [과목명]
    1. 분석: (틀린 파트에 대한 분석)
    2. 조언: (구체적인 공부 방법 5줄 내외)
    """
    
    report = model.generate_content(prompt).text
    st.markdown(report) # 화면에 출력
    st.session_state["report"] = report # PDF 저장을 위해 세션에 저장

# 3. PDF 다운로드 버튼
if "report" in st.session_state:
    if st.button("분석 리포트 PDF로 다운로드"):
        # 1. fpdf2 객체 생성
        pdf = FPDF()
        pdf.add_page()
        
        # 2. 한글 폰트 설정 (fpdf2 필수 설정)
        font_path = "C:/Windows/Fonts/malgun.ttf" # 윈도우 한글 폰트
        pdf.add_font("Malgun", "", font_path, uni=True)
        pdf.set_font("Malgun", size=12)
        
        # 3. PDF 내용 작성
        pdf.cell(200, 10, txt=f"Student Report: {student}", ln=True, align='C')
        pdf.ln(10)
        
        # 한글은 인코딩 변환 필요 없이 바로 입력 가능합니다.
        pdf.multi_cell(0, 10, txt=st.session_state["report"])
        
        # 4. PDF 데이터 생성 (fpdf2에서는 encode 필요 없음)
        pdf_output = bytes(pdf.output(dest='S'))
        
        # 5. 다운로드 버튼 표시
        st.download_button(
            label="PDF 파일 다운로드",
            data=pdf_output,
            file_name=f"{student}_{subject}_report.pdf",
            mime="application/pdf"
        )