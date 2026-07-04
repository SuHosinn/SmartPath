import streamlit as st
import json
import os
import pandas as pd
from fpdf import FPDF
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(dotenv_path=".env")

###########################################################
# 페이지 설정
###########################################################

st.set_page_config(
    page_title="스마트패쓰",
    layout="wide"
)

st.title("🎓 스마트패쓰 : AI 성적관리 시스템")

###########################################################
# 파일
###########################################################

DATA_FILE = "student_data.json"
CONFIG_FILE = "exam_config.json"

SUBJECTS = [
    "국어",
    "수학",
    "사회",
    "과학",
    "영어",
    "한국사",
    "도덕",
    "한문"
]

###########################################################
# Gemini
###########################################################

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)


if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY가 .env에 설정되지 않았습니다.")
    st.stop()

vision_model = genai.GenerativeModel("gemini-2.5-pro")
analysis_model = genai.GenerativeModel("gemini-2.5-pro")

###########################################################
# JSON
###########################################################

def load_json(file):

    if os.path.exists(file):

        with open(file,"r",encoding="utf-8") as f:

            return json.load(f)

    return {}



def save_json(file,data):

    with open(file,"w",encoding="utf-8") as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )

###########################################################
# 세션
###########################################################

if "students" not in st.session_state:

    st.session_state.students = load_json(DATA_FILE)

if "config" not in st.session_state:

    st.session_state.config = load_json(CONFIG_FILE)

###########################################################
# 학생 등록
###########################################################

st.header("학생 등록")

new_student = st.text_input("학생 이름")

if st.button("학생 추가"):

    if new_student == "":

        st.warning("학생 이름을 입력하세요.")

    elif new_student in st.session_state.students:

        st.warning("이미 등록된 학생입니다.")

    else:

        st.session_state.students[new_student] = {}

        save_json(
            DATA_FILE,
            st.session_state.students
        )

        st.success("학생 등록 완료")

###########################################################
# 정답 입력
###########################################################

st.header("과목별 정답 등록")

subject = st.selectbox(
    "과목 선택",
    SUBJECTS
)

old_answer = ",".join(

    st.session_state.config.get(subject,[])

)

answer = st.text_input(

    "정답 입력",

    value=old_answer,

    placeholder="1,2,3,4,5..."

)

if st.button("정답 저장"):

    ans = [

        x.strip()

        for x in answer.split(",")

        if x.strip()!=""

    ]

    st.session_state.config[subject] = ans

    save_json(

        CONFIG_FILE,

        st.session_state.config

    )

    st.success("정답 저장 완료")

###########################################################
# Gemini Vision
###########################################################

def recognize_answers(image):

    prompt = """
이 이미지는 OMR 답안지입니다.

학생이 체크한 답만 읽으세요.

JSON만 출력하세요.

{
 "answers":[
   "1",
   "2",
   "3",
   "4"
 ]
}

설명은 절대 쓰지 마세요.
"""

    img = Image.open(image)

    response = vision_model.generate_content(

        [

            prompt,

            img

        ]

    )

    text = response.text

    text = text.replace("```json","")

    text = text.replace("```","")

    text = text.strip()

    data = json.loads(text)

    return data["answers"]

###########################################################
# AI 분석
###########################################################

def analyze_student(name,data):

    prompt = f"""

학생 이름

{name}

학생 성적

{json.dumps(data,ensure_ascii=False)}

다음을 작성하세요.

1. 전체 학습 수준

2. 강점

3. 약점

4. 공부 방법

5. 다음 시험 대비

한국어로 자세히 작성.
"""

    result = analysis_model.generate_content(

        prompt

    )

    return result.text

###########################################################
# 채점 화면
###########################################################

st.header("답안 업로드")

if len(st.session_state.students)==0:

    st.info("학생을 먼저 등록하세요.")

    st.stop()

student = st.selectbox(

    "학생",

    list(st.session_state.students.keys())

)

subject2 = st.selectbox(

    "채점 과목",

    SUBJECTS,

    key="subject2"

)

uploaded = st.file_uploader(

    "답안 업로드",

    type=["png","jpg","jpeg"]

)

###########################################################
# AI 답안 인식
###########################################################

if uploaded is not None:

    if st.button("AI 답안 인식"):

        with st.spinner("답안을 인식하는 중입니다..."):

            try:

                answers = recognize_answers(uploaded)

                st.session_state["recognized_answers"] = answers

                st.success("답안 인식 완료!")

            except Exception as e:

                st.error(e)

###########################################################
# 사람이 수정
###########################################################

