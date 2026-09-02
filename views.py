import datetime
import os
import random
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from CareerMatch_app.models import *
import code
import datetime
from datetime import timedelta
import random
import smtplib
import logging
import threading


logger = logging.getLogger(__name__)

# Global thread-safe counter for concurrent face encoding requests
_face_encoding_lock = threading.Lock()
_face_encoding_count = 0
_max_concurrent_encodings = 2  # Allow max 2 concurrent face encoding operations


try:
    import numpy as np
except Exception:
    np = None


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that converts numpy types to native Python types."""
    def default(self, obj):
        if np is not None:
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


projectemail = "carzfiree@gmail.com"
projectpassword = "pqlr sgkw niwy jyal"




def send_notification_email(sender_email, app_password, receiver_email, subject, html_content):
    """
    Send HTML email notification with SMTP settings
    """
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart("alternative")
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_content, "html"))
        
        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email sent successfully to {receiver_email}")
        return True
    except Exception as e:
        print(f"⚠️ Error sending email: {str(e)}")
        return False

# Create your views here.
def login_get(request):
    return render(request,"index.html")

def login_post(request):
    un=request.POST['name']
    ps=request.POST['pass']
    res=login.objects.filter(username=un,password=ps)
    print(res,"RES",un,ps   )    
    if res.exists():
        request.session['lid'] = res[0].id
        request.session['usertype'] = res[0].usertype
        if res[0].usertype=='admin':
            return HttpResponse('<script>alert("login successfull");window.location="/admin_home"</script>')
        elif res[0].usertype == "company":
            return HttpResponse("<script>alert('Login successful');window.location='/home'</script>")
        elif res[0].usertype == "candidate":
            return HttpResponse("<script>alert('Login successful');window.location='/student_home'</script>")

        else:
            return HttpResponse('<script>alert("unauthorised candidate");window.location="/"</script>')
    else:
        return HttpResponse('<script>alert("invalid credentials");window.location="/"</script>')


def logout(request):
    request.session['lid'] = 0

    return HttpResponse('<script>alert("LogOut");window.location="/"</script>')


def home(request):
    request.session['head'] = "home"
    return render(request,"company/index.html")


def student_home(request):
    request.session['head'] = "student home"
    return render(request,"candidate/index.html")

def admin_add_job_category(request):
    if request.session['lid'] == "":
        return HttpResponse("<script>alert('session expired');window.location='/'</script>")

    return render(request,"admin/Add Job Categories.html")

def admin_add_job_category_post(request):
    cn=request.POST['textfield']
    data = job_category.objects.filter(category_name=cn)
    if data.exists():
        return HttpResponse("<script>alert('Already Exists');window.location='/admin_add_job_category#services'</script>")
    else:
        obj=job_category()
        obj.category_name=cn
        obj.save()
        return HttpResponse('<script>alert("Added");window.location="/view_job_categories#services"</script>')


def admin_home(request):
    return render(request,"admin/index.html")

def approved_companies(request):
    if request.session['lid'] == "":
        return HttpResponse("<script>alert('session expired');window.location='/'</script>")
    res=company.objects.filter(LOGIN__usertype='company')
    return render(request,"admin/Approved Companies.html",{'data':res})

def rejected_companies(request):
    if request.session['lid'] == "":
        return HttpResponse("<script>alert('session expired');window.location='/'</script>")

    res=company.objects.filter(LOGIN__usertype='rejected')
    return render(request,"admin/Rejected Companies.html",{'data':res})

def view_companies(request):
    if request.session['lid'] == "":
        return HttpResponse("<script>alert('session expired');window.location='/'</script>")

    res=company.objects.filter(LOGIN__usertype='pending')
    return render(request,"admin/View Companies.html",{'data':res})

def view_job_categories(request):
    if request.session['lid'] == "":
        return HttpResponse("<script>alert('session expired');window.location='/'</script>")

    res=job_category.objects.all()
    return render(request,"admin/View Job Categories.html",{'data':res})

def addqualification(request):
    if request.session['lid'] == "":
        return HttpResponse("<script>alert('session expired');window.location='/'</script>")

    return render(request, "admin/addQualifications.html")

def addqualification_post(request):
    qualifications1 = request.POST['q']
    type = request.POST['t']

    obj=qualifications()

    obj.qualification = qualifications1
    obj.type = type
    obj.save()
    return HttpResponse('<script>alert("Add Successfully");window.location="/view_qualificationsssss#services"</script>')



def view_qualificationsssss(request):
    if request.session['lid'] == "":
        return HttpResponse("<script>alert('session expired');window.location='/'</script>")

    res=qualifications.objects.all()
    types_count = res.values('type').distinct().count()
    scount = res.filter(type='Skill').count()
    qcount = res.filter(type='Qualification').count()
    return render(request,"admin/viewqualifications.html",{'data':res, 'types_count': types_count, 'scount': scount, 'qcount': qcount})



def deleteq(request,id):
    qualifications.objects.get(id=id).delete()
    return HttpResponse('<script>alert("Deleted Successfully");window.location="/view_qualificationsssss#services"</script>')




def _build_suggestions_context(filter_type='all'):
    total_count = suggestions.objects.count()
    user_count = suggestions.objects.filter(type='candidate').count()
    company_count = suggestions.objects.filter(type='company').count()

    if filter_type == 'candidate':
        suggestions_qs = suggestions.objects.filter(type='candidate')
    elif filter_type == 'company':
        suggestions_qs = suggestions.objects.filter(type='company')
    else:
        suggestions_qs = suggestions.objects.all()

    ar = []
    for suggestion_item in suggestions_qs:
        if suggestion_item.type == 'candidate':
            type_label = 'User'
            icon = 'user'
            profile_name = suggestion_item.LOGIN.username
            try:
                profile_name = user.objects.get(LOGIN=suggestion_item.LOGIN).name
            except user.DoesNotExist:
                pass
        else:
            type_label = 'Company'
            icon = 'building'
            profile_name = suggestion_item.LOGIN.username
            try:
                profile_name = company.objects.get(LOGIN=suggestion_item.LOGIN).company_name
            except company.DoesNotExist:
                pass

        ar.append({
            'id': suggestion_item.id,
            'suggestion': suggestion_item.suggestion,
            'date': suggestion_item.date,
            'name': profile_name,
            'type': type_label,
            'type_icon': icon,
        })

    return {
        'data': ar,
        'filter_type': filter_type,
        'total_count': total_count,
        'user_count': user_count,
        'company_count': company_count,
    }


def view_suggestions_get(request):
    if request.session.get('lid', '') == "":
        return HttpResponse("<script>alert('session expired');window.location='/'</script>")

    filter_type = request.GET.get('select', 'all')
    context = _build_suggestions_context(filter_type)
    return render(request, "admin/View Suggestions.html", context)


def view_suggestions_post(request):
    if request.session.get('lid', '') == "":
        return HttpResponse("<script>alert('session expired');window.location='/'</script>")

    filter_type = request.POST.get('select', 'all')
    context = _build_suggestions_context(filter_type)
    return render(request, "admin/View Suggestions.html", context)

def view_users(request):
    if request.session['lid'] == "":
        return HttpResponse("<script>alert('session expired');window.location='/'</script>")

    res=user.objects.all()
    return render(request,"admin/View Users.html",{'data':res})

def approve_company(request,id):
    login.objects.filter(id=id).update(usertype='company')
    # *✨ Python Email Codeimport smtplib*

    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # ✅ Gmail credentials (use App Password, not real password)
    sender_email = "carzfiree@gmail.com"
    receiver_email = login.objects.get(id=id).username  # change to actual recipient
    app_password = "vtde phpd htcz hcnh"  # App Password from Google
    pwd = "Your account has been successfully verified."  # Example password to send

    # Setup SMTP
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, app_password)

    # Create the email
    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = "*✨  CareerMatch Verification *✨ "

    # Plain text (backup)
    # text = f"""
    # Hello,

    # Your password for Smart Donation Website is: {pwd}

    # Please keep it safe and do not share it with anyone.
    # """

    # HTML (attractive)
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color:#2c7be5;">🔑 Career Match Website</h2>
        <p>Hello,</p>
        <p style="padding:10px; background:#f4f4f4; 
                  border:1px solid #ddd; 
                  display:inline-block;
                  font-size:18px;
                  font-weight:bold;
                  color:#2c7be5;">
          {pwd}
        </p>
        <p>Please keep it safe and do not share it with anyone.</p>
        <hr>
        <small style="color:gray;">This is an automated email from CareerMatch System.</small>
      </body>
    </html>
    """

    # Attach both versions
    # msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    # Send email
    server.send_message(msg)
    print("✅ Email sent successfully!")

    # Close connection
    server.quit()
    return HttpResponse('<script>alert("Approved");window.location="/approved_companies#services"</script>')

def reject_company(request,id):
    login.objects.filter(id=id).update(usertype='rejected')
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # ✅ Gmail credentials (use App Password, not real password)
    sender_email = "carzfiree@gmail.com"
    receiver_email = login.objects.get(id=id).username  # change to actual recipient
    app_password = "vtde phpd htcz hcnh"  # App Password from Google
    pwd = "⚠️ Your account request has been rejected. Please review your details and try again."  # Example password to send

    # Setup SMTP
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, app_password)

    # Create the email
    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = "*✨  CareerMatch Verification *✨"

    # Plain text (backup)
    # text = f"""
    # Hello,

    # Your password for Smart Donation Website is: {pwd}

    # Please keep it safe and do not share it with anyone.
    # """

    # HTML (attractive)
    html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color:#2c7be5;">🔑 Career Match Website</h2>
            <p>Hello,</p>
            <p style="padding:10px; background:#f4f4f4; 
                      border:1px solid #ddd; 
                      display:inline-block;
                      font-size:18px;
                      font-weight:bold;
                      color:#2c7be5;">
              {pwd}
            </p>
            <p>Please keep it safe and do not share it with anyone.</p>
            <hr>
            <small style="color:gray;">This is an automated email from CareerMatch System.</small>
          </body>
        </html>
        """

    # Attach both versions
    # msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    # Send email
    server.send_message(msg)
    print("✅ Email sent successfully!")

    # Close connection
    server.quit()

    return HttpResponse('<script>alert("Rejected");window.location="/rejected_companies#services"</script>')

def delete_company(request,id):
    company.objects.filter(id=id).delete()
    return HttpResponse('<script>alert("Deleted");window.location="/approved_companies#services"</script>')

def register_company_get(request):
   return render(request,"company/reg.html")

def register_company_post(request):
    import datetime
    na=request.POST['name']
    lat=request.POST['lati']
    lon=request.POST['longi']
    email=request.POST['email']
    ph=request.POST['phone']
    desc=request.POST['des']
    place=request.POST['place']
    pin=request.POST['pin']
    post=request.POST['post']
    img=request.FILES['img']

    d=datetime.datetime.now().strftime("%y%m%d-%H%M%S")
    fs=FileSystemStorage()
    img = fs.save(img.name,img)
    path= fs.url(img)

    password=request.POST['pass']
    con=request.POST['cpass']
    data = login.objects.filter(username=email)
    if data.exists():
        return HttpResponse("<script>alert('Already Exists');window.location='/register_company_get'</script>")
    else:
        if password==con:
            obj=login()
            obj.username=email
            obj.password=con
            obj.usertype='pending'
            obj.save()
            obj1=company()
            obj1.company_name=na
            obj1.latitude=lat
            obj1.longitude=lon
            obj1.email=email
            obj1.phone=ph
            obj1.description=desc
            obj1.place=place
            obj1.pin=pin
            obj1.post=post
            obj1.image=path
            obj1.LOGIN=obj
            obj1.save()

            return HttpResponse('<script>alert("Registered Successfully");window.location="/"</script>')
        else:
            return HttpResponse('<script>alert("Password mismatch");window.location="/register_company_get"</script>')


def register_user_get(request):
    return render(request, "candidate/reg.html")

def register_user_post(request):
    na = request.POST['name']
    email = request.POST['email']
    ph = request.POST['phone']
    desc = request.POST['des']
    place = request.POST['place']
    pin = request.POST['pin']
    post = request.POST['post']
    img = request.FILES['img']

    fs = FileSystemStorage()
    img = fs.save(img.name,img)
    path = fs.url(img)

    password = request.POST['pass']
    con = request.POST['cpass']
    data = login.objects.filter(username=email)
    if data.exists():
        return HttpResponse("<script>alert('Already Exists');window.history.back();window.location='/register_user_get'</script>")
    else:
        if password == con:
            obj = login()
            obj.username = email
            obj.password = con
            obj.usertype = 'candidate'
            obj.save()
            obj1 = user()
            obj1.name = na
            obj1.email = email
            obj1.phone = ph
            obj1.experience = desc
            obj1.place = place
            obj1.pin = pin
            obj1.post = post
            obj1.image = path
            obj1.LOGIN = obj
            obj1.save()

            return HttpResponse('<script>alert("Registered Successfully");window.location="/"</script>')
        else:
            return HttpResponse(
                '<script>alert("Password mismatch");window.location="/register_user_get"</script>')


def view_profile(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    lid = request.session.get('lid')
    try:
        login_obj = login.objects.get(id=lid)
    except Exception:
        return HttpResponse("<script>alert('User not found');window.location='/'</script>")

    # Only candidates have user profiles
    if login_obj.usertype != 'candidate':
        return HttpResponse("<script>alert('Unauthorized');window.location='/'</script>")

    try:
        user_obj = user.objects.get(LOGIN=login_obj)
    except user.DoesNotExist:
        return HttpResponse("<script>alert('Profile not found');window.location='/'</script>")

    return render(request, 'candidate/view_profile.html', {'user_obj': user_obj})


def edit_profile(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    lid = request.session.get('lid')
    try:
        login_obj = login.objects.get(id=lid)
    except Exception:
        return HttpResponse("<script>alert('User not found');window.location='/'</script>")

    if login_obj.usertype != 'candidate':
        return HttpResponse("<script>alert('Unauthorized');window.location='/'</script>")

    try:
        user_obj = user.objects.get(LOGIN=login_obj)
    except user.DoesNotExist:
        return HttpResponse("<script>alert('Profile not found');window.location='/'</script>")

    if request.method == 'GET':
        return render(request, 'candidate/edit_profile.html', {'user_obj': user_obj})

    # POST: update profile
    name = request.POST.get('name', user_obj.name)
    phone = request.POST.get('phone', user_obj.phone)
    place = request.POST.get('place', user_obj.place)
    pin = request.POST.get('pin', user_obj.pin)
    post = request.POST.get('post', user_obj.post)
    experience = request.POST.get('experience', user_obj.experience)

    # handle image upload (optional)
    if request.FILES.get('image'):
        fs = FileSystemStorage()
        img = request.FILES['image']
        img_name = fs.save(img.name, img)
        path = fs.url(img_name)
        user_obj.image = path

    user_obj.name = name
    user_obj.phone = phone
    user_obj.place = place
    user_obj.pin = pin
    user_obj.post = post
    try:
        user_obj.experience = int(experience)
    except Exception:
        pass
    user_obj.save()

    return HttpResponse("<script>alert('Profile updated successfully');window.location='/view_profile'</script>")


import PyPDF2
import re


def normalize_text(text):
    """Normalize text for flexible matching:
    - Convert to lowercase
    - Remove extra spaces, punctuation, and numbers
    - Keep only alphanumeric characters and spaces
    """
    text = text.lower().strip()
    # Remove punctuation, special chars, and numbers; keep only letters and spaces
    text = re.sub(r'[^a-z\s]', '', text)
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def check_requirement_match(resume_text, requirements_list):
    """Check if resume contains required skills/qualifications with flexible matching.
    Handles variations like: 'Master of Computer Application' vs 'masterofcomputerapplication(2016–2019)'
    Returns: (match_count, total_requirements, matched_items, unmatched_items)
    """
    matched = []
    unmatched = []

    for req in requirements_list:
        req_normalized = normalize_text(req)

        # Skip empty requirements
        if not req_normalized:
            continue

        # Check if normalized requirement text exists in resume
        # Split requirement into words and check if all words appear in sequence or nearby
        req_words = req_normalized.split()

        # Try to find all requirement words in the resume
        found_all_words = all(word in resume_text for word in req_words)

        if found_all_words:
            matched.append(req)
        else:
            unmatched.append(req)

    return len(matched), len(requirements_list), matched, unmatched

# ===================================================================================

##################################################################################################



def emailsetting(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "Email Setting"
    lid = request.session.get('lid')
    if not lid:
        return redirect('/')

    user = login.objects.get(id=lid)
    if user.usertype != 'company':
        return redirect('/')
    return render(request, "company/email.html",{"company_obj":company.objects.get(LOGIN=user)})


def save_email_settings(request):
    """Save mail settings"""
    if request.method != 'POST':
        return redirect('/mail_settings')

    try:
        lid = request.session.get('lid')
        if not lid:
            return redirect('/')

        user = login.objects.get(id=lid)
        if user.usertype != 'company':
            return redirect('/')

        company_obj = company.objects.get(LOGIN=user)
        smtp_email = request.POST.get('email', '').strip()
        smtp_password = request.POST.get('password', '').strip()
        company_obj.mailprovider = smtp_email
        company_obj.apppassword = smtp_password
        company_obj.save()

        messages.success(request, 'Mail settings saved successfully!')
        return redirect('/emailsetting')

    except ValueError:
        messages.error(request, 'Invalid port number.')
        return redirect('/emailsetting')
    except Exception as e:
        messages.error(request, f'Error saving mail settings: {str(e)}')
        return redirect('/emailsetting')


def add_vacancy(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "Add vacancy"
    return render(request, "company/add_vacancy.html")


def add_vacancy_post(request):
    job = request.POST['textfield']
    fl = request.POST['textfield2']
    Salary = request.POST['textfield4']
    job_description = request.POST['job_description']
    experience = request.POST['textfield6']
    cuttoff = request.POST['textfield7']
    apply_from_date = request.POST.get('apply_from_date')
    apply_to_date = request.POST.get('apply_to_date')

    obj = vacancy()
    obj.job_type = job
    obj.fulltime_parttime = fl
    obj.salary = Salary
    obj.description = job_description
    obj.experience = experience
    obj.cuttoff = cuttoff
    obj.apply_from_date = apply_from_date
    obj.apply_to_date = apply_to_date
    obj.COMPANY = company.objects.get(LOGIN=request.session['lid'])
    obj.save()
    request.session['vid'] = obj.id
    return HttpResponse("<script>alert('Added successfully');window.location='/add_vacancy#abc'</script>")


def view_vacancy(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "view vacancy"
    res = vacancy.objects.filter(COMPANY__LOGIN=request.session['lid'])
    return render(request, "company/view_vaccancy.html", {"data": res})


def edit_vacancy(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "Edit vacancy"
    data = vacancy.objects.get(id=id)
    return render(request, "company/edit_vacancy.html", {"data": data})


def edit_vacancy_post(request, id):
    job_type = request.POST['textfield']
    fl = request.POST['textfield2']
    description = request.POST['textfield6']
    Salary = request.POST['textfield4']
    experience = request.POST['textfield5']
    cuttoff = request.POST['textfield7']
    apply_from_date = request.POST.get('apply_from_date')
    apply_to_date = request.POST.get('apply_to_date')

    vacancy.objects.filter(id=id).update(job_type=job_type, salary=Salary,
                                         fulltime_parttime=fl, experience=experience, cuttoff=cuttoff,
                                         description=description, apply_from_date=apply_from_date, apply_to_date=apply_to_date)

    return HttpResponse("<script>alert('Edited successfully');window.location='/view_vacancy#abc'</script>")


def delete_vacancy(request, id):
    vacancy.objects.filter(id=id).delete()
    return HttpResponse("<script>alert('deleted successfully');window.location='/view_vacancy#abc'</script>")


# =============== QUESTION MANAGEMENT ==============

def add_question(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "ADD QUESTION"
    return render(request, "company/add-questions.html", {"id": id})


def add_question_post(request, id):
    questions = request.POST['qstn']
    Option_A = request.POST['textfield2']
    Option_B = request.POST['textfield3']
    Option_C = request.POST['textfield4']
    Option_D = request.POST['textfield5']
    answer = request.POST['RadioGroup1']
    if answer == 'A':
        obj = question()
        obj.question = questions
        obj.option1 = Option_A
        obj.option2 = Option_B
        obj.option3 = Option_C
        obj.option4 = Option_D

        obj.answers = Option_A
        obj.VACANCY_id = id
        obj.save()
    if answer == 'B':
        obj = question()
        obj.question = questions
        obj.option1 = Option_A
        obj.option2 = Option_B
        obj.option3 = Option_C
        obj.option4 = Option_D

        obj.answers = Option_B
        obj.VACANCY_id = id
        obj.save()
    if answer == 'C':
        obj = question()
        obj.question = questions
        obj.option1 = Option_A
        obj.option2 = Option_B
        obj.option3 = Option_C
        obj.option4 = Option_D

        obj.answers = Option_C
        obj.VACANCY_id = id
        obj.save()
    if answer == 'D':
        obj = question()
        obj.question = questions
        obj.option1 = Option_A
        obj.option2 = Option_B
        obj.option3 = Option_C
        obj.option4 = Option_D

        obj.answers = Option_D
        obj.VACANCY_id = id
        obj.save()

    return  redirect('/view_questions/'+str(id)+"#abc")


def extract_text_from_pdf2(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""

def add_question_pdf(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")

    pdf_file = request.FILES['pdf_file']

    try:
        # Extract text from PDF
        pdf_text = extract_text_from_pdf2(pdf_file)
        print(pdf_text,"PT")

        # Parse questions from the text
        questions_data = parse_questions_from_text(pdf_text)
        print(questions_data,"DATA")

        # Save questions to database
        saved_count = 0
        for q_data in questions_data:
            print(q_data['answer'][:100])
            try:
                obj = question()
                obj.question = q_data['question'][:500]  # Limit to model field size
                obj.option1 = q_data['options'][0][:100] if len(q_data['options']) > 0 else ''
                obj.option2 = q_data['options'][1][:100] if len(q_data['options']) > 1 else ''
                obj.option3 = q_data['options'][2][:100] if len(q_data['options']) > 2 else ''
                obj.option4 = q_data['options'][3][:100] if len(q_data['options']) > 3 else ''
                if q_data['answer'][:100] == "A":
                    obj.answers = q_data['options'][0][:100] if len(q_data['options']) > 0 else ''
                elif q_data['answer'][:100] == "B":
                    obj.answers = q_data['options'][1][:100] if len(q_data['options']) > 1 else ''
                elif q_data['answer'][:100] == "C":
                    obj.answers = q_data['options'][2][:100] if len(q_data['options']) > 2 else ''
                elif q_data['answer'][:100] == "D":
                    obj.answers = q_data['options'][3][:100] if len(q_data['options']) > 3 else ''
                obj.VACANCY_id = id
                obj.save()
                saved_count += 1
            except Exception as e:
                print(f"Error saving question: {e}")
                continue

        if saved_count > 0:
            return HttpResponse(f'<script>alert("{saved_count} questions extracted and saved successfully!");window.location="/view_questions/{id}#abc"</script>')
        else:
            return HttpResponse('<script>alert("No valid questions found in the PDF. Please check the format.");window.location="/add_question/'+str(id)+'#abc"</script>')

    except Exception as e:
        print(f"Error processing PDF: {e}")
        return HttpResponse('<script>alert("Error processing PDF file. Please try again.");window.location="/add_question/'+str(id)+'#abc"</script>')

#
# import re
#
# def parse_questions_from_text(text):
#     questions = []
#
#     # Normalize line breaks
#     text = re.sub(r'\r', '', text)
#
#     # Split into question blocks
#     blocks = re.split(r'Question\s*\d+', text, flags=re.IGNORECASE)
#
#     for block in blocks:
#         block = block.strip()
#         if not block:
#             continue
#
#         lines = [line.strip() for line in block.split('\n') if line.strip()]
#
#         question_text = ""
#         options = []
#         answer = ""
#
#         i = 0
#
#         # First line = question
#         if i < len(lines):
#             question_text = lines[i]
#             i += 1
#
#         # Next lines = options
#         while i < len(lines):
#             line = lines[i]
#
#             if re.match(r'^[A-Da-d][\)\.]', line):
#                 options.append(line[2:].strip())
#             elif line.lower().startswith('answer'):
#                 match = re.search(r'([A-Da-d])', line)
#                 if match:
#                     ans_letter = match.group(1).upper()
#                     idx = ord(ans_letter) - ord('A')
#                     if idx < len(options):
#                         answer = options[idx]
#             i += 1
#
#         if question_text and len(options) >= 2:
#             questions.append({
#                 'question': question_text,
#                 'options': options,
#                 'answer': answer
#             })
#
#     return questions
# # def parse_questions_from_text(text):
# #     import re
# #
# #     questions = []
# #
# #     # Normalize text
# #     text = text.lower()
# #     text = re.sub(r'\s+', ' ', text)
# #
# #     # Split using "question"
# #     parts = re.split(r'\bquestion\b', text)
# #
# #     for part in parts:
# #         part = part.strip()
# #         if not part:
# #             continue
# #
# #         try:
# #             # Extract question text (before ' a ')
# #             q_split = re.split(r'\sa\s', part, maxsplit=1)
# #             if len(q_split) < 2:
# #                 continue
# #
# #             question_text = q_split[0].strip()
# #
# #             rest = q_split[1]
# #
# #             # Extract options
# #             options = []
# #
# #             pattern = r'(.*?)\sb\s(.*?)\sc\s(.*?)\sd\s(.*?)\sanswer\s([a-d])'
# #             match = re.search(pattern, rest)
# #
# #             if match:
# #                 options.append(match.group(1).strip())
# #                 options.append(match.group(2).strip())
# #                 options.append(match.group(3).strip())
# #                 options.append(match.group(4).strip())
# #
# #                 answer_letter = match.group(5).upper()
# #                 answer_index = ord(answer_letter) - ord('A')
# #
# #                 answer = options[answer_index] if answer_index < len(options) else ""
# #
# #                 questions.append({
# #                     'question': question_text,
# #                     'options': options,
# #                     'answer': answer
# #                 })
# #
# #         except Exception as e:
# #             print("Parsing error:", e)
# #             continue
# #
# #     return questions


import re

def parse_questions_from_text(text):
    questions = []

    # Normalize text
    text = re.sub(r'\r', '', text)

    # Split using "Question 1", "Question 2", etc.
    blocks = re.split(r'Question\s*\d+', text, flags=re.IGNORECASE)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = [line.strip() for line in block.split('\n') if line.strip()]

        question_text = ""
        options = []
        answer = ""

        i = 0

        # First valid line = question
        if i < len(lines):
            question_text = lines[i]
            i += 1

        # Read rest
        while i < len(lines):
            line = lines[i]

            # Match A), A., A:
            opt_match = re.match(r'^([A-Da-d])[\)\.\:]\s*(.*)', line)
            if opt_match:
                options.append(opt_match.group(2).strip())

            # Match Answer: A / Ans: B
            ans_match = re.search(r'(Answer|Ans)[\s\:]*([A-Da-d])', line, re.IGNORECASE)
            if ans_match:
                answer = ans_match.group(2).upper()

            i += 1

        # Save only valid questions
        if question_text and len(options) >= 2:
            questions.append({
                'question': question_text,
                'options': options[:4],  # max 4
                'answer': answer         # STORE LETTER (IMPORTANT)
            })

    return questions

def view_questions(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "view questions"
    data = question.objects.filter(VACANCY_id=id)
    request.session['vid'] = id
    return render(request, "company/view_questions.html", {"data": data})


def edit_questions(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "Edit Question"
    data = question.objects.get(id=id)
    return render(request, "company/edit_question.html", {"data": data})


def edit_questions_post(request, id):
    questions = request.POST['textarea']
    Option_A = request.POST['textfield']
    Option_B = request.POST['textfield2']
    Option_C = request.POST['textfield3']
    Option_D = request.POST['textfield4']
    answer = request.POST['select']
    if answer == 'A':
        obj = question.objects.get(id=id)
        obj.question = questions
        obj.option1 = Option_A
        obj.option2 = Option_B
        obj.option3 = Option_C
        obj.option4 = Option_D

        obj.answers = Option_A
        obj.VACANCY_id = id
        obj.save()
    if answer == 'B':
        obj = question.objects.get(id=id)
        obj.question = questions
        obj.option1 = Option_A
        obj.option2 = Option_B
        obj.option3 = Option_C
        obj.option4 = Option_D

        obj.answers = Option_B
        obj.VACANCY_id = id
        obj.save()
    if answer == 'C':
        obj = question.objects.get(id=id)
        obj.question = questions
        obj.option1 = Option_A
        obj.option2 = Option_B
        obj.option3 = Option_C
        obj.option4 = Option_D

        obj.answers = Option_C
        obj.VACANCY_id = id
        obj.save()
    if answer == 'D':
        obj = question.objects.get(id=id)
        obj.question = questions
        obj.option1 = Option_A
        obj.option2 = Option_B
        obj.option3 = Option_C
        obj.option4 = Option_D

        obj.answers = Option_D
        obj.VACANCY_id = id
        obj.save()
    return HttpResponse("<script>alert('edited successfully');window.location='/home'</script>")


def delete_questions(request, id):
    question.objects.filter(id=id).delete()
    vid = request.session['vid']
    return HttpResponse("<script>alert('Deleted successfully');window.location='/view_questions/" + vid + "#abc'</script>")


def add_qualification(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "ADD QUALIFICATION"
    data1 = qualifications.objects.filter()
    for i in data1:
        print("qualification", i.id)
        data = vaccancy_qualification.objects.filter(VACANCY_id=id, QUALIFICATION_id=i.id)
        if data.exists():
            i.status = "added"
            i.vid = data[0].id
        else:
            i.status = "not added"
        print("status", i.status)
    request.session['vid'] = id
    return render(request, "company/add_qualification.html", {"id": id, "data": data1})


def add_qualification_form(request, qualification_id, vacancy_id):
    obj = vaccancy_qualification()
    obj.QUALIFICATION_id = qualification_id
    obj.VACANCY_id = vacancy_id
    obj.save()
    return HttpResponse(
        "<script>alert('Added successfully');window.location='/add_qualification/" + str(vacancy_id) + "#abc'</script>")


def remove_qualification_(request, id):
    vaccancy_qualification.objects.filter(id=id).delete()
    vid = str(request.session['vid'])
    return HttpResponse(
        "<script>alert('Deleted successfully');window.location='/add_qualification/" + vid + "#abc'</script>")


def deleteuser(request, id):
    user.objects.filter(id=id).delete()
    return HttpResponse(
        "<script>alert('Deleted successfully');window.location='/view_users#services'</script>")


# --- schedule interview



def schedule_interview(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "SCHEDULE INTERVIEW"
    return render(request, "company/schedule_interview.html", {"id": id})


def schedule_interview_post(request, id):
    interview_date = request.POST['textfield']
    interview_time = request.POST['textfield2']
    link = request.POST['textfield3']
    
    # Update candidate with interview details
    candidate.objects.filter(id=id).update(interview_date=interview_date,
                                           interview_time=interview_time,
                                           link=link, status="updated")
    
    # Get candidate details
    candidate_obj = candidate.objects.filter(id=id)[0]
    vacancy_id = candidate_obj.VACANCY_id
    
    # Send email notification to candidate
    try:
        # Get company details

        # Try to get company email settings
        try:
            mail_settings = candidate_obj.VACANCY.COMPANY
            sender_email = mail_settings.mailprovider
            app_password = mail_settings.apppassword
        except:
            # Fallback to default Gmail settings
            sender_email = "carzfiree@gmail.com"
            app_password = "vtde phpd htcz hcnh"

        receiver_email = candidate_obj.USER.email
        
        # Create email content
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color:#10B981;">🤝 Team Interview Scheduled</h2>
            <p>Hello {candidate_obj.USER.name},</p>
            <p>Congratulations! Your team interview has been scheduled for the position of <strong>{candidate_obj.VACANCY.job_type}</strong>.</p>
            
            <div style="padding:15px; background:#f0fdf4; border:1px solid #10B981; border-radius:8px; margin:20px 0;">
              <p><strong>📅 Interview Date:</strong> {interview_date}</p>
              <p><strong>⏰ Interview Time:</strong> {interview_time}</p>
              <p><strong>🏢 Company:</strong> {candidate_obj.VACANCY.COMPANY.company_name}</p>
              <p><strong>📹 Meeting Link:</strong> <a href="{link}" style="color:#10B981; text-decoration:none;">{link}</a></p>
            </div>

            <p>Please make sure to:</p>
            <ul>
              <li>Join the interview a few minutes before the scheduled time</li>
              <li>Ensure you have a stable internet connection</li>
              <li>Use a computer or laptop with a camera and microphone</li>
              <li>Wear professional attire</li>
              <li>Have a quiet and well-lit environment</li>
              <li>Click the link above to join the video call</li>
            </ul>

            <p style="color:#6B7280;">If you have any questions or need to reschedule, please contact {company_obj.company_name}.</p>
            <hr>
            <small style="color:#999;">This is an automated email from CareerMatch System.</small>
          </body>
        </html>
        """
        
        subject = f"Team Interview Scheduled - {candidate_obj.VACANCY.job_type}"
        send_notification_email(sender_email, app_password, receiver_email, subject, html)
        
    except Exception as e:
        print(f"⚠️ Error sending email: {str(e)}")
        # Don't fail the interview scheduling if email fails
    
    vacancy_id = str(candidate_obj.VACANCY_id)
    return HttpResponse(
        "<script>alert('Interview Scheduled..');window.location='/view_applied_candidate/" + vacancy_id + "#abc'</script>")


