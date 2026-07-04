student_list = ["김철수", "이영희", "박지성"] # 테스트용 학생 이름

def add_student(name):
    if name not in student_list:
        student_list.append(name)
        return True
    return False

def remove_student(name):
    if name in student_list:
        student_list.remove(name)
        return True
    return False