if "recognized_answers" in st.session_state:

    st.subheader("AI 인식 결과")

    answers = st.session_state["recognized_answers"]

    edited_answers = []

    cols = st.columns(5)

    for i, ans in enumerate(answers):

        with cols[i % 5]:

            try:

                idx = int(ans)-1

            except:

                idx = 0

            edit = st.selectbox(

                f"{i+1}번",

                ["1","2","3","4","5"],

                index=idx,

                key=f"edit_{i}"

            )

            edited_answers.append(edit)

###########################################################
# 채점
###########################################################

    if st.button("수정 완료 후 채점"):

        if subject2 not in st.session_state.config:

            st.error("정답지가 등록되지 않았습니다.")

            st.stop()

        master = st.session_state.config[subject2]

        length = min(

            len(master),

            len(edited_answers)

        )

        correct = 0

        wrong_list = []

        for i in range(length):

            if edited_answers[i] == master[i]:

                correct += 1

            else:

                wrong_list.append(i+1)

        score = round(

            correct / length * 100,

            1

        )

        result = {

            "점수":score,

            "맞은문제":correct,

            "total":length,

            "틀린문제":wrong_list,

            "student_answers":edited_answers

        }

        st.session_state.students[student][subject2] = result

        save_json(

            DATA_FILE,

            st.session_state.students

        )

        st.success(f"채점 완료! {score}점")

###########################################################
# 결과 출력
###########################################################

        st.subheader("채점 결과")

        c1,c2,c3 = st.columns(3)

        c1.metric(

            "점수",

            f"{score}점"

        )

        c2.metric(

            "정답",

            correct

        )

        c3.metric(

            "오답",

            len(wrong_list)

        )

        if len(wrong_list)==0:

            st.success("전부 정답입니다!")

        else:

            st.warning(

                "오답 번호 : " +

                ", ".join(

                    map(str,wrong_list)

                )

            )

###########################################################
# 학생 성적 조회
###########################################################

st.header("학생 성적")

if len(st.session_state.students)>0:

    student2 = st.selectbox(

        "조회 학생",

        list(st.session_state.students.keys()),

        key="lookup"

    )

    if len(

        st.session_state.students[student2]

    )>0:

        df = pd.DataFrame(

            st.session_state.students[student2]

        ).T

        st.dataframe(

            df,

            use_container_width=True

        )

    else:

        st.info("성적이 없습니다.")

###########################################################
# AI 성적 분석 버튼
###########################################################

st.header("AI 성적 분석")

if len(st.session_state.students) > 0:

    student3 = st.selectbox(
        "분석 학생 선택",
        list(st.session_state.students.keys()),
        key="analysis_student"
    )

    if st.button("Gemini 분석 실행"):

        try:

            report = analyze_student(
                student3,
                st.session_state.students[student3]
            )

            st.session_state["report"] = report

            st.success("분석 완료")

            st.markdown("### 📊 AI 분석 결과")

            st.write(report)

        except Exception as e:

            st.error(str(e))

###########################################################
# PDF 생성
###########################################################

st.header("PDF 리포트 다운로드")

def make_pdf(name, data, report):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=f"{name} 성적 리포트", ln=True, align="C")

    pdf.ln(10)

    for subject, info in data.items():

        pdf.cell(
            200,
            10,
            txt=f"{subject}: {info['score']}점",
            ln=True
        )

    pdf.ln(5)

    pdf.multi_cell(
        0,
        10,
        txt="AI 분석 결과:\n\n" + (report or "")
    )

    return pdf.output(dest="S").encode("latin-1")


if len(st.session_state.students) > 0:

    pdf_student = st.selectbox(
        "PDF 생성 학생",
        list(st.session_state.students.keys()),
        key="pdf_student"
    )

    if st.button("PDF 생성"):

        try:

            report_text = st.session_state.get("report","")

            pdf_bytes = make_pdf(
                pdf_student,
                st.session_state.students[pdf_student],
                report_text
            )

            st.download_button(
                label="PDF 다운로드",
                data=pdf_bytes,
                file_name=f"{pdf_student}_report.pdf",
                mime="application/pdf"
            )

            st.success("PDF 생성 완료")

        except Exception as e:

            st.error(str(e))

###########################################################
# 안전 초기 안내
###########################################################

st.markdown("---")

st.info(
"""
✔ Gemini Vision: 답안 인식  
✔ 사람이 수정 후 채점  
✔ 자동 점수 계산  
✔ AI 성적 분석  
✔ PDF 리포트 생성  

"""
)