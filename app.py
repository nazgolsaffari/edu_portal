from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
import jdatetime
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'xyz_123'  

# مسیر فایل‌ها
DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
COURSE_FILE = os.path.join(DATA_DIR, 'courses.json')
STUDENTS_FILE = os.path.join(DATA_DIR, 'students.json')
UPLOAD_FOLDER = 'static/media/'

# اطمینان از وجود پوشه data
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# اطمینان از وجود فایل‌ها
for file_path in [USERS_FILE, COURSE_FILE, STUDENTS_FILE]:
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

# خواندن اطلاعات کاربران
def load_users():
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

# خواندن اطلاعات دانش‌آموزان
def load_students():
    with open(STUDENTS_FILE, encoding='utf-8') as f:
        return json.load(f)

def save_students(data):
    with open(STUDENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# خواندن دوره‌ها
def load_courses():
    try:
        with open(COURSE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

# ذخیره دوره‌ها
def save_courses(data):
    with open(COURSE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# دسته‌بندی دوره‌ها
def categorize_courses(courses_dict):
    levels = []
    elevels = []
    for level in courses_dict:
        if level.startswith('E'):
            elevels.append(level)
        else:
            levels.append(level)
    return levels, elevels

# تبدیل تاریخ میلادی به جلالی
def miladi_to_jalali(miladi_str):
    try:
        date_obj = datetime.strptime(miladi_str, "%Y-%m-%d")
        jalali = jdatetime.date.fromgregorian(date=date_obj)
        return jalali.strftime('%Y/%m/%d')
    except:
        return miladi_str

# بررسی پاس کردن سطح
def has_passed(student_username, level):
    students = load_students()
    student = students.get(student_username)
    if not student:
        return False
    return student.get('courses', {}).get(level, {}).get('passed', False)

# دریافت سطوح پاس‌شده توسط دانش‌آموز
def get_passed_levels(student_username):
    students = load_students()
    student = students.get(student_username)
    if not student:
        return []
    return [level for level, info in student.get('courses', {}).items() if info.get('passed')]

#بارگذاری و ذخیره ی محتویات دوره ها
def load_course_details():
    return load_courses()

def load_course_content(level):
    with open('data/course_content.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get(level, [])

def save_course_content(content):
    with open('data/course_content.json', 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)


def load_all_course_contents():
    with open('data/course_content.json', 'r', encoding='utf-8') as f:
        return json.load(f)

#گرفتن نام کامل کاربر
def get_full_name(username):
    users = load_users()  
    user = users.get(username, {})
    return user.get('full_name', username)


# صفحه‌ی اصلی
@app.route('/')
def home():
    course_data = load_course_details()

    # فیلدهایی که باید کامل باشند
    required_fields = ["title", "start_date", "duration_weeks", "schedule", "capacity", "teacher"]

    # فیلتر کردن فقط دوره‌هایی که اطلاعات کامل دارند
    complete_course_data = {
        level: info for level, info in course_data.items()
        if all(field in info and info[field] for field in required_fields)
    }

    # دسته‌بندی پس از فیلتر
    levels, elevels = categorize_courses(complete_course_data)

    return render_template("home.html", levels=levels, elevels=elevels)


# ثبت‌نام کاربر جدید
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    next_page = request.args.get('next')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form['full_name']
        phone = request.form['phone']
        email = request.form['email']
        national_id = request.form['national_id']

        if not os.path.exists(USERS_FILE):
            users = {}
        else:
            with open(USERS_FILE, 'r') as f:
                users = json.load(f)

        if username in users:
            error = 'این نام کاربری قبلاً ثبت شده است.'
        else:
            users[username] = {
                'password': password,
                'confirm_password': confirm_password,
                'role': 'student',
                'learning': [],
                'full_name': full_name,
                'phone': phone,
                'email': email,
                'national_id': national_id
            }

            with open(USERS_FILE, 'w') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)

            session['username'] = username
            return redirect(url_for('login'))

    return render_template('register.html', error=error, next=next_page)


# ورود
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    next_page = request.args.get('next')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']  

        users = load_users()

        if username in users:
            user_data = users[username]

            if user_data['password'] == password:
                if user_data.get('role') != role:
                    error = 'نقش انتخاب‌شده با نقش ثبت‌شده در سیستم مطابقت ندارد.'
                else:
                    session['username'] = username
                    session['role'] = role  
                    return redirect(next_page or url_for('profile'))
            else:
                error = 'رمز عبور اشتباه است.'
        else:
            error = 'نام کاربری یافت نشد.'

    return render_template('login.html', error=error)

#ورود به پنل مدیر
@app.route('/admin-panel')
def admin_panel():
    if session.get('role') != 'admin':
        return "شما به این بخش دسترسی ندارید.", 403
    return render_template('admin_panel.html')

#افزودن عنوان سطح جدید 
@app.route('/admin/add_course_title', methods=['GET', 'POST'])
def add_course_title():
    if session.get('role') != 'admin':
        return "دسترسی غیرمجاز", 403

    error = None
    success = False

    if request.method == 'POST':
        level = request.form['level'].strip()
        title = request.form['title'].strip()

        if not level or not title:
            error = "هر دو فیلد الزامی هستند."
        else:
            courses = load_courses()
            if level in courses:
                error = f"موضوعی با کلید {level} قبلاً وجود دارد."
            else:
                
                courses[level] = {
                    "title": title
                }
                save_courses(courses)
                success = True
                return redirect(url_for('profile'))

    return render_template("admin/add_course_title.html", error=error, success=success)

#افزودن دوره‌ی جدید
@app.route('/admin/add_course', methods=['GET', 'POST'])
def add_course():
    if session.get('role') != 'admin':
        return "دسترسی غیرمجاز", 403

    error = None
    success = False

    users = load_users()
    courses = load_courses()

    # لیست تمام سطح‌ها از courses
    levels = list(courses.keys())

    # لیست همه معلم‌ها و دوره‌هایی که دارند
    teacher_courses = {
        username: data.get('courses', [])
        for username, data in users.items()
        if data.get('role') == 'teacher'
    }

    # لیست همه معلم‌ها: username -> full_name
    teachers = {
        username: data.get('full_name', username)
        for username, data in users.items()
        if data.get('role') == 'teacher'
    }

    if request.method == 'POST':
        level = request.form['level']
        title = request.form['title']
        start_date = request.form['start_date']
        duration = int(request.form['duration'])
        schedule = request.form['schedule']
        prerequisites = request.form['prerequisites']
        capacity = int(request.form['capacity'])
        selected_teacher = request.form.get('teacher')

        if level in courses:
        
            courses[level] = {
                "title": title,
                "start_date": start_date,
                "duration_weeks": duration,
                "schedule": schedule,
                "prerequisites": prerequisites,
                "capacity": capacity,
                "teacher": selected_teacher
            }
            save_courses(courses)
            return redirect(url_for('profile'))

    return render_template(
        'admin/add_course.html',
        error=error,
        success=success,
        levels=levels,
        teacher_courses=teacher_courses,
        teachers=teachers
    )

#ویرایش دوره
@app.route('/admin/edit_course/<level>', methods=['GET', 'POST'])
def edit_course(level):
    if session.get('role') != 'admin':
        return "دسترسی غیرمجاز", 403

    courses = load_courses()
    users = load_users()

    if level not in courses:
        return "دوره‌ای با این سطح وجود ندارد.", 404

    course = courses[level]

    #  فیلتر استادهایی که این درس خاص را در لیست‌شان دارند
    teachers = [
        username for username, data in users.items()
        if data.get('role') == 'teacher' and level in data.get('courses', [])
    ]

    if request.method == 'POST':
        course['title'] = request.form['title']
        course['start_date'] = request.form['start_date']
        course['duration_weeks'] = int(request.form['duration'])
        course['schedule'] = request.form['schedule']
        course['prerequisites'] = request.form['prerequisites']
        course['capacity'] = int(request.form['capacity'])
        course['teacher'] = request.form.get('teacher')

        save_courses(courses)
        return redirect(url_for('profile'))

    return render_template('admin/edit_course.html', level=level, course=course, teachers=teachers)

#افزودن استاد جدید
@app.route('/admin/add_teacher', methods=['GET', 'POST'])
def add_teacher():
    if session.get('role') != 'admin':
        return "دسترسی غیرمجاز", 403

    courses = load_course_details()
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        selected_courses = request.form.getlist('courses')  

        users = load_users()

        if username in users:
            error = "استادی با این نام کاربری وجود دارد."
        else:
            users[username] = {
                'password': password,
                'role': 'teacher',
                'full_name': full_name,
                'courses': selected_courses
            }

            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)

            return redirect(url_for('profile'))

    return render_template('admin/add_teacher.html', courses=courses, error=error)

#حذف درس
@app.route('/admin/delete_course', methods=['POST'])
def delete_course():
    if session.get('role') != 'admin':
        return "دسترسی غیرمجاز", 403

    level = request.form.get('level')

    if not level:
        return "هیچ دوره‌ای انتخاب نشده.", 400

    # حذف از فایل courses.json
    courses = load_course_details()
    if level in courses:
        del courses[level]
        with open('data/courses.json', 'w', encoding='utf-8') as f:
            json.dump(courses, f, ensure_ascii=False, indent=2)

    students = load_students()
    for student_username, student_data in students.items():
        if 'courses' in student_data and level in student_data['courses']:
            del student_data['courses'][level]

    # ذخیره‌ی نسخه‌ی جدید students.json
    with open('data/students.json', 'w', encoding='utf-8') as f:
        json.dump(students, f, ensure_ascii=False, indent=2)

    return redirect(url_for('profile'))


# پروفایل کاربر
@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    users = load_users()
    username = session['username']
    user = users.get(username, {})

    role = session.get('role')
    learning = user.get('learning', [])
    levels, elevels = categorize_courses(load_courses())

    student = {}
    full_courses = {}
    teacher_courses = []  

    full_name = user.get('full_name', username)  


    if role == 'student':
        students = load_students()
        student = students.get(username, {}) or {}
        
        if 'courses' not in student:
            student['courses'] = {}

        # بارگذاری اطلاعات کامل دوره‌ها برای دانش‌آموز
        all_courses = load_courses()
        for level, info in student['courses'].items():
            course_info = all_courses.get(level)
            teacher_username = info.get('teacher')
            teacher_full_name = users.get(teacher_username, {}).get('full_name', teacher_username)

            if course_info:
                full_courses[level] = {
                    'teacher': teacher_full_name,
                    'passed': info['passed'],
                    'schedule': course_info.get('schedule')
                }
            else:
                full_courses[level] = {
                    'teacher': teacher_full_name,
                    'passed': info.get('passed'),
                    'schedule': 'نامشخص'
                }

    elif session.get('role') == 'teacher':
        teacher_courses = []
        all_courses = load_courses()
        students = load_students()  

        for code, course in all_courses.items():
            if course.get('teacher') == username:
                # بررسی ثبت‌نام دانشجویان برای این درس
                has_students = False
                for student in students.values():
                    student_courses = student.get('courses', {})
                    if code in student_courses and student_courses[code].get('teacher') == username:
                        has_students = True
                        break

                if has_students:
                    start_date = course.get('start_date')
                    start_date_jalali = miladi_to_jalali(start_date) if start_date else '---'

                    teacher_courses.append({
                        'code': code,
                        'title': course.get('title'),
                        'schedule': course.get('schedule'),
                        'start_date': start_date,
                        'start_date_jalali': start_date_jalali,
                        'duration_weeks': course.get('duration_weeks')
                    })


    return render_template(
        'profile.html',
        username=username,
        full_name=full_name,  
        role=role,
        learning=learning,
        levels=levels,
        elevels=elevels,
        student=student,
        full_courses=full_courses,
        teacher_courses=teacher_courses  
    )

# صفحه دوره‌ها
@app.route('/courses')
def courses():
    course_data = load_course_details()
    levels, elevels = categorize_courses(course_data)
    return render_template('courses.html', levels=levels, elevels=elevels)

#اطلاعات یک دوره‌ی خاص
@app.route('/courses/<level>')
def course_detail(level):
    course_details = load_course_details()
    course = course_details.get(level)

    users = load_users()
    teacher_username = course.get('teacher')
    teacher_full_name = users.get(teacher_username, {}).get('full_name', teacher_username)


    if not course:
        return "دوره‌ای با این سطح وجود ندارد.", 404

    users = load_users()
    teachers = [u for u, info in users.items()
                if info.get('role') == 'teacher' and level in info.get('courses', [])]

    course['start_date_jalali'] = miladi_to_jalali(course['start_date'])

    prereq_passed = True
    enrolled = False
    student_course = {}
    course_status = None  

    if session.get('role') == 'student':
        username = session.get('username')
        students = load_students()
        student = students.get(username, {})
        student_courses = student.get('courses', {})

        # بررسی پیش‌نیاز
        prereq_list = course.get('prerequisites', [])
        prereq_passed = all(
            student_courses.get(p, {}).get('passed') == True for p in prereq_list
        )

        # بررسی ثبت‌نام در دوره جاری
        if level in student_courses:
            enrolled = True
            student_course = student_courses[level]
            course_status = student_course.get('passed')

    return render_template("course_detail.html",
                           level=level,
                           course=course,
                           teachers=teachers,
                           enrolled=enrolled,
                           teacher_full_name=teacher_full_name,
                           student_course=student_course,
                           prereq_passed=prereq_passed,
                           course_status=course_status)  

@app.route('/teacher/course/<course>')
def view_course_students(course):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    students = load_students()
    users = load_users()
    course_students = []

    for student_username, data in students.items():
        student_courses = data.get('courses', {})
        if course in student_courses:
            course_info = student_courses[course]
            if course_info.get('teacher') == session['username']:
                full_name = users.get(student_username, {}).get('full_name', student_username)
                course_students.append({
                    'username': student_username,  
                    'full_name': full_name,
                    'passed': course_info.get('passed')
                })


    return render_template('course_students.html', course=course, students=course_students)

@app.route('/teacher/course/<course>/student/<student>', methods=['POST'])
def update_student_status(course, student):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    status = request.form.get('status')
    passed = True if status == 'true' else False

    students = load_students()
    if student in students:
        if course in students[student].get('courses', {}):
            # فقط اگر استاد فعلی مسئول این درس باشد
            if students[student]['courses'][course]['teacher'] == session['username']:
                students[student]['courses'][course]['passed'] = passed
                save_students(students)

    return redirect(url_for('view_course_students', course=course))


# شروع یادگیری دوره
@app.route('/start_course/<level>', methods=['POST'])
def start_course(level):
    if 'username' not in session or session.get('role') != 'student':
        return redirect(url_for('login', next=url_for('start_course', level=level)))

    # ذخیره‌ی اطلاعات موقت در session تا بعد از پرداخت نهایی شوند
    session['pending_course'] = {
        'level': level
    }

    return redirect(url_for('payment'))
#پرداخت
@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if session.get('role') != 'student' or 'pending_course' not in session:
        return redirect(url_for('profile'))

    course_info = session['pending_course']
    level = course_info['level']

    # گرفتن استاد از فایل courses
    courses = load_courses()
    teacher = courses.get(level, {}).get('teacher', 'نامشخص')

    if request.method == 'POST':
        # فرضاً اطلاعات کارت و ایمیل گرفته شده‌اند
        card_number = request.form.get('card_number')
        if len(card_number) != 16 or not card_number.isdigit():
            return "شماره کارت نامعتبر است"
        cvv2 = request.form.get('cvv2')
        email = request.form.get('email')

        session.pop('pending_course', None)

        students = load_students()
        student = students.get(session['username'], {})
        if 'courses' not in student:
            student['courses'] = {}
        student['courses'][level] = {'teacher': teacher, 'passed': 'in_progress'}

        students[session['username']] = student
        save_students(students)

        return redirect(url_for('payment_success'))

    return render_template('payment.html')

@app.route('/payment_success')
def payment_success():
    return render_template('payment_success.html')

#مشاهده ی محتوای دوره
@app.route('/course_content/<level>')
def course_content(level):
    if session.get('role') != 'student':
        return "دسترسی غیرمجاز", 403

    username = session.get('username')
    students = load_students()
    student = students.get(username, {})
    student_courses = student.get('courses', {})

    # بررسی اینکه دانش‌آموز واقعاً در حال گذراندن این درس هست یا نه
    course = student_courses.get(level)
    if not course or course.get('passed') != 'in_progress':
        return "شما در این دوره ثبت‌نام نکرده‌اید یا دوره فعال نیست.", 403

    
    content_data = load_course_content(level)  

    return render_template("student/course_content.html", level=level, content=content_data)

#ویرایش محتوا

@app.route('/teacher/course/<course_code>/content', methods=['GET', 'POST'])
def edit_course_content(course_code):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    username = session['username']
    courses = load_courses()
    course = courses.get(course_code)

    if not course or course.get('teacher') != username:
        return "شما اجازه دسترسی به این درس را ندارید", 403

    course_contents = load_course_content(course_code)

    with open('data/course_content.json', 'r', encoding='utf-8') as f:
        all_content_data = json.load(f)

    if request.method == 'POST':
        action = request.form.get('action')
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        file = request.files.get('file')

        file_url = ''
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            file_url = '/' + file_path  # مسیر قابل دسترسی از سمت کلاینت

        if action == 'add' and title and body:
            course_contents.append({
                'title': title,
                'body': body,
                'file_url': file_url  # آدرس فایل (در صورت وجود)
            })
            all_content_data[course_code] = course_contents
            save_course_content(all_content_data)

        elif action == 'delete' and title:
            course_contents = [c for c in course_contents if c['title'] != title]
            all_content_data[course_code] = course_contents
            save_course_content(all_content_data)

        return redirect(url_for('edit_course_content', course_code=course_code))

    return render_template('edit_course_content.html', course=course, code=course_code, contents=course_contents)

#لیست دانشجویان
@app.route('/admin/student_report')
def student_report():
    if session.get('role') != 'admin':
        return "دسترسی غیرمجاز", 403

    selected_teacher = request.args.get('teacher')
    username = session['username']
    users = load_users()
    students = load_students()
    
    #  مقداردهی امن از ابتدا
    full_name = users.get(username, {}).get('full_name', username)

    # ساخت دیکشنری استادها: username -> full_name
    teacher_names = {
        uname: info.get('full_name', uname)
        for uname, info in users.items()
        if info.get('role') == 'teacher'
    }

    report = {}
    for username, data in students.items():
        for level, info in data.get('courses', {}).items():
            teacher = info.get('teacher', 'نامشخص')

            if selected_teacher and teacher != selected_teacher:
                continue

            if level not in report:
                report[level] = []

            s_full_name = users.get(username, {}).get('full_name', username)
            t_full_name = users.get(teacher, {}).get('full_name', teacher)

            report[level].append({
                'username': username,
                'full_name': s_full_name,
                't_full_name': t_full_name,
                'passed': info.get('passed', 'نامشخص')
            })

    return render_template(
        'admin/student_report.html',
        report=report,
        teachers=teacher_names,
        full_name=full_name,
        selected_teacher=selected_teacher
    )


# خروج از حساب
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# اجرای برنامه
if __name__ == '__main__':
    app.run(debug=True)