def bschedule_interview(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "SCHEDULE INTERVIEW"
    return render(request, "company/schedule_bot_interview.html", {"id": id})


def bschedule_interview_post(request, id):
    interview_date = request.POST['textfield']
    interview_time = request.POST['textfield2']
    
    # Update candidate with bot interview details
    candidate.objects.filter(id=id).update(binterview_date=interview_date,
                                           binterview_time=interview_time,
                                           status="inteviewwithbotscheduled")
    
    # Get candidate details
    candidate_obj = candidate.objects.filter(id=id)[0]
    vacancy_id = candidate_obj.VACANCY_id
    
    # Send email notification to candidate
    try:
        # Get company details (vacancy model uses `COMPANY` FK)
        company_obj = candidate_obj.VACANCY.COMPANY
        
        # Try to get company email settings
        try:
            mail_settings = candidate_obj.VACANCY.COMPANY
            sender_email = mail_settings.mailprovider
            app_password = mail_settings.apppassword
        except:
            # Fallback to default Gmail settings
            sender_email = "carzfiree@gmail.com"
            app_password = "vtde phpd htcz hcnh"

        receiver_email = candidate_obj.USER.email
        
        # Create email content
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color:#10B981;">🤖 Bot Interview Scheduled</h2>
            <p>Hello {candidate_obj.USER.name},</p>
            <p>Great news! Your bot interview has been scheduled for the position of <strong>{candidate_obj.VACANCY.job_type}</strong>.</p>
            
            <div style="padding:15px; background:#f0fdf4; border:1px solid #10B981; border-radius:8px; margin:20px 0;">
              <p><strong>📅 Interview Date:</strong> {interview_date}</p>
              <p><strong>⏰ Interview Time:</strong> {interview_time}</p>
              <p><strong>🏢 Company:</strong> {company_obj.company_name}</p>
              <p><strong>🤖 Interview Type:</strong> AI-Powered Bot Interview</p>
            </div>

            <p>Please make sure to:</p>
            <ul>
              <li>Join the bot interview a few minutes before the scheduled time</li>
              <li>Ensure you have a stable internet connection</li>
              <li>Use a computer or laptop with a camera and microphone</li>
              <li>Have a quiet and well-lit environment</li>
              <li>Answer questions clearly and naturally</li>
              <li>Ensure proper lighting so the AI can see your expressions</li>
            </ul>

            <p style="color:#6B7280;">If you have any questions or technical issues, please contact {company_obj.company_name}.</p>
            <hr>
            <small style="color:#999;">This is an automated email from CareerMatch System.</small>
          </body>
        </html>
        """
        
        subject = f"Bot Interview Scheduled - {candidate_obj.VACANCY.job_type}"
        send_notification_email(sender_email, app_password, receiver_email, subject, html)
        
    except Exception as e:
        print(f"⚠️ Error sending email: {str(e)}")
        # Don't fail the bot interview scheduling if email fails
    if request.session.get('usertype') == 'company':
        vacancy_id = str(candidate_obj.VACANCY_id)
        return HttpResponse(
            f"<script>alert('Interview Scheduled..');window.location='/view_applied_candidate/{vacancy_id}#abc'</script>")
    else:
        return HttpResponse(
            "<script>alert('Interview completed..');window.location='/view_applied_list#abc'</script>")


def view_scheduled_interview(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "VIEW SCHEDULE INTERVIEW"
    data = candidate.objects.filter(id=id)
    import datetime
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.datetime.now().strftime("%H-%M-%S")
    data1 = candidate.objects.filter(interview_date=current_date, interview_time=current_time)

    return render(request, "company/view_scheduled_interview.html", {"data": data, "data1": data1})


def select_candidate(request, id, status):

    print(status,"STATUS")

    # Update candidate status
    candidate.objects.filter(id=id).update(status=status)
    
    # Get candidate details
    candidate_obj = candidate.objects.filter(id=id)[0]
    vacancy_id = str(candidate_obj.VACANCY_id)
    
    # Send email notification to candidate
    # Get company details
    company_obj = candidate_obj.VACANCY.COMPANY

    # Try to get company email settings
    try:
        mail_settings = candidate_obj.VACANCY.COMPANY
        sender_email = mail_settings.mailprovider
        app_password = mail_settings.apppassword
    except:
        # Fallback to default Gmail settings
        sender_email = "carzfiree@gmail.com"
        app_password = "vtde phpd htcz hcnh"

    receiver_email = candidate_obj.USER.email

    # Create email content based on status
    if status == "selected":
        subject = f"🎉 Selection Notification - {candidate_obj.VACANCY.job_type}"
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color:#10B981;">🎉 Congratulations!</h2>
            <p>Hello {candidate_obj.USER.name},</p>
            <p>We are pleased to inform you that you have been <strong>selected</strong> for the position of <strong>{candidate_obj.VACANCY.job_type}</strong>.</p>
            
            <div style="padding:15px; background:#f0fdf4; border:1px solid #10B981; border-radius:8px; margin:20px 0;">
              <p><strong>🏢 Company:</strong> {company_obj.company_name}</p>
              <p><strong>💼 Position:</strong> {candidate_obj.VACANCY.job_type}</p>
              <p><strong>💰 Salary:</strong> {candidate_obj.VACANCY.salary}</p>
              <p><strong>📋 Job Type:</strong> {candidate_obj.VACANCY.fulltime_parttime}</p>
            </div>

            <p>Congratulations on this achievement! We look forward to working with you.</p>
            <p style="color:#6B7280;">If you have any questions or need further information, please contact {company_obj.company_name}.</p>
            <hr>
            <small style="color:#999;">This is an automated email from CareerMatch System.</small>
          </body>
        </html>
        """
    elif status == "rejected":
        subject = f"Application Status Update - {candidate_obj.VACANCY.job_type}"
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color:#EF4444;">Application Status Update</h2>
            <p>Hello {candidate_obj.USER.name},</p>
            <p>Thank you for your interest in the position of <strong>{candidate_obj.VACANCY.job_type}</strong> at <strong>{company_obj.company_name}</strong>.</p>
            
            <div style="padding:15px; background:#fef2f2; border:1px solid #EF4444; border-radius:8px; margin:20px 0;">
              <p>We have reviewed your application and qualifications. Unfortunately, we have decided to move forward with other candidates whose qualifications more closely match our current requirements.</p>
            </div>

            <p>We appreciate your time and effort in applying. We encourage you to apply for other positions that may be suitable for your profile in the future.</p>
            <p style="color:#6B7280;">Best of luck with your career!</p>
            <hr>
            <small style="color:#999;">This is an automated email from CareerMatch System.</small>
          </body>
        </html>
        """
    else:
        # For other statuses, send a generic update
        subject = f"Application Status Update - {candidate_obj.VACANCY.job_type}"
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color:#2c7be5;">Application Status Update</h2>
            <p>Hello {candidate_obj.USER.name},</p>
            <p>Your application status for the position of <strong>{candidate_obj.VACANCY.job_type}</strong> has been updated to: <strong>{status}</strong></p>
            
            <div style="padding:15px; background:#f0f9ff; border:1px solid #2c7be5; border-radius:8px; margin:20px 0;">
              <p><strong>🏢 Company:</strong> {company_obj.company_name}</p>
              <p><strong>💼 Position:</strong> {candidate_obj.VACANCY.job_type}</p>
            </div>

            <p>If you have any questions, please contact {company_obj.company_name}.</p>
            <hr>
            <small style="color:#999;">This is an automated email from CareerMatch System.</small>
          </body>
        </html>
        """

    send_notification_email(sender_email, app_password, receiver_email, subject, html)
        
    redirect_url = '/view_applied_list#abc' if str(request.session.get('usertype')) == 'candidate' else '/home'
    message = f'Candidate {status}..'

    # Support both normal page requests and fetch/ajax calls
    is_ajax = False
    accept_header = ''
    if hasattr(request, 'headers'):
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        accept_header = request.headers.get('Accept', '')
    else:
        is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        accept_header = request.META.get('HTTP_ACCEPT', '')

    if is_ajax or accept_header.startswith('application/json'):
        return JsonResponse({'message': message, 'redirect': redirect_url})

    return HttpResponse(
        f"<script>alert('{message}');window.location='{redirect_url}'</script>")


def view_selected_candidate(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "VIEW SELECTED CANDIDATE"
    data = candidate.objects.filter(status='selected')
    return render(request, "company/view_selected_list.html", {"data": data})


# def view_applied_candidate(request,id):
#     if "lid" not in request.session:
#         return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
#     request.session['head'] = "VIEW APPLIED CANDIDATE"
#     data = candidate.objects.filter(VACCANCY_id=id)
#     return render(request,"company/view_applied_candidate.html",{"data":data})


# --- SCHEFULE TEST ---

def schedule_test(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "SCHEDULE TEST"
    return render(request, "company/schedule_test.html", {"id": id})


def schedule_test_post(request, id):
    import datetime
    exam_date = request.POST['textfield']
    exam_time = request.POST['textfield2']
    exam_timet = request.POST['textfield3']
    
    # Update candidate with test schedule
    candidate.objects.filter(id=id).update(exam_date=exam_date, exam_ftime=exam_time, exam_ttime=exam_timet,
                                           status="shortlisted")
    
    # Get candidate details
    candidate_obj = candidate.objects.filter(id=id)[0]
    vacancy_id = candidate_obj.VACANCY_id
    request.session['n'] = candidate.objects.filter(VACANCY=vacancy_id, status="pending").count()

    # Send email notification to candidate
    try:
        # Get company details
        company_obj = candidate_obj.VACANCY.COMPANY
        
        # Try to get company email settings
        try:
            mail_settings = candidate_obj.VACANCY.COMPANY
            sender_email = mail_settings.mailprovider
            app_password = mail_settings.apppassword
        except:
            # Fallback to default Gmail settings
            sender_email = "carzfiree@gmail.com"
            app_password = "vtde phpd htcz hcnh"

        receiver_email = candidate_obj.USER.email
        
        # Create email content
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color:#10B981;">📋 Test Scheduled</h2>
            <p>Hello {candidate_obj.USER.name},</p>
            <p>Your test has been scheduled for the position of <strong>{candidate_obj.VACANCY.job_type}</strong>.</p>
            
            <div style="padding:15px; background:#f0fdf4; border:1px solid #10B981; border-radius:8px; margin:20px 0;">
              <p><strong>📅 Test Date:</strong> {exam_date}</p>
              <p><strong>⏰ Start Time:</strong> {exam_time}</p>
              <p><strong>⏱️ End Time:</strong> {exam_timet}</p>
              <p><strong>🏢 Company:</strong> {company_obj.company_name}</p>
            </div>

            <p>Please make sure to:</p>
            <ul>
              <li>Join the test a few minutes before the start time</li>
              <li>Ensure you have a stable internet connection</li>
              <li>Use a computer or laptop with a camera and microphone</li>
              <li>Have a quiet environment for the test</li>
            </ul>

            <p style="color:#6B7280;">If you have any questions, please contact {company_obj.company_name}.</p>
            <hr>
            <small style="color:#999;">This is an automated email from CareerMatch System.</small>
          </body>
        </html>
        """
        
        subject = f"Test Scheduled - {candidate_obj.VACANCY.job_type}"
        send_notification_email(sender_email, app_password, receiver_email, subject, html)
        
    except Exception as e:
        print(f"⚠️ Error sending email: {str(e)}")
        # Don't fail the test scheduling if email fails

    return HttpResponse(
        "<script>alert('Test Scheduled');window.location='/view_applied_candidate/" + str(vacancy_id) + "#abc'</script>")



def view_schedule_test(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "VIEW SCHEDULE TEST"
    data = candidate.objects.filter(id=id)
    return render(request, "company/view_scheduletest.html", {"data": data})




def company_change_password(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "CHANGE PASSWORD"
    return render(request, "company/change_password.html")


def company_change_password_post(request):
    current_password = request.POST['current_password']
    new_password = request.POST['new_password']
    confirm_password = request.POST['confirm_password']
    data = login.objects.filter(password=current_password, id=request.session['lid'])
    if data.exists():
        if new_password == confirm_password:
            login.objects.filter(id=request.session['lid']).update(password=confirm_password)
            return HttpResponse("<script>alert('updated');window.location='/'</script>")
        else:
            return HttpResponse("<script>alert('Not updated');window.location='/company_change_password_post#abc'</script>")
    else:
        return HttpResponse("<script>alert('Not found');window.location='/college_change_password#abc'</script>")


def view_applied_candidate(request, id):
    request.session['uid'] = id
    data = candidate.objects.filter(VACANCY=id)
    return render(request, "company/view_applied_candidate.html", {'data': data})


###################################################################3




def register_student(request):
    request.session['head'] = "register student"
    return render(request, "candidate/registerindex.html")


def register_student_post(request):
    # Get form data
    f_n = request.POST.get('f_n', '').strip()
    l_n = request.POST.get('l_n', '').strip()
    q_f = request.POST.get('q_f', '').strip()
    g_r = request.POST.get('gender', '').strip()
    p_c = request.POST.get('p_c', '').strip()
    p_t = request.POST.get('p_t', '').strip()
    p_h = request.POST.get('p_h', '').strip()
    e_m = request.POST.get('e_m', '').strip()
    p_w = request.POST.get('p_w', '').strip()
    cpd = request.POST.get('cpd', '').strip()

    # Check if email already exists
    res = login.objects.filter(username=e_m)
    if res.exists():
        return HttpResponse("<script>alert('Email already exists');window.location='/register_student'</script>",
                            status=400)

    # Validate passwords match
    if p_w != cpd:
        return HttpResponse("<script>alert('Password does not match');window.location='/register_student'</script>",
                            status=400)

    photo = request.FILES['photo']
    filename = photo.name

    # Save file
    fs = FileSystemStorage()
    filename = fs.save(filename, photo)
    photo_url = fs.url(filename)

    # Create login record
    login_obj = login()
    login_obj.username = e_m
    login_obj.password = p_w
    login_obj.usertype = 'student'
    login_obj.save()

    # Create student record
    user_obj = user()
    user_obj.name = f_n + ' ' + l_n
    user_obj.email = e_m
    user_obj.phone = p_h
    user_obj.place = p_c
    user_obj.image = photo_url
    user_obj.LOGIN = login_obj
    user_obj.save()

    return HttpResponse("<script>alert('Registered successfully');window.location='/'</script>", status=200)


def candidate_view_college(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = ""
    today = datetime.date.today()
    data = vacancy.objects.filter(
        COMPANY__LOGIN__usertype='company',
        apply_from_date__lte=today,
        apply_to_date__gte=today,
    )
    for i in data:
        i.vaccancy_qualification = vaccancy_qualification.objects.filter(VACANCY_id=i.id)
    return render(request, "candidate/viewvaccancyy.html", {"data": data, "today": today})


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


def get_requirements(request, vacancy_id):
    if "lid" not in request.session:
        return JsonResponse({'success': False, 'error': 'Session expired'})

    try:
        # Get all qualifications for this vacancy
        qualifications = vaccancy_qualification.objects.filter(VACANCY_id=vacancy_id)

        # Prepare the data
        requirements_data = []
        for qual in qualifications:
            requirements_data.append({
                'qualification_skill': qual.QUALIFICATION.qualification,
                'type': qual.QUALIFICATION.type
            })
        print("requirements_data", requirements_data)

        return JsonResponse({
            'success': True,
            'requirements': requirements_data,
            'count': len(requirements_data)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file.

    Args:
        pdf_file: Django UploadedFile object

    Returns:
        str: Extracted text from PDF
    """
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return normalize_text(text)
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""


def upload_resume(request, id):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "UPLOAD RESUME"

    # Get vacancy and its requirements
    try:
        vacancy_obj = vacancy.objects.get(id=id)
        requirements = vaccancy_qualification.objects.filter(VACANCY_id=id)
        req_list = [req.QUALIFICATION.qualification for req in requirements]

        context = {
            "id": id,
            "vacancy": vacancy_obj,
            "requirements": requirements,
            "req_list": req_list
        }
        return render(request, "candidate/upload_resume.html", context)
    except Exception as e:
        print(f"Error in upload_resume: {e}")
        return render(request, "candidate/upload_resume.html", {"id": id})


def upload_resume_post(request, id):
    import datetime
    resume = request.FILES['fileField']
    dt = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    fs = FileSystemStorage()
    path = fs.save(resume.name, resume)
    path = fs.url(path)

    # Check if already applied
    data = candidate.objects.filter(VACANCY_id=id, USER=user.objects.get(LOGIN=request.session['lid']))
    if data.exists():
        return HttpResponse(
            "<script>alert('You have already applied for this job');window.location='/view_applied_list#abc'</script>")

    # Extract text from PDF and validate requirements
    resume_text = extract_text_from_pdf(resume)
    print("Extracted Resume Text:", resume_text)
    requirements_objs = vaccancy_qualification.objects.filter(VACANCY_id=id)
    requirements_list = [req.QUALIFICATION.qualification for req in requirements_objs]

    matched_count, total_reqs, matched_items, unmatched_items = check_requirement_match(resume_text, requirements_list)
    match_percentage = (matched_count / total_reqs * 100) if total_reqs > 0 else 0

    # Prepare alert message with validation results
    if total_reqs > 0:
        matched_str = ", ".join(matched_items) if matched_items else "None"
        unmatched_str = ", ".join(unmatched_items) if unmatched_items else "None"
        validation_msg = f"Resume Validation:\\n\\nMatched Skills ({matched_count}/{total_reqs}):\\n{matched_str}\\n\\nMissing Skills:\\n{unmatched_str}\\n\\nMatch Percentage: {match_percentage:.1f}%"
    else:
        validation_msg = "No specific requirements for this job."
    if match_percentage < 50:
        validation_msg += "\\n\\nWarning: Your resume matches less than 50% of the job requirements. Consider updating your resume to improve your chances."
        return HttpResponse(f"<script>alert('{validation_msg}');window.location='/upload_resume/{id}#abc'</script>")    
    # Save candidate application
    obj = candidate()
    obj.exam_date = "pending"
    obj.exam_ftime = "pending"
    obj.exam_ttime = "pending"
    obj.status = "cvshortlist"
    obj.match_percentage = match_percentage
    obj.apply_date = datetime.datetime.now().strftime("%Y-%m-%d")
    obj.apply_time = datetime.datetime.now().strftime("%H:%M:%S")
    obj.link = "pending"
    obj.interview_date = "pending"
    obj.binterview_date = "pending"
    obj.interview_time = "pending"
    obj.binterview_time = "pending"
    obj.no_of_unknown_person = 0
    obj.multiple_person = 0
    obj.resume = path
    obj.USER = user.objects.get(LOGIN=request.session['lid'])
    obj.VACANCY_id = id
    obj.save()

    # Return success with validation details
    alert_msg = f"Applied successfully!\\n\\n{validation_msg}"
    return HttpResponse(f"<script>alert('{alert_msg}');window.location='/view_applied_list#abc'</script>")


def view_applied_list(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "VIEW APPLIED LIST"
    data_qs = candidate.objects.filter(USER__LOGIN=request.session['lid'])
    # Compute whether the mock interview "Start" link should be shown.
    # We compare date (YYYY-MM-DD) and hour:minute (HH:MM) after normalizing time formats.
    import datetime
    for obj in data_qs:
        obj.can_start = str(obj.binterview_date) == str(datetime.datetime.now().date()) and str(obj.binterview_time) == datetime.datetime.now().strftime("%H:%M")
        print(f"Checking interview_date: {obj.binterview_date} against today: {datetime.datetime.now().date()} => can_start: {obj.can_start}")
    request.session['count'] = 0
    return render(request, "candidate/view_applied_list.html", {"data": data_qs})


def view_selected_list(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "VIEW SELECTED LIST"
    data = candidate.objects.filter(USER__LOGIN=request.session['lid'], status="Finalised")
    return render(request, "candidate/view_selected_list.html", {"data": data})


def candidate_change_password(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "CHANGE PASSWORD"
    return render(request, "candidate/change_password.html")


def candidate_change_password_post(request):
    current_password = request.POST['textfield']
    new_password = request.POST['textfield2']
    confirm_password = request.POST['textfield3']
    data = login.objects.filter(username=current_password, id=request.session['lid'])
    if data.exists():
        if new_password == confirm_password:
            login.objects.filter(id=request.session['lid']).update(password=confirm_password)
            return HttpResponse("<script>alert('updated');window.location='/'</script>")
        else:
            return HttpResponse(
                "<script>alert('Not updated');window.location='/candidate_change_password#abc'</script>")
    else:
        return HttpResponse("<script>alert('Not found');window.location='/candidate_change_password#abc'</script>")


def send_complaint(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "SEND COMPLAINT"
    return render(request, "candidate/send_complaint.html")


def send_complaint_post(request):
    import datetime
    complaint = request.POST['textarea']
    obj = suggestions()
    obj.suggestion = complaint
    obj.date = datetime.datetime.now().date()
    obj.type = "candidate"
    obj.LOGIN_id = request.session['lid']
    obj.save()
    return HttpResponse("<script>alert('Success');window.location='/send_complaint#abc'</script>")


def handle_post(request, id):
    try:
        import datetime
        selected_option = request.POST.get('answer')
        correct_answer = request.POST.get('selected_answer')

        if not selected_option or not correct_answer:
            return JsonResponse({
                'success': False,
                'message': 'Invalid submission'
            }, status=400)

        mark = 1 if selected_option == correct_answer else 0

        # Use a zero-based session counter for the current question index.
        # Default to 0 if not present or invalid.
        try:
            current_count = int(request.session.get('count', 0) or 0)
        except (ValueError, TypeError):
            current_count = 0

        # save test result
        tr = test_results()
        tr.USER = user.objects.get(LOGIN=request.session['lid'])
        tr.QUESTION_id = id   # ✅ FIXED
        tr.mark = mark
        tr.status = 'exam attended'
        tr.save()

        candidate_instance = candidate.objects.get(id=request.session.get('cid', request.session.get('testid')))

        exam_obj, created = exam.objects.get_or_create(
            CANDIDATE=candidate_instance,
            defaults={'mark': mark}
        )

        if not created:
            exam_obj.mark += mark
            exam_obj.save()

        cutoff = int(candidate_instance.VACANCY.cuttoff)
        total_marks = exam_obj.mark
        if total_marks >= cutoff:
            candidate.objects.filter(
                id=candidate_instance.id
            ).update(status='selecledforinterview')


            try:
                candidate_instance = candidate.objects.get(id=candidate_instance.id)
                interview_date = candidate_instance.interview_date
                interview_time = candidate_instance.interview_time
                candidate_obj = candidate.objects.get(id=candidate_instance.id)
                # Get company details (vacancy model uses `COMPANY` FK)
                company_obj = candidate_obj.VACANCY.COMPANY
                
                # Try to get company email settings
                try:
                    mail_settings = candidate_obj.VACANCY.COMPANY
                    sender_email = mail_settings.mailprovider
                    app_password = mail_settings.apppassword
                except:
                    # Fallback to default Gmail settings
                    sender_email = "carzfiree@gmail.com"
                    app_password = "vtde phpd htcz hcnh"

                receiver_email = candidate_obj.USER.email
                
                # Create email content
                html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2 style="color:#10B981;">🤖 Bot Interview Scheduled</h2>
                    <p>Hello {candidate_obj.USER.name},</p>
                    <p>Great news! Your bot interview has been scheduled for the position of <strong>{candidate_obj.VACANCY.job_type}</strong>.</p>
                    
                    <div style="padding:15px; background:#f0fdf4; border:1px solid #10B981; border-radius:8px; margin:20px 0;">
                    <p><strong>📅 Interview Date:</strong> {interview_date}</p>
                    <p><strong>⏰ Interview Time:</strong> {interview_time}</p>
                    <p><strong>🏢 Company:</strong> {company_obj.company_name}</p>
                    <p><strong>🤖 Interview Type:</strong> AI-Powered Bot Interview</p>
                    </div>

                    <p>Please make sure to:</p>
                    <ul>
                    <li>Join the bot interview a few minutes before the scheduled time</li>
                    <li>Ensure you have a stable internet connection</li>
                    <li>Use a computer or laptop with a camera and microphone</li>
                    <li>Have a quiet and well-lit environment</li>
                    <li>Answer questions clearly and naturally</li>
                    <li>Ensure proper lighting so the AI can see your expressions</li>
                    </ul>

                    <p style="color:#6B7280;">If you have any questions or technical issues, please contact {company_obj.company_name}.</p>
                    <hr>
                    <small style="color:#999;">This is an automated email from CareerMatch System.</small>
                </body>
                </html>
                """
                
                subject = f"Bot Interview Scheduled - {candidate_obj.VACANCY.job_type}"
                send_notification_email(sender_email, app_password, receiver_email, subject, html)
                
            except Exception as e:
                print(f"⚠️ Error sending email: {str(e)}")
                # Don't fail the bot interview scheduling if email fails


        else:
            candidate.objects.filter(
                id=candidate_instance.id
            ).update(status='examattended')

        # After saving the answer, advance the counter to the next question
        request.session['count'] = current_count + 1
        new_count = request.session['count']
        # Explicitly save session to ensure persistence
        request.session.save()
        print(f"📤 ANSWER SUBMITTED:")
        print(f"   Question ID: {id}")
        print(f"   Previous count: {current_count}")
        print(f"   New count: {new_count}")
        print(f"   Selected answer: {selected_option}")
        print(f"   Correct answer: {correct_answer}")
        print(f"   Mark awarded: {mark}")
        print(f"   Session saved explicitly")

        # check completion using the incremented count (new_count)
        total_questions = question.objects.filter(VACANCY=candidate_instance.VACANCY).count()

        # new_count is the zero-based index of the next question; when it
        # is >= total_questions the exam is complete.
        if new_count >= total_questions:
            if total_marks < cutoff:
                # All questions answered but failed
                print(f"❌ EXAM FAILED - count ({new_count}) >= total ({total_questions})")
                try:
                    candidate_obj = candidate.objects.get(id=candidate_instance.id)
                    company_obj = candidate_obj.VACANCY.COMPANY
                    try:
                        mail_settings = candidate_obj.VACANCY.COMPANY
                        sender_email = mail_settings.mailprovider
                        app_password = mail_settings.apppassword
                    except:
                        sender_email = "carzfiree@gmail.com"
                        app_password = "vtde phpd htcz hcnh"
                    receiver_email = candidate_obj.USER.email
                    html = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; color: #333;">
                        <h2 style="color:#EF4444;">Application Update</h2>
                        <p>Hello {candidate_obj.USER.name},</p>
                        <p>We regret to inform you that you did not meet the required cutoff score for the position of <strong>{candidate_obj.VACANCY.job_type}</strong>.</p>
                        
                        <div style="padding:15px; background:#fef2f2; border:1px solid #EF4444; border-radius:8px; margin:20px 0;">
                        <p><strong>Your Score:</strong> {total_marks}/{total_questions}</p>
                        <p><strong>Required Cutoff:</strong> {cutoff}/{total_questions}</p>
                        <p><strong>🏢 Company:</strong> {company_obj.company_name}</p>
                        </div>

                        <p>We appreciate your interest in the position and encourage you to apply for future opportunities that match your qualifications.</p>
                        <p style="color:#6B7280;">If you have any questions, please contact {company_obj.company_name}.</p>
                        <hr>
                        <small style="color:#999;">This is an automated email from CareerMatch System.</small>
                    </body>
                    </html>
                    """
                    
                    subject = f"Application Update - {candidate_obj.VACANCY.job_type}"
                    send_notification_email(sender_email, app_password, receiver_email, subject, html)
                    
                except Exception as e:
                    print(f"⚠️ Error sending failure email: {str(e)}")
                
            # All questions answered and passed
            print(f"✅ EXAM COMPLETED - count ({new_count}) >= total ({total_questions})")
            return JsonResponse({
                'success': True,
                'completed': True,
                'current_count': new_count,
                'redirect': '/exam-terminated/'
            })

        # Return current_count so frontend can load the correct next question
        print(f"⏭️ NEXT QUESTION - Moving from count {current_count} to {new_count}")
        return JsonResponse({
            'success': True,
            'completed': False,
            'current_count': new_count,
            'redirect': f"/view_sample_question/{request.session.get('cid', request.session.get('testid','0'))}#abc"
        })

    except Exception as e:
        print("SUBMIT ERROR:", e)
        return JsonResponse({
            'success': False,
            'message': 'Submission failed. Try again'
        }, status=500)

# import json
# from django.http import JsonResponse, HttpResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.shortcuts import render, redirect
# from django.utils import timezone
# from .face_recognition_utilss import SimpleFaceDetector
#
#
# # Initialize face detector
# face_detector = SimpleFaceDetector()
#
#
# @csrf_exempt
# def detect_faces_api(request):
#     """API endpoint for face detection"""
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             image_data = data.get('image_data')
#
#             if not image_data:
#                 return JsonResponse({"success": False, "message": "No image data provided"})
#
#             result = face_detector.detect_faces(image_data)
#             return JsonResponse(result)
#
#         except Exception as e:
#             return JsonResponse({"success": False, "message": str(e)})
#
#     return JsonResponse({"success": False, "message": "Only POST method allowed"})
#
#
# @csrf_exempt
# def check_proctoring_api(request):
#     """API endpoint for proctoring check"""
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             image_data = data.get('image_data')
#             candidate_id = data.get('candidate_id')
#
#             if not image_data or not candidate_id:
#                 return JsonResponse({
#                     "success": False,
#                     "message": "Image data and candidate ID are required"
#                 })
#
#             # Check proctoring
#             result = face_detector.check_proctoring(image_data, candidate_id)
#
#             # Save violations to database
#             if result.get("success") and result.get("violations"):
#                 violations = result["violations"]
#                 for violation in violations:
#                     # Save screenshot
#                     screenshot_path = face_detector.save_screenshot(
#                         image_data,
#                         candidate_id,
#                         violation["type"]
#                     )
#
#                     # Create violation record
#                     try:
#                         cand = candidate.objects.get(id=candidate_id)
#
#                         ProctoringViolation.objects.create(
#                             candidate=cand,
#                             violation_type=violation["type"],
#                             details=violation["message"],
#                             screenshot=screenshot_path
#                         )
#
#                         # Update candidate's violation counts
#                         if violation["type"] == 'multiple_faces':
#                             current_count = int(cand.multiple_person) if cand.multiple_person else 0
#                             cand.multiple_person = str(current_count + 1)
#                         elif violation["type"] == 'no_face':
#                             current_count = int(cand.no_of_unknown_person) if cand.no_of_unknown_person else 0
#                             cand.no_of_unknown_person = str(current_count + 1)
#
#                         cand.save()
#
#                     except candidate.DoesNotExist:
#                         print(f"Candidate {candidate_id} not found")
#
#             return JsonResponse(result)
#
#         except Exception as e:
#             return JsonResponse({"success": False, "message": str(e)})
#
#     return JsonResponse({"success": False, "message": "Only POST method allowed"})
#
#
# from django.shortcuts import render, redirect
# from django.http import HttpResponse
# import datetime
# from .models import candidate, question, ProctoringViolation
#
#
# def view_sample_question(request, id):
#     request.session['head'] = "VIEW SAMPLE QUESTION"
#
#     try:
#         # ------------------ Candidate ------------------
#         try:
#             candidate_data = candidate.objects.get(id=id)
#         except candidate.DoesNotExist:
#             return HttpResponse(
#                 "<script>alert('Candidate not found!');"
#                 "window.location='/view_shortlisted_list#abc'</script>"
#             )
#
#         request.session['cid'] = id
#
#         # ------------------ Proctoring Block ------------------
#         no_unknown = int(candidate_data.no_of_unknown_person or 0)
#         multiple_persons = int(candidate_data.multiple_person or 0)
#
#         if no_unknown >= 2 and multiple_persons >= 2:
#             return HttpResponse(
#                 "<script>alert('Unauthorised events occurred. Exam is blocked!!');"
#                 f"window.location='/view_exam_date/{id}';</script>"
#             )
#
#         # ------------------ Questions ------------------
#         questions = question.objects.filter(
#             VACANCY=candidate_data.VACANCY
#         ).order_by('id')
#
#         total_questions = questions.count()
#
#         if total_questions == 0:
#             return HttpResponse(
#                 "<script>alert('No questions available');"
#                 "window.location='/view_applied_list#abc'</script>"
#             )
#
#         # ------------------ Session Init ------------------
#         if 'count' not in request.session:
#             request.session['count'] = 0
#
#         if 'testid' not in request.session:
#             request.session['testid'] = id
#
#         current_index = request.session['count']
#
#         # ------------------ Exam Completed ------------------
#         if current_index >= total_questions:
#             request.session['count'] = 0
#             return HttpResponse(
#                 "<script>alert('Exam completed!');"
#                 "window.location='/view_applied_list#abc'</script>"
#             )
#
#         current_question = questions[current_index]
#
#         # ------------------ Remaining Time ------------------
#         remaining_seconds = 600  # default 10 mins
#
#         try:
#             if candidate_data.exam_ftime and candidate_data.exam_ttime:
#                 start_h, start_m = map(int, candidate_data.exam_ftime.split(':')[:2])
#                 end_h, end_m = map(int, candidate_data.exam_ttime.split(':')[:2])
#
#                 now = datetime.now()
#                 start_total = start_h * 60 + start_m
#                 end_total = end_h * 60 + end_m
#                 current_total = now.hour * 60 + now.minute
#
#                 if start_total <= current_total <= end_total:
#                     remaining_seconds = (end_total - current_total) * 60
#         except Exception as e:
#             print("Time error:", e)
#
#         # ------------------ Violations ------------------
#         recent_violations = ProctoringViolation.objects.filter(
#             candidate=candidate_data
#         ).order_by('-timestamp')[:5]
#
#         # ------------------ Context ------------------
#         context = {
#             'data': current_question,
#             'c': current_index + 1,  # display purpose
#             'total_questions': total_questions,
#             'remaining_seconds': remaining_seconds,
#             'testid': id,
#             'candidate_id': candidate_data.id,
#             'candidate_name': candidate_data.USER.name,
#             'no_of_unknown_person': no_unknown,
#             'multiple_person': multiple_persons,
#             'recent_violations': recent_violations,
#             'total_violations': recent_violations.count(),
#             'exam_start_time': candidate_data.exam_ftime,
#             'exam_end_time': candidate_data.exam_ttime,
#         }
#
#         return render(request, 'candidate/attend_exam.html', context)
#
#     except Exception as e:
#         print("view_sample_question error:", e)
#         request.session['count'] = 0
#         return HttpResponse(
#             "<script>alert('Exam completed!');"
#             "window.location='/view_applied_list#abc'</script>"
#         )
#
# def exam_terminated(request):
#     """Render a simple exam terminated page."""
#     try:
#         return render(request, 'candidate/exam_terminated.html')
#     except Exception as e:
#         print(f"Error rendering exam_terminated: {e}")
#         return HttpResponse("<h1>Exam terminated</h1>")
#
#
def get_violations_api(request, candidate_id):
    """Get violations for a candidate"""
    try:
        violations = ProctoringViolation.objects.filter(
            candidate_id=candidate_id
        ).order_by('-timestamp')[:10]

        violations_list = []
        for violation in violations:
            violations_list.append({
                'id': violation.id,
                'type': violation.get_violation_type_display(),
                'timestamp': violation.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                'details': violation.details,
                'screenshot': violation.screenshot.url if violation.screenshot else None
            })

        return JsonResponse({
            'success': True,
            'violations': violations_list,
            'count': len(violations_list)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
#
#
def reset_violation_count(request, candidate_id):
    """Reset violation counts for a candidate (admin function)"""
    if request.method == 'POST':
        try:
            cand = candidate.objects.get(id=candidate_id)
            cand.no_of_unknown_person = "0"
            cand.multiple_person = "0"
            cand.save()

            # Also delete all ProctoringViolation records for this candidate
            ProctoringViolation.objects.filter(candidate=cand).delete()

            return JsonResponse({'success': True, 'message': 'Violation counts reset'})

        except candidate.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Candidate not found'})

    return JsonResponse({'success': False, 'message': 'Only POST method allowed'})


def exam_terminated(request):
    """Display exam terminated page when exam is blocked due to violations."""
    violation_count = request.GET.get('violations', 'multiple')
    return render(request, 'candidate/exam_terminated.html', {
        'violation_count': violation_count,
        'message': '❌ EXAM BLOCKED! You have exceeded the maximum number of violations allowed. Your exam access has been denied.'
    })


import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import candidate, ProctoringViolation
import base64

# Lazy initialization of face detector - initialized on first use
face_detector = None


def get_face_detector():
    """Lazy load face detector to avoid TensorFlow initialization at startup.

    Returns the `SimpleFaceDetector` instance (initializes on first use).
    This is a pure utility function and should not be decorated as a view.
    """
    global face_detector
    if face_detector is None:
        from .face_recognition_utils import SimpleFaceDetector
        face_detector = SimpleFaceDetector()
    return face_detector


def get_face_detector_view(request):
    """HTTP view wrapper around `get_face_detector` for the URL endpoint.

    This keeps the internal utility `get_face_detector()` free of view
    semantics so other code can call it without passing a `request`.
    """
    try:
        detector = get_face_detector()
        return JsonResponse({
            "status": "initialized",
            "message": "Face detector initialized",
            "timestamp": datetime.datetime.now().isoformat()
        }, status=200)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=503)


@csrf_exempt
def proctoring_health_check(request):
    """Health check endpoint for proctoring system - verifies backend is responsive"""
    if request.method == 'GET':
        try:
            # Try to import face_recognition to verify dependencies
            import face_recognition

            # Try to get the face detector - this will initialize if needed
            detector = get_face_detector()

            return JsonResponse({
                "status": "healthy",
                "message": "Proctoring backend is operational",
                "services": {
                    "face_recognition": "available",
                    "detector": "initialized",
                    "timestamp": datetime.datetime.now().isoformat()
                }
            }, status=200)

        except ImportError as e:
            logger.error(f"Missing dependency for proctoring: {e}")
            return JsonResponse({
                "status": "unhealthy",
                "message": "Required library not installed",
                "error": str(e),
                "services": {
                    "face_recognition": "missing"
                }
            }, status=503)

        except Exception as e:
            logger.error(f"Proctoring health check failed: {e}")
            return JsonResponse({
                "status": "unhealthy",
                "message": str(e),
                "error": type(e).__name__
            }, status=503)

    return JsonResponse({
        "status": "error",
        "message": "Only GET method allowed"
    }, status=405)


@csrf_exempt
def detect_faces_api(request):
    """API endpoint for face detection"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image_data')

            if not image_data:
                return JsonResponse({"success": False, "message": "No image data provided"})

            detector = get_face_detector()
            result = detector.detect_faces(image_data)
            return JsonResponse(result)

        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "Only POST method allowed"})


@csrf_exempt
def check_proctoring_api(request):
    """API endpoint for proctoring check with real face verification and violation detection"""
    if request.method == 'POST':
        try:
            # Safely parse JSON body with error handling for broken pipes
            try:
                # Log raw body for debugging (safe in dev only)
                raw_body = request.body.decode('utf-8', errors='replace') if request.body else ''
                print(f"[check_proctoring_api] Raw request body (truncated 1024): {raw_body[:1024]}")

                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                return JsonResponse({
                    "success": False,
                    "message": "Invalid JSON data",
                    "raw_body": raw_body
                }, status=400)
            except Exception as e:
                print(f"❌ Request body error (possible client disconnect): {e}")
                return JsonResponse({
                    "success": False,
                    "message": "Request processing error",
                    "error": str(e)
                }, status=400)

            # Validate required fields
            # Defensive handling: if JSON isn't a dict, fail clearly
            if not isinstance(data, dict):
                return JsonResponse({"success": False, "message": "JSON payload must be an object"}, status=400)

            image_data = (data.get('image_data') or '').strip()
            candidate_id = data.get('candidate_id')
            request.session['cid'] = data.get('candidate_id')
            violation_type = data.get('violation_type', None)  # Client-side violation type
            violation_message = data.get('violation_message', 'No details provided')  # Client-side violation message

            # Check if this is a violation-only request (no image for proctoring check)
            is_violation_only = not image_data and violation_type is not None

            # Check image size to prevent processing large payloads
            if not image_data and not is_violation_only:
                print(
                    f"[check_proctoring_api] Missing image_data and not a violation-only request. Received keys: {list(data.keys())}")
                return JsonResponse({
                    "success": False,
                    "message": "Image data is required for proctoring check",
                    "received_keys": list(data.keys())
                }, status=400)

            if not candidate_id or candidate_id == 0:
                print(
                    f"[check_proctoring_api] Missing or invalid candidate_id (0). Received payload keys: {list(data.keys())}")
                return JsonResponse({
                    "success": False,
                    "message": "Valid Candidate ID is required",
                    "received_keys": list(data.keys()),
                    "raw_body_preview": raw_body[:512]
                }, status=400)

            # Limit image data size (max 2MB base64)
            if len(image_data) > 2 * 1024 * 1024:  # 2MB limit
                print(f"⚠️ Image data too large: {len(image_data)} bytes")
                return JsonResponse({
                    "success": False,
                    "message": "Image data is too large. Please check your camera settings."
                }, status=413)

            try:
                cand = candidate.objects.get(id=candidate_id)
            except candidate.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "message": "Candidate not found"
                }, status=404)

            # Get or create answer sheet for this candidate
            # from .models import answer_sheet
            # try:
            #     ans_sheet = answer_sheet.objects.filter(CANDIDATE=cand, SCHEDULE=request.session['suid']).latest('id')
            # except answer_sheet.DoesNotExist:
            #     # Create answer sheet if it doesn't exist
            #     ans_sheet = answer_sheet.objects.create(
            #         SCHEDULE=request.session['suid'],
            #         CANDIDATE=cand,
            #         total_mark='0',
            #         status='ongoing',
            #         no_of_unknown_person='0',
            #         multiple_person='0'
            #     )

            detector = get_face_detector()

            # ==============================================================
            # STEP 0: SAVE CLIENT-SIDE VIOLATIONS (tab_hidden, window_switch, etc)
            # ==============================================================
            if violation_type:
                try:
                    ProctoringViolation.objects.create(
                        candidate=cand,
                        violation_type=violation_type,
                        details=violation_message
                    )
                    print(f"🚨 Security Violation Recorded: {violation_type} - {violation_message}")
                except Exception as e:
                    print(f"Error recording {violation_type} violation: {e}")

            # If this is violation-only request, return early (no image data)
            if is_violation_only:
                return JsonResponse({
                    "success": True,
                    "violation_recorded": True,
                    "violation_type": violation_type,
                    "message": f"Security violation {violation_type} recorded successfully"
                })

            # ==============================================================
            # STEP 1: FACE VERIFICATION - Compare current face with registered photo
            # ==============================================================
            global _face_encoding_count, _max_concurrent_encodings

            face_comparison = None
            skip_face_check = False

            # Check if we're at capacity for concurrent face encodings
            with _face_encoding_lock:
                if _face_encoding_count >= _max_concurrent_encodings:
                    print(
                        f"⚠️ Face encoding queue full ({_face_encoding_count}/{_max_concurrent_encodings}). Skipping face check to prevent server overload.")
                    skip_face_check = True
                else:
                    _face_encoding_count += 1

            try:
                if not skip_face_check:
                    logger.info(
                        f"[API] Starting face comparison for candidate {candidate_id} ({_face_encoding_count}/{_max_concurrent_encodings} concurrent)")
                    print(f"[API] Starting face comparison for candidate {candidate_id}")

                    try:
                        face_comparison = detector._compare_with_registered(candidate_id, image_data)
                        logger.info(f"[API] Face comparison completed for candidate {candidate_id}")
                        print(f"[API] Face comparison completed for candidate {candidate_id}")
                    except Exception as fc_error:
                        logger.error(f"[API] Face comparison threw exception: {type(fc_error).__name__}: {fc_error}",
                                     exc_info=True)
                        print(f"[API] Face comparison threw exception: {fc_error}")
                        # Fallback - don't block on face comparison errors
                        face_comparison = {
                            'match': False,
                            'score': 0.0,
                            'method': 'face_comparison_error'
                        }
                else:
                    # Skip face check - return neutral result
                    face_comparison = {
                        'match': True,  # Don't penalize for skipped check
                        'score': 0.5,
                        'method': 'skipped_overload'
                    }
            finally:
                # Always decrement the counter when done
                with _face_encoding_lock:
                    if not skip_face_check and _face_encoding_count > 0:
                        _face_encoding_count -= 1

            face_match = face_comparison.get('match', False)
            comparison_method = face_comparison.get('method', 'none')
            match_score = face_comparison.get('score', 0.0)

            print(f"🔍 Face comparison result: Match={face_match}, Method={comparison_method}, Score={match_score:.3f}")

            # Track face mismatch violations - but don't block on first mismatch
            # Only create a violation record to accumulate count
            if not face_match:
                # Log face mismatch as warning, not blocking condition
                # Will check accumulated count later to block exam
                try:
                    ProctoringViolation.objects.create(
                        candidate=cand,
                        violation_type='face_mismatch',
                        details=f'Face does not match registered photo (Method: {comparison_method}, Match Score: {match_score:.3f})'
                    )
                except Exception as e:
                    print(f"Error creating face mismatch violation: {e}")
            else:
                # Face matched successfully
                print(f"✅ Face verification passed for candidate {candidate_id}")

            # ==============================================================
            # STEP 2: CHECK PROCTORING VIOLATIONS - Face detection, head movement, multiple persons
            # ==============================================================
            result = detector.check_proctoring(image_data, candidate_id)

            if not result.get("success"):
                return JsonResponse({
                    "success": False,
                    "message": f"Proctoring check failed: {result.get('message')}"
                })

            violations = result.get("violations", [])
            exam_blocked = False
            blocking_violation = None

            # ==============================================================
            # STEP 3: PROCESS VIOLATIONS AND SAVE TO DATABASE
            # ==============================================================
            for violation in violations:
                violation_type = violation['type']

                # Save screenshot
                screenshot_path = detector.save_screenshot(
                    image_data,
                    candidate_id,
                    violation_type
                )

                # Create violation record
                try:
                    ProctoringViolation.objects.create(
                        candidate=cand,
                        violation_type=violation_type,
                        details=violation.get('message', ''),
                        screenshot=screenshot_path
                    )
                except Exception as e:
                    print(f"Error creating violation record: {e}")

                # ==============================================================
                # STEP 4: DETERMINE BLOCKING CONDITIONS
                # ==============================================================

                # Multiple faces - block on second occurrence (consistent with view_sample_question)
                if violation_type == 'multiple_faces':
                    try:
                        # ans_sheets = answer_sheet.objects.get(CANDIDATE=cand, SCHEDULE=request.session['suid'])

                        # Check if we already incremented this counter in the last 5 seconds
                        # to prevent duplicate counting from rapid successive frames
                        recent_multiple_face_violation = ProctoringViolation.objects.filter(
                            candidate=cand,
                            violation_type='multiple_faces',
                            timestamp__gte=datetime.datetime.now() - timedelta(seconds=5)
                        ).count()

                        # Only increment if this is the first violation or it's been more than 5 seconds
                        if recent_multiple_face_violation <= 1:  # Current one is just created above
                            # current_count = int(ans_sheet.multiple_person) if ans_sheet.multiple_person and str(
                            #     ans_sheet.multiple_person).isdigit() else 0
                            # current_count += 1
                            # ans_sheet.multiple_person = current_count  # Store as integer, not string
                            # ans_sheet.save()

                            print(f"📊 Multiple faces count incremented: for candidate {candidate_id}")
                        else:
                            print(f"⏭️ Skipping duplicate multiple_faces increment (detected within 5 seconds)")

                        # Block only on second or more violations
                        # current_count = int(ans_sheet.multiple_person) if ans_sheet.multiple_person and str(
                        #     ans_sheet.multiple_person).isdigit() else 0
                        if current_count >= 2:
                            exam_blocked = True
                            blocking_violation = {
                                "type": "multiple_faces",
                                "count": current_count,
                                "message": f"❌ EXAM BLOCKED! Multiple unauthorized persons detected {current_count} times. Exam access denied."
                            }
                    except Exception as e:
                        print(f"Error processing multiple_faces violation: {e}")

                # No face detected - block on second occurrence
                elif violation_type == 'no_face':
                    try:
                        # Check if we already incremented this counter in the last 5 seconds
                        # to prevent duplicate counting from rapid successive frames


                        # ans_sheets = answer_sheet.objects.get(CANDIDATE=cand, SCHEDULE=request.session['suid'])
                        recent_no_face_violation = ProctoringViolation.objects.filter(
                            candidate=cand,
                            violation_type='no_face',
                            timestamp__gte=datetime.datetime.now() - timedelta(seconds=5)
                        ).count()

                        # Only increment if this is the first violation or it's been more than 5 seconds
                        if recent_no_face_violation <= 1:  # Current one is just created above
                            # current_count = int(
                            #     ans_sheet.no_of_unknown_person) if ans_sheet.no_of_unknown_person and str(
                            #     ans_sheet.no_of_unknown_person).isdigit() else 0
                            # current_count += 1
                            # ans_sheet.no_of_unknown_person = current_count  # Store as integer, not string
                            # ans_sheet.save()

                            print(f"📊 No face count incremented: for candidate {candidate_id}")
                        else:
                            print(f"⏭️ Skipping duplicate no_face increment (detected within 5 seconds)")

                        # Block on second or more violations
                        # current_count = int(ans_sheet.no_of_unknown_person) if ans_sheet.no_of_unknown_person and str(
                        #     ans_sheet.no_of_unknown_person).isdigit() else 0
                        if recent_no_face_violation >= 2:
                            exam_blocked = True
                            blocking_violation = {
                                "type": "no_face",
                                "count": recent_no_face_violation,
                                "message": f"❌ EXAM BLOCKED! No face detected {current_count} times. Exam access denied."
                            }
                    except Exception as e:
                        print(f"Error processing no_face violation: {e}")

                # Head movement violations - track, debounce duplicates, and block on threshold
                elif violation_type == 'head_movement':
                    try:
                        print(f"⚠️ Head movement detected for candidate {candidate_id}")

                        # Ensure we have the answer_sheet instance for this candidate+schedule
                        # ans_sheets = answer_sheet.objects.get(CANDIDATE=cand, SCHEDULE=request.session['suid'])

                        # Short debounce window to avoid duplicate counting from rapid frames
                        recent_head_move_short = ProctoringViolation.objects.filter(
                            candidate=cand,
                            violation_type='head_movement',
                            timestamp__gte=datetime.datetime.now() - timedelta(seconds=5)
                        ).count()

                        if recent_head_move_short > 1:
                            # Skip duplicate processing for near-identical frames
                            print(f"⏭️ Skipping duplicate head_movement event (within 5s) for {candidate_id}")
                        else:
                            # Count head movements within a reasonable window (e.g., 3 minutes)
                            recent_window_minutes = 3
                            recent_head_move_count = ProctoringViolation.objects.filter(
                                candidate=cand,
                                violation_type='head_movement',
                                timestamp__gte=datetime.datetime.now() - timedelta(minutes=recent_window_minutes)
                            ).count()

                            print(
                                f"📊 Head movement count in last {recent_window_minutes} minutes: {recent_head_move_count} for candidate {candidate_id}")

                            # Thresholds: allow occasional movement, block if repeated frequently
                            HEAD_MOVE_BLOCK_THRESHOLD = 10  # block if 5+ events in the window

                            if recent_head_move_count >= HEAD_MOVE_BLOCK_THRESHOLD:
                                exam_blocked = True
                                blocking_violation = {
                                    "type": "head_movement",
                                    "count": recent_head_move_count,
                                    "message": f"❌ EXAM BLOCKED! Repeated head movement detected ({recent_head_move_count} times). Exam access denied."
                                }
                            else:
                                # Not blocking yet; just a warning entry for audit trail
                                print(
                                    f"⚠️ Head movement warning recorded ({recent_head_move_count}/{HEAD_MOVE_BLOCK_THRESHOLD}) for candidate {candidate_id}")
                    except Exception as e:
                        print(f"Error processing head_movement violation: {e}")

            # ==============================================================
            # STEP 5: RETURN RESPONSE - Include current violation counts
            # ==============================================================
            # Get current violation counts from answer_sheet
            # try:
            #     current_no_face_count = int(ans_sheet.no_of_unknown_person) if ans_sheet.no_of_unknown_person and str(
            #         ans_sheet.no_of_unknown_person).strip().isdigit() else 0
            #     current_multi_face_count = int(ans_sheet.multiple_person) if ans_sheet.multiple_person and str(
            #         ans_sheet.multiple_person).strip().isdigit() else 0
            # except (ValueError, TypeError, AttributeError):
            #     current_no_face_count = 0
            #     current_multi_face_count = 0
            current_no_face_count = 0
            current_multi_face_count = 0

            if exam_blocked and blocking_violation:
                return JsonResponse({
                    "success": False,
                    "exam_blocked": True,
                    "violation_type": blocking_violation['type'],
                    "violation_count": blocking_violation.get('count', 0),
                    "no_face_count": current_no_face_count,
                    "multi_face_count": current_multi_face_count,
                    "message": blocking_violation['message']
                })

            # Return success with violation details and current counts
            # Include face verification info but don't block the exam
            ans_sheets = cand

            face_mismatch_count = ProctoringViolation.objects.filter(
                candidate=ans_sheets,
                violation_type='face_mismatch'
            ).count()

            return JsonResponse({
                "success": True,
                "face_verified": face_match,
                "face_match_score": match_score,
                "comparison_method": comparison_method,
                "face_mismatch_count": face_mismatch_count,
                "violations_detected": len(violations),
                "violations": violations if violations else [],
                "heads_detected": result.get('heads_detected', 1),
                "no_face_count": current_no_face_count,
                "multi_face_count": current_multi_face_count,
                "client_violation_recorded": violation_type is not None,
                "client_violation_type": violation_type,
                "message": f"Proctoring check complete. Face verified: {face_match}. {len(violations)} potential issue(s) detected." if violations else f"Proctoring check passed. Face verified: {face_match}."
            })

        except candidate.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Candidate not found"
            })
        except (BrokenPipeError, ConnectionResetError) as e:
            # Client disconnected - don't log as error, just silently fail
            print(f"⚠️ Client disconnected during proctoring check: {type(e).__name__}")
            return JsonResponse({
                "success": False,
                "message": "Connection lost. Please refresh and try again."
            }, status=500)
        except Exception as e:
            # Log unexpected errors with full context
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__
            tb = traceback.format_exc()

            logger.error(f"❌ Error in check_proctoring_api: {error_type}: {error_msg}", extra={
                'error_type': error_type,
                'error_msg': error_msg,
                'candidate_id': candidate_id if 'candidate_id' in locals() else 'unknown',
                'traceback': tb
            })
            print(f"❌ Error in check_proctoring_api: {error_type}: {error_msg}")
            print(f"Traceback: {tb}")

            return JsonResponse({
                "success": False,
                "message": "Proctoring check failed. Backend service encountered an error."
            }, status=500)

    return JsonResponse({
        "success": False,
        "message": "Only POST method allowed"
    }, status=405)


import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def view_sample_question(request, id):
    # request.session['cand_id']=id
    # Check if it's an AJAX request (Django <3.2 compatibility)
    is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    print('is_ajax:', is_ajax)

    try:
        # Validate session data

        # Get candidate data
        data = candidate.objects.filter(id=id)
        if not data.exists():
            if is_ajax:
                return JsonResponse({'error': 'Candidate not found'}, status=404)
            return HttpResponse("Candidate not found", status=404)

        candidate_data = data[0]

        # Set session variables (provide multiple aliases for compatibility)
        request.session['cand_id'] = id
        request.session['cid'] = id  # legacy key used by other handlers
        request.session['testid'] = id  # ensure testid is available
        request.session['suid'] = candidate_data.VACANCY.id

        print(candidate_data, "CD")

        #
        # Get answer sheet for violation counts
        # Use candidate_data for violation counts
        ans_sheet = candidate_data  # For compatibility, use candidate_data

        # Check for exam blocking conditions. Safely parse numeric counters;
        # fields may contain non-numeric values or strings.
        def _safe_int(v, default=0):
            """Safely convert a value to integer, handling CharField storage"""
            if v is None or v == '':
                return default
            try:
                # Handle both int and string types
                val = int(str(v).strip())
                return max(0, val)  # Ensure non-negative
            except (ValueError, TypeError, AttributeError) as e:
                print(f"Warning: Could not parse {v} as integer: {e}")
                return default

        # Extract violation counts with safe parsing
        # Get fresh violation counts from answer_sheet
        no_unknown = _safe_int(ans_sheet.no_of_unknown_person, 0)
        multiple_persons = _safe_int(ans_sheet.multiple_person, 0)

        # Validate counts are non-negative
        if no_unknown < 0:
            no_unknown = 0
            ans_sheet.no_of_unknown_person = 0
            ans_sheet.save()
        if multiple_persons < 0:
            multiple_persons = 0
            ans_sheet.multiple_person = 0
            ans_sheet.save()

        # Count face mismatch violations from database
        try:
            from .models import ProctoringViolation
            face_mismatch_count = ProctoringViolation.objects.filter(
                candidate=candidate_data,
                violation_type='face_mismatch'
            ).count()
        except Exception as e:
            print(f"Warning: Could not count face mismatch violations: {e}")
            face_mismatch_count = 0

        print(
            f"📊 Exam blocking check - No Face: {no_unknown}, Multiple Faces: {multiple_persons}, Face Mismatch: {face_mismatch_count}")

        # BLOCK EXAM CONDITIONS:
        # Increased thresholds to 4 to account for temporary camera adjustments and brief detection glitches
        # with 3-second proctoring intervals during a 30-60 minute exam
        # 1. Four or more proctoring violations (no_face OR multiple_faces)
        if no_unknown >= 4 or multiple_persons >= 4:
            error_msg = "❌ EXAM BLOCKED! Unauthorized event detected during exam. Your exam has been terminated."
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'exam_blocked': True,
                    'message': error_msg,
                    'redirect': '/student_home'
                })
            return HttpResponse(
                f"<script>alert('{error_msg}');window.location='/student_home';</script>"
            )

        # 2. Three or more face mismatches (to allow for occasional camera angle changes affecting recognition)
        if face_mismatch_count >= 3:
            error_msg = "❌ EXAM BLOCKED! Your face does not match the registered photo. Exam access denied."
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'exam_blocked': True,
                    'violation_type': 'face_mismatch',
                    'message': error_msg,
                    'redirect': '/student_home'
                })
            return HttpResponse(
                f"<script>alert('{error_msg}');window.location='/student_home';</script>"
            )

        # Get questions
        from .models import question  # Import your question model

        print(request.session['suid'], "SH")
        try:
            questions = question.objects.filter(VACANCY=request.session['suid']).order_by('id')
            current_total = len(questions)

            print(f"\n📚 QUESTIONS FETCH:")
            print(f"   Vacancy ID: {request.session['suid']}")
            print(f"   Questions found: {current_total}")
            if current_total > 0:
                q_ids = [q.id for q in questions[:5]]
                print(f"   First 5 question IDs: {q_ids}")
            else:
                print(f"   ⚠️  NO QUESTIONS FOUND for this vacancy!")

            # Cache total on first fetch (when cache doesn't exist yet)
            if 'total_questions_cached' not in request.session:
                request.session['total_questions_cached'] = current_total
                print(f"   📌 Caching total questions: {current_total}")
            
            # Verify against cached total to detect mid-exam question deletions
            cached_total = request.session.get('total_questions_cached', 0)
            if cached_total > 0 and current_total != cached_total:
                print(f"   ⚠️  WARNING: Question count mismatch! Cached: {cached_total}, Current: {current_total}")
                # Use cached count for safety to prevent index issues
                total_to_use = cached_total
            else:
                total_to_use = current_total

            request.session['tq'] = total_to_use
            print(f"   Final total to use: {total_to_use}")
        except Exception as e:
            print(f"   ❌ ERROR fetching questions: {e}")
            error_msg = f"Database error fetching exam questions: {str(e)}"
            if is_ajax:
                return JsonResponse({'error': error_msg}, status=500)
            return HttpResponse(f"<script>alert('{error_msg}');window.location='/student_home';</script>")

        # Normalize session count to a zero-based integer index
        if 'count' not in request.session:
            request.session['count'] = 0
            print(f"🆕 Session 'count' was missing - initialized to 0")
        else:
            try:
                count_val = request.session['count']
                request.session['count'] = int(request.session['count'])
                if request.session['count'] < 0:
                    request.session['count'] = 0
                print(f"🔄 Session 'count' normalized: {count_val} → {request.session['count']}")
            except (ValueError, TypeError):
                request.session['count'] = 0
                print(f"⚠️  Session 'count' was invalid - reset to 0")

        current_count = int(request.session.get('count', 0))
        print(f"\n📋 EXAM STATE:")
        print(f"   Session count (zero-based): {current_count}")
        print(f"   Questions fetched: {len(questions)}")
        print(f"   Total questions cached: {request.session.get('total_questions_cached', 'NOT SET')}")
        print(f"   Candidate ID: {candidate_data.id}")
        print(f"   Vacancy ID: {request.session['suid']}")
        print(f"   Session ID: {request.session.session_key}")
        print(f"   Full session keys: {list(request.session.keys())}")

        # Check if we have questions
        if not questions.exists():
            error_msg = "❌ No questions found for this exam. Please contact the administrator."
            print(error_msg)
            if is_ajax:
                return JsonResponse({'error': error_msg, 'missing_questions': True}, status=404)
            return HttpResponse(f"<script>alert('{error_msg}');window.location='/view_applied_list';</script>")

        # Check if exam is completed - use session total questions for consistency
        total_questions_session = int(request.session.get('tq', len(questions)))
        if current_count >= total_questions_session:
            request.session['count'] = 0
            print(f"✅ Exam completed: count ({current_count}) >= total ({total_questions_session})")
            # Exam completed
            if is_ajax:
                return JsonResponse({
                    'completed': True,
                    'message': 'Exam completed successfully!',
                    'redirect': '/student_home'
                })
            return HttpResponse(
                "<script>alert('Exam completed!');window.location='/student_home'</script>"
            )

        # Get current question (0-indexed) with bounds check
        try:
            if 0 <= current_count < len(questions):
                current_question = questions[current_count]
            else:
                raise IndexError(f"Question index {current_count} is out of range for {len(questions)} questions")
        except (IndexError, Exception) as e:
            print(f"❌ ERROR getting current question: {e}")
            # No more questions - end exam
            request.session['count'] = 0
            if is_ajax:
                return JsonResponse({
                    'completed': True,
                    'message': 'Exam completed successfully!',
                    'redirect': '/student_home'
                })
            return HttpResponse(
                "<script>alert('Exam completed!');window.location='/student_home'</script>"
            )

        # Calculate remaining time
        remaining_seconds = 600  # Default 10 minutes

        try:
            exam_schedule = candidate_data
            exam_start_time = exam_schedule.exam_ftime
            exam_end_time = exam_schedule.exam_ttime

            if exam_start_time and exam_end_time:
                # Parse times (assuming format HH:MM)
                start_parts = str(exam_start_time).split(':')
                end_parts = str(exam_end_time).split(':')

                if len(start_parts) >= 2 and len(end_parts) >= 2:
                    start_hour = int(start_parts[0])
                    start_minute = int(start_parts[1])
                    end_hour = int(end_parts[0])
                    end_minute = int(end_parts[1])

                    # Get current time
                    now = datetime.datetime.now()
                    current_hour = now.hour
                    current_minute = now.minute

                    # Convert to minutes
                    start_total = start_hour * 60 + start_minute
                    end_total = end_hour * 60 + end_minute
                    current_total = current_hour * 60 + current_minute

                    # Calculate remaining minutes
                    if current_total >= start_total and current_total <= end_total:
                        remaining_minutes = end_total - current_total
                        remaining_seconds = remaining_minutes * 60
                    else:
                        remaining_seconds = 600  # Default if not within exam time
        except Exception as e:
            print(f"⚠️  WARNING: Schedule {request.session['suid']} not found for time calculation: {e}")
            exam_schedule = None
            remaining_seconds = 600
        except Exception as e:
            print(f"⚠️  WARNING: Error calculating exam time: {e}")
            exam_schedule = None
            remaining_seconds = 600

        # Get schedule for context (use the one we just fetched)
        try:
            sc = candidate_data
        except Exception as e:
            print(f"❌ ERROR: Cannot find schedule {request.session['suid']}: {e}")
            error_msg = "Exam schedule not found. Please contact administrator."
            if is_ajax:
                return JsonResponse({'error': error_msg}, status=404)
            return HttpResponse(f"<script>alert('{error_msg}');window.location='/student_home';</script>")

        # Prepare context - validate question data exists
        question_dict = {}
        print(f"\n🎯 QUESTION RENDERING CHECK:")
        print(f"   current_count={current_count}, len(questions)={len(questions)}")
        print(f"   Condition check: 0 <= {current_count} < {len(questions)} = {0 <= current_count < len(questions)}")
        
        if 0 <= current_count < len(questions):
            try:
                q = current_question
                print(f"   ✅ Got question at index {current_count}: ID={q.id}")

                # Validate that question has all required fields
                if not q.question or q.question.strip() == '':
                    print(f"   ⚠️  WARNING: Question {q.id} has empty text")
                if not q.option1 or q.option1.strip() == '':
                    print(f"   ⚠️  WARNING: Question {q.id} has empty option 1")
                if not q.option2 or q.option2.strip() == '':
                    print(f"   ⚠️  WARNING: Question {q.id} has empty option 2")
                if not q.option3 or q.option3.strip() == '':
                    print(f"   ⚠️  WARNING: Question {q.id} has empty option 3")
                if not q.option4 or q.option4.strip() == '':
                    print(f"   ⚠️  WARNING: Question {q.id} has empty option 4")
                if not q.answers or q.answers.strip() == '':
                    print(f"   ⚠️  WARNING: Question {q.id} has empty correct answer")

                question_dict = {
                    'id': q.id,
                    'questions': q.question or '[Question Text Missing]',
                    'option_1': q.option1 or '[Option A Missing]',
                    'option_2': q.option2 or '[Option B Missing]',
                    'option_3': q.option3 or '[Option C Missing]',
                    'option_4': q.option4 or '[Option D Missing]',
                    'correct_answer': q.answers or '',
                    'marks': '1',  # Default marks
                }
                print(f"   ✅ Question loaded successfully for display")
            except AttributeError as e:
                print(f"   ❌ ERROR: Question object missing attributes: {e}")
                error_msg = "Question data is incomplete. Please contact administrator."
                if is_ajax:
                    return JsonResponse({'error': error_msg}, status=500)
                return HttpResponse(f"<script>alert('{error_msg}');window.location='/student_home';</script>")
        else:
            print(f"   ❌ ERROR: Question index out of bounds - condition failed")
            question_dict = {}

        # Get recent violations for this candidate
        recent_violations = []
        try:
            from .models import ProctoringViolation
            recent_violations = ProctoringViolation.objects.filter(
                candidate=candidate_data
            ).order_by('-timestamp')[:5]
        except Exception as e:
            print(f"⚠️  Warning: Error fetching violations: {e}")

        ar = {
            'data': question_dict,
            # expose 1-based question number to templates (they expect c starting at 1)
            'c': current_count + 1,
            'remaining_seconds': remaining_seconds,
            'testid': id,
            'candidate_id': candidate_data.id,
            'candidate_name': f"{candidate_data.USER.name}",
            'no_of_unknown_person': no_unknown,
            'multiple_person': multiple_persons,
            'recent_violations': recent_violations,
            'total_violations': len(recent_violations),
            'exam_start_time': sc.exam_ftime,
            'exam_end_time': sc.exam_ttime,
            'is_ajax': is_ajax,
            'total_questions': len(questions),
            'schedule_id': request.session['suid'],  # Add for debugging
            'question_id': question_dict.get('id', 'MISSING') if question_dict else 'MISSING',  # Add for debugging
        }

        # If AJAX request, return only the question content
        print(f"DEBUG Context: {ar}")
        if is_ajax:
            return render(request, 'candidate/partial_question.html', ar)

        return render(request, 'candidate/attend_exam.html', ar)

    except Exception as e:
        print(f"Error in view_sample_question: {e}")
        if is_ajax:
            return JsonResponse({'error': str(e)}, status=500)
        return HttpResponse(f"Error: {str(e)}", status=500)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import base64
import os
from django.conf import settings
from .models import ProctoringViolation, candidate, user, exam
from django.contrib.auth.decorators import login_required, login_required, login_required, login_required


@login_required
def get_violation_stats(request):
    """Get violation statistics for dashboard"""
    try:
        user_obj = user.objects.get(LOGIN_id=request.session['lid'])
        if not user_obj:
            return JsonResponse({'status': 'error', 'message': 'User not found'})

        # Get candidate for current user
        cand_obj = candidate.objects.filter(USER=user_obj).first()
        if not cand_obj:
            return JsonResponse({'status': 'error', 'message': 'No exam found'})

        # Get violations for this candidate
        violations = ProctoringViolation.objects.filter(candidate=cand_obj)

        violation_summary = {
            'total_violations': violations.count(),
            'face_mismatch': violations.filter(violation_type='face_mismatch').count(),
            'multiple_faces': violations.filter(violation_type='multiple_faces').count(),
            'no_face': violations.filter(violation_type='no_face').count(),
            'head_movement': violations.filter(violation_type='head_movement').count(),
        }

        return JsonResponse({
            'status': 'success',
            'stats': violation_summary,
            'candidate_name': cand_obj.USER.name,
            'exam_status': cand_obj.status
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def get_proctoring_summary(request, candidate_id=None):
    """Get detailed proctoring summary for admin"""
    try:
        if candidate_id:
            cand_obj = candidate.objects.get(id=candidate_id)
        else:
            # Get from request if student
            user_obj = user.objects.get(LOGIN_id=request.session['lid'])
            if user_obj:
                cand_obj = candidate.objects.filter(USER=user_obj).first()
            else:
                return JsonResponse({'status': 'error', 'message': 'Candidate not found'})

        if not cand_obj:
            return JsonResponse({'status': 'error', 'message': 'Candidate not found'})

        # Get all violations for this candidate
        violations = ProctoringViolation.objects.filter(candidate=cand_obj).order_by('-timestamp')

        violation_list = []
        for violation in violations:
            violation_list.append({
                'id': violation.id,
                'type': violation.violation_type,
                'timestamp': violation.timestamp.isoformat(),
                'details': violation.details,
                'screenshot': violation.screenshot.url if violation.screenshot else None
            })

        # Calculate statistics
        total_violations = len(violation_list)

        # Group by type
        violations_by_type = {}
        for violation in violation_list:
            violation_type = violation['type']
            violations_by_type[violation_type] = violations_by_type.get(violation_type, 0) + 1

        return JsonResponse({
            'status': 'success',
            'candidate': {
                'id': cand_obj.id,
                'name': cand_obj.USER.name,
                'exam': cand_obj.EXAM.id if cand_obj.EXAM else None,
                'status': cand_obj.status
            },
            'violations': violation_list,
            'statistics': {
                'total': total_violations,
                'by_type': violations_by_type
            }
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def forgotpassword(request):
    return render(request, "forgotpassword.html")


def forgotpasswordbuttonclick(request):
    email = request.POST['textfield']
    if login.objects.filter(username=email).exists():
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # ✅ Gmail credentials (use App Password, not real password)
            sender_email = projectemail
            receiver_email = email  # change to actual recipient
            app_password = projectpassword  # App Password from Google
            pwd = str(random.randint(1100, 9999))
            print(pwd)  # Example password to send
            request.session['otp'] = pwd
            request.session['email'] = email

            # Setup SMTP
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, app_password)

            # Create the email
            msg = MIMEMultipart("alternative")
            msg["From"] = sender_email
            msg["To"] = receiver_email
            msg["Subject"] = "Your OTP"

            # Plain text (backup)
            # text = f"""
            # Hello,

            # Your password for Smart Donation Website is: {pwd}

            # Please keep it safe and do not share it with anyone.
            # """

            # HTML (attractive)
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color:#2c7be5;">Interview Stimulator</h2>
                <p>Hello,</p>
                <p>Your OTP is:</p>
                <p style="padding:10px; background:#f4f4f4; 
                        border:1px solid #ddd; 
                        display:inline-block;
                        font-size:18px;
                        font-weight:bold;
                        color:#2c7be5;">
                {pwd}
                </p>
                <p>Please keep it safe and do not share it with anyone.</p>
                <hr>
                <small style="color:gray;">This is an automated email from Interview Stimulator System.</small>
            </body>
            </html>
            """

            # Attach both versions
            # msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            # Send email
            server.send_message(msg)
            print("✅ Email sent successfully!")

            # Close connection
            server.quit()
        except Exception as e:
            print("❌ Error sending email:", e)
        return HttpResponse("<script>window.location='/otp'</script>")
    else:
        return HttpResponse("<script>alert('Email not found');window.location='/forgotpassword'</script>")


def otp(request):
    print("session otp", request.session['otp'])

    return render(request, "otp.html")


def otpbuttonclick(request):
    otp = request.POST["textfield"]
    if otp == str(request.session['otp']):
        return HttpResponse("<script>window.location='/forgotpswdpswed'</script>")
    else:
        return HttpResponse("<script>alert('incorrect otp');window.location='/otp'</script>")


def forgotpswdpswed(request):
    return render(request, "forgotpswdpswed.html")


def forgotpswdpswedbuttonclick(request):
    np = request.POST["password"]
    login.objects.filter(username=request.session['email']).update(password=np)
    return HttpResponse("<script>alert('password has been changed');window.location='/' </script>")


def send_complaint2(request):
    if "lid" not in request.session:
        return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
    request.session['head'] = "SEND COMPLAINT"
    return render(request, "company/sendsuggestion.html")


def send_complaint_post2(request):
    import datetime
    complaint = request.POST['textarea']
    obj = suggestions()
    obj.suggestion = complaint
    obj.date = datetime.datetime.now().date()
    obj.type = "company"
    obj.LOGIN_id = request.session['lid']
    obj.save()
    return HttpResponse("<script>alert('Success');window.location='/send_complaint2#abc'</script>")


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db import IntegrityError
import uuid
from .models import InterviewSession, QuestionAnswer, SessionAnalytics, EmotionSession, InterviewQA
from .serializers import InterviewSessionSerializer, QuestionAnswerSerializer, SessionAnalyticsSerializer
from .gemini_service import GeminiQuestionService
import logging

logger = logging.getLogger(__name__)


def mockinterview(request,id):
    return render(request, "mockinterview.html",{'vobj':candidate.objects.get(id=id)})


@csrf_exempt
def deepface_health(request):
    """Check if DeepFace is installed and ready"""
    try:
        from deepface import DeepFace
        return JsonResponse({'success': True, 'message': 'DeepFace is installed and ready'})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'DeepFace not available: {str(e)}',
            'hint': 'Install with: pip install deepface'
        }, status=503)


@csrf_exempt
def face_analyze(request):
    """Receive an image file (multipart form `image`) and run DeepFace analysis.
    Returns JSON with DeepFace analysis or an error message.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    image_file = request.FILES.get('image') if request.FILES else None
    if image_file is None:
        return JsonResponse({'success': False, 'error': 'No image provided'}, status=400)

    # Extract session_id from POST/GET data, or generate one if not provided
    session_id = request.POST.get('session_id') or request.GET.get('session_id')
    if not session_id:
        # Generate a default session_id from timestamp if none provided
        import uuid
        session_id = str(uuid.uuid4())

    try:
        captures_dir = os.path.join(settings.MEDIA_ROOT or '.', 'captures')
        os.makedirs(captures_dir, exist_ok=True)
        fs = FileSystemStorage(location=captures_dir)
        # Use a filesystem-safe timestamp for the filename
        safe_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = fs.save(f'capture_{safe_ts}.png', image_file)
        file_path = fs.path(filename)

        from deepface import DeepFace
        # analyze for common attributes
        analysis = DeepFace.analyze(img_path=file_path, actions=['emotion'], enforce_detection=False)
        print(f"DeepFace analysis result: {analysis}")
        logger.info(f"DeepFace analysis completed")

        # Extract emotion data from analysis
        if analysis and len(analysis) > 0:
            result = analysis[0]
            emotion = str(result.get('dominant_emotion', 'neutral'))
            emotions_raw = result.get('emotion', {})

            # Extract confidence for dominant emotion
            emotion_confidence = float(emotions_raw.get(emotion, 0.0)) if emotion in emotions_raw else 0.0
            print(f"✅ Emotion Analysis: dominant={emotion}, confidence={emotion_confidence}, session_id={session_id}")
            logger.info(f"✅ Emotion Analysis: dominant={emotion}, confidence={emotion_confidence}")

            # Map emotion to emoji
            emotion_emoji_map = {
                'happy': '😊',
                'sad': '😢',
                'angry': '😠',
                'fear': '😨',
                'surprise': '😲',
                'neutral': '😐',
                'disgust': '🤢'
            }
            emotion_emoji = emotion_emoji_map.get(emotion.lower(), '😐')

            # Determine if face was detected (not neutral + sufficient confidence)
            face_detected = emotion != 'neutral' and emotion_confidence > 30
            print(f"Face detection: emotion='{emotion}', conf={emotion_confidence:.1f}, detected={face_detected}")
            if face_detected == False:
                return JsonResponse({
                    'success': True,
                    'dominant_emotion': 'No face detected in image',
                    'emotion_emoji': '😐',
                    'emotions': {},
                    'message': 'No face detected in image'
                }, encoder=NumpyEncoder)

            # Always save or update EmotionSession with emotion and confidence
            EmotionSession.objects.update_or_create(
                session_id=session_id,
                defaults={
                    'dominant_emotion': emotion,
                    'emotion_confidence': emotion_confidence
                }
            )

            # Convert emotions to native Python types for JSON serialization
            emotions = {}
            for emotion_name, emotion_score in emotions_raw.items():
                try:
                    emotions[str(emotion_name)] = float(emotion_score)
                except (TypeError, ValueError):
                    emotions[str(emotion_name)] = 0.0

            # Create response with only JSON-serializable data
            response_data = {
                'success': True,
                'dominant_emotion': emotion,
                'emotion_confidence': emotion_confidence,
                'emotion_emoji': emotion_emoji,
                'face_detected': face_detected,
                'emotions': emotions
            }

            return JsonResponse(response_data, encoder=NumpyEncoder)
        else:
            return JsonResponse({
                'success': True,
                'dominant_emotion': 'No face detected in image',
                'emotion_emoji': '😐',
                'emotions': {},
                'message': 'No face detected in image'
            }, encoder=NumpyEncoder)
    except Exception as e:
        logger.exception("Error in face_analyze")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



class StartSessionView(APIView):
    def post(self, request):
        try:
            # Parse incoming payload (role/level/persona optional)
            data = request.data if hasattr(request, 'data') else json.loads(request.body or '{}')
            role = (data.get('role') or 'unknown')
            level = (data.get('level') or 'mid')
            persona = (data.get('persona') or 'general')
            # Robust parsing of requested question count
            try:
                count = int(data.get('count', 5))
            except Exception:
                count = 5
            count = max(1, min(count, 10))  # constrain to 1..10

            # Generate a unique session id
            session_id = str(uuid.uuid4())
            print()
            logger.debug("Starting session request: id=%s role=%s level=%s persona=%s count=%s", session_id, role,
                         level, persona, count)

            # Use get_or_create to avoid race conditions and handle DB constraints more gracefully
            session, created = InterviewSession.objects.get_or_create(
                session_id=session_id,
                defaults={
                    'started_at': timezone.now(),
                    'role': role,
                    'level': level,
                    'persona': persona,
                    'question_count': count
                }
            )

            return Response({
                'status': 'success',
                'session_id': session.session_id,
                'started_at': session.started_at,
                'role': session.role,
                'level': session.level,
                'persona': session.persona,
                'question_count': session.question_count,
                'message': 'Interview session started successfully'
            }, status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK))

        except IntegrityError as ie:
            # Database-level unique constraint exists (likely from old migrations)
            logger.exception("IntegrityError starting session: possible unique constraint on role/level/persona")
            return Response({
                'status': 'error',
                'message': 'Database constraint error when creating session',
                'detail': str(ie),
                'hint': 'There appears to be a unique index on one of the session fields (role/level/persona). Run the provided migration to remove unique indexes and then run `python manage.py migrate`.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.exception("Error starting session")
            return Response({
                'status': 'error',
                'message': 'Failed to start session',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateQuestionsView(APIView):
    def post(self, request):
        try:
            role = request.data.get('role', 'developer')
            level = request.data.get('level', 'mid')
            session_id = request.data.get('session_id')

            # Prefer explicit count from request; otherwise try using stored session count; fall back to 5
            raw_count = request.data.get('count', None)
            if raw_count in (None, ''):
                count = 5
                if session_id:
                    try:
                        session_obj = InterviewSession.objects.get(session_id=session_id)
                        count = getattr(session_obj, 'question_count', 5)
                    except InterviewSession.DoesNotExist:
                        count = 5
            else:
                try:
                    count = int(raw_count)
                except Exception:
                    count = 5
            count = max(1, min(count, 10))

            # If a session id was provided, persist the last used count for future calls
            if session_id:
                try:
                    sess = InterviewSession.objects.get(session_id=session_id)
                    if sess.question_count != count:
                        sess.question_count = count
                        sess.save(update_fields=['question_count'])
                except InterviewSession.DoesNotExist:
                    pass

            # Generate questions using Gemini
            gemini_service = GeminiQuestionService()
            questions = gemini_service.generate_questions(role, level, count)

            return Response({
                'status': 'success',
                'questions': questions,
                'count': len(questions)
            })

        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to generate questions'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmitQAView(APIView):
    def post(self, request):
        try:
            data = request.data if hasattr(request, 'data') else json.loads(request.body or '{}')
            logger.debug('SubmitQAView received data: %s', data)

            session_id = data.get('session_id')
            question = data.get('question')
            answer = data.get('answer')

            # Validate fields and return helpful message
            missing = []
            if not question:
                missing.append('question')
            if not answer:
                missing.append('answer')

            if missing:
                return Response({
                    'status': 'error',
                    'message': 'Missing required fields',
                    'missing_fields': missing
                }, status=status.HTTP_400_BAD_REQUEST)

            # If session is missing or a local session id, skip DB save and only evaluate locally
            is_local_session = not session_id or (isinstance(session_id, str) and session_id.startswith('local_'))

            session = None
            if not is_local_session:
                try:
                    session = InterviewSession.objects.get(session_id=session_id)
                except InterviewSession.DoesNotExist:
                    return Response({
                        'status': 'error',
                        'message': 'Session not found'
                    }, status=status.HTTP_404_NOT_FOUND)

            # Evaluate answer using Gemini (or fallback)
            gemini_service = GeminiQuestionService()
            evaluation = gemini_service.evaluate_answer(question, answer)

            # Save QA only if we have a real session
            qa_id = None
            if session:
                qa = QuestionAnswer.objects.create(
                    session=session,
                    question=question,
                    answer=answer,
                    question_type=data.get('question_type', 'general'),
                    category=data.get('category', 'General'),
                    confidence_score=evaluation.get('confidence'),
                    clarity_score=evaluation.get('clarity'),
                    ai_feedback=evaluation.get('feedback')
                )
                qa_id = qa.id

                # Optional audio/phoneme/viseme metadata (frontend may include these)
                asr_confidence = data.get('asr_confidence', None)
                phoneme_durations = data.get('phoneme_durations', None)
                viseme_sequence = data.get('viseme_sequence', None)
                confidence_history = data.get('confidence_history', None)
                audio_levels = data.get('audio_levels', None)
                speaking_duration = data.get('speaking_duration', None)

                # Optional audio metrics from enhanced_data or audio_metrics
                audio_metrics = data.get('audio_metrics', {})
                if audio_metrics:
                    if not confidence_history:
                        confidence_history = audio_metrics.get('confidenceHistory')
                    if not audio_levels:
                        audio_levels = audio_metrics.get('audioLevels')
                    if not speaking_duration:
                        speaking_duration = audio_metrics.get('speakingDuration')

                # Optional emotion data from face analysis
                emotion_data = data.get('emotion_data', None)
                dominant_emotion = data.get('dominant_emotion', None)

                # Compute grammar suggestions and grammar score
                try:
                    from .audio_analysis import (
                        grammar_suggestions_and_score,
                        compute_shiver_penalty,
                        lip_movement_score,
                        compute_normalized_confidence,
                        compute_asr_confidence_from_history,
                        compute_pause_penalty,
                        compute_hesitation_penalty,
                        compute_stuck_penalty,
                        compute_emotion_confidence,
                        compute_combined_emotion_confidence
                    )

                    suggestions, gscore = grammar_suggestions_and_score(answer)

                    # If asr_confidence not provided, estimate it from history/audio
                    if asr_confidence in (None, '', 0):
                        try:
                            est = compute_asr_confidence_from_history(confidence_history=confidence_history,
                                                                      audio_levels=audio_levels)
                            if est is not None:
                                asr_confidence = est
                        except Exception:
                            pass

                    shiver = compute_shiver_penalty(phoneme_durations=phoneme_durations,
                                                    confidence_history=confidence_history)
                    lip_score = lip_movement_score(viseme_sequence)

                    # Compute COMBINED emotion confidence from both face AND audio
                    emotion_result = compute_combined_emotion_confidence(
                        face_emotion_data=emotion_data,
                        face_dominant_emotion=dominant_emotion,
                        phoneme_durations=phoneme_durations,
                        confidence_history=confidence_history,
                        audio_levels=audio_levels,
                        speaking_duration=data.get('speaking_duration')
                    )

                    emotion_conf = emotion_result['combined_emotion_confidence']
                    audio_emotion_conf = emotion_result['audio_emotion_confidence']

                    # Save derived fields
                    qa.grammar_suggestions = json.dumps(suggestions)
                    qa.grammar_score = gscore
                    qa.shiver_penalty = shiver
                    qa.lip_movement_score = lip_score
                    qa.emotion_data = json.dumps(emotion_data) if emotion_data else None
                    qa.dominant_emotion = dominant_emotion
                    qa.emotion_confidence = emotion_result['face_emotion_confidence']
                    qa.audio_emotion_confidence = audio_emotion_conf
                    qa.combined_emotion_confidence = emotion_conf

                    # Extract frontend-enhanced audio metrics if provided
                    enhanced = data.get('enhanced_data') or {}
                    audio_analysis = enhanced.get('audioAnalysis') if isinstance(enhanced, dict) else None

                    pause_penalty = 0.0
                    hesitation_penalty = 0.0
                    stuck_penalty = 0.0

                    try:
                        if audio_analysis:
                            pause_hist = audio_analysis.get('pauseHistory')
                            filler_count = audio_analysis.get('fillerWordCount', 0) or 0
                            wpm = audio_analysis.get('wordsPerMinute')

                            pause_penalty = compute_pause_penalty(pause_hist)
                            hesitation_penalty = compute_hesitation_penalty(filler_word_count=filler_count,
                                                                            words_per_minute=wpm)

                        # compute repeated pairs from answer text as a fallback for stuck detection
                        words = [w.strip(',.!?;:').lower() for w in (answer or '').split()]
                        repeated_pairs = sum(1 for i in range(len(words) - 1) if words[i] == words[i + 1])
                        restart_attempts = (
                                           enhanced.get('restartAttempts') if isinstance(enhanced, dict) else None) or 0
                        stuck_penalty = compute_stuck_penalty(restart_attempts=restart_attempts,
                                                              repeated_words=repeated_pairs)
                    except Exception:
                        logger.exception('Error computing additional audio penalties')

                    # Compute a normalized confidence (0..1) including all penalties and emotion
                    normalized = compute_normalized_confidence(asr_confidence=asr_confidence,
                                                               model_confidence=evaluation.get('confidence'),
                                                               clarity_score=evaluation.get('clarity'),
                                                               grammar_score=gscore,
                                                               shiver_penalty=shiver,
                                                               lip_score=lip_score,
                                                               pause_penalty=pause_penalty,
                                                               hesitation_penalty=hesitation_penalty,
                                                               stuck_penalty=stuck_penalty,
                                                               emotion_data=emotion_data,
                                                               dominant_emotion=dominant_emotion)

                    # Attach a brief audio analysis summary to ai_feedback for visibility
                    try:
                        details = {'pause_penalty': pause_penalty, 'hesitation_penalty': hesitation_penalty,
                                   'stuck_penalty': stuck_penalty, 'shiver_penalty': shiver}
                        if qa.ai_feedback:
                            try:
                                fb = json.loads(qa.ai_feedback)
                                fb['_audio_analysis'] = details
                                qa.ai_feedback = json.dumps(fb)
                            except Exception:
                                qa.ai_feedback = json.dumps({'feedback': qa.ai_feedback, '_audio_analysis': details})
                        else:
                            qa.ai_feedback = json.dumps({'_audio_analysis': details})
                    except Exception:
                        logger.exception('Could not attach audio analysis details to ai_feedback')

                    qa.normalized_confidence = normalized
                    qa.save(
                        update_fields=['grammar_suggestions', 'grammar_score', 'shiver_penalty', 'lip_movement_score',
                                       'normalized_confidence', 'ai_feedback', 'emotion_data', 'dominant_emotion',
                                       'emotion_confidence', 'audio_emotion_confidence', 'combined_emotion_confidence'])
                except Exception as e:
                    logger.exception('Error during post-evaluation audio/grammar analysis: %s', e)

                # Save/update EmotionSession with aggregated emotion data
                try:
                    if session_id:
                        # Get or create emotion session
                        emotion_session, created = EmotionSession.objects.get_or_create(
                            session_id=session_id
                        )

                        # Aggregate emotions from all QAs in this session
                        all_qas = QuestionAnswer.objects.filter(session=session)
                        logger.info(f"Aggregating emotions for {len(all_qas)} QAs in session {session_id}")

                        # Prepare aggregation structures
                        emotions_list = []
                        emotions_dict = {}
                        dominant_emotion_counts = {}

                        for qa in all_qas:
                            logger.debug(
                                f"QA {qa.id}: emotion_data={qa.emotion_data}, dominant={qa.dominant_emotion}, conf={qa.combined_emotion_confidence}")
                            if qa.emotion_data:
                                try:
                                    qa_emotions = json.loads(qa.emotion_data)
                                    emotions_list.append(qa_emotions)
                                except Exception:
                                    pass

                            # Always track dominant emotion, regardless of whether raw emotion_data exists
                            if qa.dominant_emotion:
                                if qa.dominant_emotion not in dominant_emotion_counts:
                                    dominant_emotion_counts[qa.dominant_emotion] = {'count': 0, 'confidences': []}
                                dominant_emotion_counts[qa.dominant_emotion]['count'] += 1
                                conf = qa.combined_emotion_confidence or qa.emotion_confidence or 0.5
                                dominant_emotion_counts[qa.dominant_emotion]['confidences'].append(conf)
                                if qa.dominant_emotion not in emotions_dict:
                                    emotions_dict[qa.dominant_emotion] = []
                                emotions_dict[qa.dominant_emotion].append(conf)

                        logger.info(
                            f"emotions_dict: {emotions_dict}, dominant_emotion_counts: {dominant_emotion_counts}")

                        # Determine dominant emotion: prefer counts + avg confidence
                        dominant = None
                        if dominant_emotion_counts:
                            sorted_emotions = sorted(
                                dominant_emotion_counts.items(),
                                key=lambda x: (
                                    x[1]['count'],
                                    (sum(x[1]['confidences']) / len(x[1]['confidences'])) if x[1][
                                        'confidences'] else 0.5
                                ),
                                reverse=True
                            )
                            dominant = sorted_emotions[0][0]
                            dominant_confs = dominant_emotion_counts[dominant]['confidences']
                            emotion_session.combined_emotion_confidence = sum(dominant_confs) / len(
                                dominant_confs) if dominant_confs else 0.5
                            emotion_session.dominant_emotion = dominant
                            logger.info(
                                f"Set dominant emotion: {dominant}, confidence: {emotion_session.combined_emotion_confidence}")
                        elif emotions_dict:
                            avg_emotions = {k: sum(v) / len(v) for k, v in emotions_dict.items()}
                            dominant = max(avg_emotions, key=avg_emotions.get)
                            emotion_session.dominant_emotion = dominant
                            emotion_session.combined_emotion_confidence = avg_emotions.get(dominant, 0.0)
                            logger.info(
                                f"Fallback - Set dominant emotion: {dominant}, confidence: {emotion_session.combined_emotion_confidence}")

                        # Aggregate all emotion confidence scores
                        face_emotions = [qa.emotion_confidence for qa in all_qas if qa.emotion_confidence is not None]
                        audio_emotions = [qa.audio_emotion_confidence for qa in all_qas if
                                          qa.audio_emotion_confidence is not None]
                        combined_emotions = [qa.combined_emotion_confidence for qa in all_qas if
                                             qa.combined_emotion_confidence is not None]

                        if face_emotions:
                            emotion_session.avg_face_emotion_confidence = sum(face_emotions) / len(face_emotions)
                        if audio_emotions:
                            emotion_session.avg_audio_emotion_confidence = sum(audio_emotions) / len(audio_emotions)
                        if combined_emotions:
                            emotion_session.avg_emotion_confidence = sum(combined_emotions) / len(combined_emotions)

                        # Store emotion timeline
                        emotion_timeline = []
                        for qa in all_qas:
                            if qa.dominant_emotion:
                                emotion_timeline.append({
                                    'question_id': qa.id,
                                    'dominant_emotion': qa.dominant_emotion,
                                    'confidence': float(
                                        qa.combined_emotion_confidence) if qa.combined_emotion_confidence else 0.0,
                                    'timestamp': qa.timestamp.isoformat() if qa.timestamp else None
                                })

                        emotion_session.emotion_timeline = json.dumps(emotion_timeline)
                        emotion_session.emotion_data = json.dumps(emotions_dict)

                        # Calculate emotion variance and stability
                        if combined_emotions and len(combined_emotions) > 1:
                            avg = sum(combined_emotions) / len(combined_emotions)
                            variance = sum((x - avg) ** 2 for x in combined_emotions) / len(combined_emotions)
                            emotion_session.emotion_variance = variance
                            stability = 1.0 - min(variance, 1.0)  # Higher stability = less variance
                            emotion_session.emotion_stability = stability

                        emotion_session.save()
                        logger.info(
                            f"✓ Updated EmotionSession for session_id: {session_id} with {len(all_qas)} QAs. Created={created}")
                except Exception as e:
                    logger.exception(f"✗ Error saving EmotionSession for {session_id}: {e}")

            return Response({
                'status': 'success',
                'evaluation': evaluation,
                'qa_id': qa_id,
                'normalized_confidence': qa.normalized_confidence if qa_id else None,
                'grammar_score': qa.grammar_score if qa_id else None
            })

        except Exception as e:
            logger.error(f"Error submitting QA: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to submit QA'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SessionAnalyticsView(APIView):
    def get(self, request, session_id):
        try:
            session = InterviewSession.objects.get(session_id=session_id)
            qas = session.qas.all()

            if qas.count() == 0:
                return Response({
                    'status': 'success',
                    'qa_count': 0,
                    'avg_confidence': 0,
                    'avg_clarity': 0,
                    'avg_emotion_confidence': 0,
                    'avg_normalized_confidence': 0
                })

            # Calculate analytics including emotion
            total_confidence = sum(qa.confidence_score or 0 for qa in qas)
            total_clarity = sum(qa.clarity_score or 0 for qa in qas)
            total_emotion_confidence = sum(qa.emotion_confidence or 0 for qa in qas)
            total_normalized_confidence = sum(qa.normalized_confidence or 0 for qa in qas)

            analytics_data = {
                'qa_count': qas.count(),
                'avg_confidence': round(total_confidence / qas.count(), 2),
                'avg_clarity': round(total_clarity / qas.count(), 2),
                'avg_emotion_confidence': round(total_emotion_confidence / qas.count(), 2),
                'avg_normalized_confidence': round(total_normalized_confidence / qas.count(), 2),
                'questions': QuestionAnswerSerializer(qas, many=True).data
            }

            # Create or update analytics record
            analytics, created = SessionAnalytics.objects.update_or_create(
                session=session,
                defaults={
                    'total_questions': qas.count(),
                    'avg_confidence': analytics_data['avg_confidence'],
                    'avg_clarity': analytics_data['avg_clarity'],
                    'total_duration': session.duration or 0
                }
            )

            return Response({
                'status': 'success',
                **analytics_data
            })

        except InterviewSession.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to get analytics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EndSessionView(APIView):
    def post(self, request, session_id):
        try:
            session = InterviewSession.objects.get(session_id=session_id)
            session.end_time = timezone.now()
            session.save()

            return Response({
                'status': 'success',
                'message': 'Session ended successfully',
                'duration': session.duration
            })

        except InterviewSession.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to end session'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ActiveRolesView(APIView):
    """Return a preview of active roles and their sessions.
    GET /api/sessions/active_roles/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            active = InterviewSession.objects.filter(ended_at__isnull=True)
            role_map = {}
            for s in active:
                r = (s.role or 'unknown')
                if r not in role_map:
                    role_map[r] = {'role': r, 'count': 0, 'sessions': []}
                role_map[r]['count'] += 1
                role_map[r]['sessions'].append({'session_id': s.session_id, 'started_at': s.started_at.isoformat(),
                                                'question_count': s.question_count, 'level': s.level,
                                                'persona': s.persona})

            roles = list(role_map.values())
            return Response({'status': 'success', 'roles': roles})
        except Exception as e:
            logger.exception('Error fetching active roles: %s', e)
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StopAllSessionsView(APIView):
    """Stop (end) all active sessions and return the summary of affected roles.
    POST /api/sessions/stop_all/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            now = timezone.now()
            active = list(InterviewSession.objects.filter(ended_at__isnull=True))
            if not active:
                return Response({'status': 'success', 'roles': []})

            # Mark ended_at for each active session
            for s in active:
                s.ended_at = now
            InterviewSession.objects.bulk_update(active, ['ended_at'])

            # Build role summary
            role_map = {}
            for s in active:
                r = (s.role or 'unknown')
                if r not in role_map:
                    role_map[r] = {'role': r, 'count': 0}
                role_map[r]['count'] += 1

            roles = list(role_map.values())
            return Response({'status': 'success', 'roles': roles})
        except Exception as e:
            logger.exception('Error stopping all sessions: %s', e)
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HealthCheckView(APIView):
    def get(self, request):
        return Response({
            'status': 'healthy',
            'service': 'Interview Simulator API',
            'version': '1.0.0'
        })


class SaveEmotionSessionView(APIView):
    """Save emotion data for a session
    POST /api/emotions/save/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data if hasattr(request, 'data') else json.loads(request.body or '{}')
            session_id = data.get('session_id')

            if not session_id:
                return Response({
                    'status': 'error',
                    'message': 'session_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get or create emotion session
            emotion_session, created = EmotionSession.objects.get_or_create(
                session_id=session_id
            )

            # Update emotion data
            emotion_session.dominant_emotion = data.get('dominant_emotion')
            emotion_session.avg_emotion_confidence = data.get('avg_emotion_confidence')
            emotion_session.avg_face_emotion_confidence = data.get('avg_face_emotion_confidence')
            emotion_session.avg_audio_emotion_confidence = data.get('avg_audio_emotion_confidence')
            emotion_session.combined_emotion_confidence = data.get('combined_emotion_confidence')
            emotion_session.emotion_data = json.dumps(data.get('emotion_data', {}))
            emotion_session.emotion_timeline = json.dumps(data.get('emotion_timeline', []))
            emotion_session.emotion_variance = data.get('emotion_variance')
            emotion_session.emotion_stability = data.get('emotion_stability')
            emotion_session.save()

            return Response({
                'status': 'success',
                'message': 'Emotion session saved successfully',
                'session_id': session_id,
                'created': created
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Exception as e:
            logger.exception('Error saving emotion session')
            return Response({
                'status': 'error',
                'message': 'Failed to save emotion session',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetEmotionSessionView(APIView):
    """Retrieve emotion data for a session
    GET /api/emotions/session/<session_id>/
    """
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            emotion_session = EmotionSession.objects.get(session_id=session_id)

            # Parse JSON fields
            emotion_data = {}
            emotion_timeline = []
            try:
                if emotion_session.emotion_data:
                    emotion_data = json.loads(emotion_session.emotion_data)
            except Exception:
                pass

            try:
                if emotion_session.emotion_timeline:
                    emotion_timeline = json.loads(emotion_session.emotion_timeline)
            except Exception:
                pass

            return Response({
                'status': 'success',
                'emotion_session': {
                    'session_id': emotion_session.session_id,
                    'dominant_emotion': emotion_session.dominant_emotion,
                    'avg_emotion_confidence': emotion_session.avg_emotion_confidence,
                    'avg_face_emotion_confidence': emotion_session.avg_face_emotion_confidence,
                    'avg_audio_emotion_confidence': emotion_session.avg_audio_emotion_confidence,
                    'combined_emotion_confidence': emotion_session.combined_emotion_confidence,
                    'emotion_data': emotion_data,
                    'emotion_timeline': emotion_timeline,
                    'emotion_variance': emotion_session.emotion_variance,
                    'emotion_stability': emotion_session.emotion_stability,
                    'created_at': emotion_session.created_at,
                    'updated_at': emotion_session.updated_at
                }
            }, status=status.HTTP_200_OK)

        except EmotionSession.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Emotion session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception('Error retrieving emotion session')
            return Response({
                'status': 'error',
                'message': 'Failed to retrieve emotion session',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAllEmotionsView(APIView):
    """Get all emotion sessions
    GET /api/emotions/all/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            emotion_sessions = EmotionSession.objects.all()

            sessions_list = []
            for emotion_session in emotion_sessions:
                sessions_list.append({
                    'session_id': emotion_session.session_id,
                    'dominant_emotion': emotion_session.dominant_emotion,
                    'avg_emotion_confidence': emotion_session.avg_emotion_confidence,
                    'combined_emotion_confidence': emotion_session.combined_emotion_confidence,
                    'created_at': emotion_session.created_at
                })

            return Response({
                'status': 'success',
                'count': len(sessions_list),
                'emotion_sessions': sessions_list
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception('Error retrieving emotion sessions')
            return Response({
                'status': 'error',
                'message': 'Failed to retrieve emotion sessions',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteEmotionSessionView(APIView):
    """Delete emotion session
    DELETE /api/emotions/session/<session_id>/
    """
    permission_classes = [AllowAny]

    def delete(self, request, session_id):
        try:
            emotion_session = EmotionSession.objects.get(session_id=session_id)
            emotion_session.delete()

            return Response({
                'status': 'success',
                'message': 'Emotion session deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)

        except EmotionSession.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Emotion session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception('Error deleting emotion session')
            return Response({
                'status': 'error',
                'message': 'Failed to delete emotion session',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TriggerEmotionAggregationView(APIView):
    """Manually trigger emotion aggregation for a session
    POST /api/emotions/aggregate/<session_id>/
    """
    permission_classes = [AllowAny]

    def post(self, request, session_id):
        try:
            session = InterviewSession.objects.get(session_id=session_id)

            # Get or create emotion session
            emotion_session, created = EmotionSession.objects.get_or_create(
                session_id=session_id
            )

            # Aggregate emotions from all QAs in this session
            all_qas = QuestionAnswer.objects.filter(session=session)
            logger.info(f"MANUAL AGGREGATION: {len(all_qas)} QAs for session {session_id}")

            # Calculate average emotions
            emotions_dict = {}
            dominant_emotion_counts = {}

            for qa in all_qas:
                logger.info(
                    f"  QA {qa.id}: emotion={qa.dominant_emotion}, conf={qa.combined_emotion_confidence}, data_len={len(qa.emotion_data) if qa.emotion_data else 0}")
                # collect raw emotion data if present
                if qa.emotion_data:
                    try:
                        _ = json.loads(qa.emotion_data)
                    except Exception:
                        pass

                # track dominant emotions and confidences
                if qa.dominant_emotion:
                    if qa.dominant_emotion not in dominant_emotion_counts:
                        dominant_emotion_counts[qa.dominant_emotion] = {'count': 0, 'confidences': []}
                    dominant_emotion_counts[qa.dominant_emotion]['count'] += 1
                    conf = qa.combined_emotion_confidence or qa.emotion_confidence or 0.5
                    dominant_emotion_counts[qa.dominant_emotion]['confidences'].append(conf)
                    emotions_dict.setdefault(qa.dominant_emotion, []).append(conf)

            logger.info(f"emotions_dict: {emotions_dict}, dominant_emotion_counts: {dominant_emotion_counts}")

            # Calculate dominant emotion (most frequent + highest avg confidence)
            dominant = None
            if dominant_emotion_counts:
                sorted_emotions = sorted(
                    dominant_emotion_counts.items(),
                    key=lambda x: (
                        x[1]['count'],
                        (sum(x[1]['confidences']) / len(x[1]['confidences'])) if x[1]['confidences'] else 0.5
                    ),
                    reverse=True
                )
                dominant = sorted_emotions[0][0]
                dominant_confs = dominant_emotion_counts[dominant]['confidences']
                emotion_session.combined_emotion_confidence = sum(dominant_confs) / len(
                    dominant_confs) if dominant_confs else 0.5
                emotion_session.dominant_emotion = dominant
                logger.info(f"Set dominant: {dominant}, conf={emotion_session.combined_emotion_confidence}")
            elif emotions_dict:
                avg_emotions = {k: sum(v) / len(v) for k, v in emotions_dict.items()}
                dominant = max(avg_emotions, key=avg_emotions.get)
                emotion_session.dominant_emotion = dominant
                emotion_session.combined_emotion_confidence = avg_emotions.get(dominant, 0.0)
                logger.info(f"Fallback - Set dominant: {dominant}, conf={emotion_session.combined_emotion_confidence}")
            # Aggregate all emotion confidence scores
            face_emotions = [qa.emotion_confidence for qa in all_qas if qa.emotion_confidence]
            audio_emotions = [qa.audio_emotion_confidence for qa in all_qas if qa.audio_emotion_confidence]
            combined_emotions = [qa.combined_emotion_confidence for qa in all_qas if qa.combined_emotion_confidence]

            if face_emotions:
                emotion_session.avg_face_emotion_confidence = sum(face_emotions) / len(face_emotions)
            if audio_emotions:
                emotion_session.avg_audio_emotion_confidence = sum(audio_emotions) / len(audio_emotions)
            if combined_emotions:
                emotion_session.avg_emotion_confidence = sum(combined_emotions) / len(combined_emotions)

            # Store emotion timeline
            emotion_timeline = []
            for qa in all_qas:
                if qa.dominant_emotion:
                    emotion_timeline.append({
                        'question_id': qa.id,
                        'dominant_emotion': qa.dominant_emotion,
                        'confidence': float(qa.combined_emotion_confidence) if qa.combined_emotion_confidence else 0.0,
                        'timestamp': qa.timestamp.isoformat() if qa.timestamp else None
                    })

            emotion_session.emotion_timeline = json.dumps(emotion_timeline)
            emotion_session.emotion_data = json.dumps(emotions_dict)

            # Calculate emotion variance and stability
            if combined_emotions and len(combined_emotions) > 1:
                avg = sum(combined_emotions) / len(combined_emotions)
                variance = sum((x - avg) ** 2 for x in combined_emotions) / len(combined_emotions)
                emotion_session.emotion_variance = variance
                stability = 1.0 - min(variance, 1.0)
                emotion_session.emotion_stability = stability

            emotion_session.save()
            logger.info(f"✓ MANUAL AGGREGATION COMPLETE for {session_id}")

            return Response({
                'status': 'success',
                'message': 'Emotion aggregation completed',
                'emotion_session': {
                    'session_id': emotion_session.session_id,
                    'dominant_emotion': emotion_session.dominant_emotion,
                    'avg_emotion_confidence': emotion_session.avg_emotion_confidence,
                    'qa_count': len(all_qas)
                }
            }, status=status.HTTP_200_OK)

        except InterviewSession.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Error in TriggerEmotionAggregationView: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to aggregate emotions',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

