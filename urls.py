"""CareerMatch URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from CareerMatch_app import views, face_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('',views.login_get),
    path('logout',views.logout),
    path('login_post', views.login_post),
    path('addqualification', views.addqualification),
    path('addqualification_post', views.addqualification_post),
    path('admin_add_job_category',views.admin_add_job_category),
    path('view_qualificationsssss',views.view_qualificationsssss),
    path('deleteq/<id>',views.deleteq),
    path('admin_add_job_category_post', views.admin_add_job_category_post),
    path('admin_home', views.admin_home),
    path('approved_companies', views.approved_companies),
    path('rejected_companies', views.rejected_companies),
    path('view_companies', views.view_companies),
    path('view_job_categories', views.view_job_categories),
    path('view_suggestions_get', views.view_suggestions_get),
    path('view_suggestions_post', views.view_suggestions_post),
    path('view_users', views.view_users),
    path('approve_company/<id>', views.approve_company),
    path('reject_company/<id>', views.reject_company),
    path('delete_company/<int:id>', views.delete_company,name="delete_company"),

    ########################################## COMPANY ###################
    path('register_company_get',views.register_company_get),
    path('register_company_post',views.register_company_post),
    path('register_user_get',views.register_user_get),
    path('register_user_post',views.register_user_post),
    path('home', views.home),
    path('emailsetting', views.emailsetting),
    path('save_email_settings', views.save_email_settings),
    path('add_vacancy', views.add_vacancy),
    path('view_vacancy', views.view_vacancy),
    path('edit_vacancy/<id>', views.edit_vacancy),
    path('delete_vacancy/<id>', views.delete_vacancy),
    path('add_question/<id>', views.add_question),
    path('view_questions/<id>', views.view_questions),
    path('edit_questions/<id>', views.edit_questions),
    path('edit_questions_post/<id>', views.edit_questions_post),
    path('delete_questions/<id>', views.delete_questions),
    path('schedule_test/<id>', views.schedule_test),
    path('add_vacancy_post', views.add_vacancy_post),
    path('edit_vacancy_post/<id>', views.edit_vacancy_post),
    path('add_question_post/<id>', views.add_question_post),
    path('add_question_pdf/<id>', views.add_question_pdf),
    path('schedule_test_post/<id>', views.schedule_test_post),
    path('schedule_interview/<id>', views.schedule_interview),
    path('schedule_interview_post/<id>', views.schedule_interview_post),
    path('bschedule_interview/<id>', views.bschedule_interview),
    path('bschedule_interview_post/<id>', views.bschedule_interview_post),
    path('view_scheduled_interview/<id>', views.view_scheduled_interview),
    path('select_candidate/<id>/<status>', views.select_candidate),
    path('view_selected_candidate', views.view_selected_candidate),
    path('schedule_test/<id>', views.schedule_test),
    path('schedule_test_post/<id>', views.schedule_test_post),
    path('view_schedule_test/<id>', views.view_schedule_test),
    path('company_change_password', views.company_change_password),
    path('company_change_password_post', views.company_change_password_post),
    path('view_applied_candidate/<id>', views.view_applied_candidate),
    path('add_qualification/<id>', views.add_qualification),
    path('add_qualification_form/<qualification_id>/<vacancy_id>', views.add_qualification_form),
    path('remove_qualification_/<id>', views.remove_qualification_),
    path('deleteuser/<id>', views.deleteuser),

    path('forgotpassword', views.forgotpassword),
    path('forgotpasswordbuttonclick', views.forgotpasswordbuttonclick),
    path('otp', views.otp),
    path('otpbuttonclick', views.otpbuttonclick),
    path('forgotpswdpswed', views.forgotpswdpswed),
    path('forgotpswdpswedbuttonclick', views.forgotpswdpswedbuttonclick),
    path('student_home', views.student_home),
    path('view_profile', views.view_profile),
    path('edit_profile', views.edit_profile),
    path('register_student', views.register_student),
    path('register_student_post', views.register_student_post),

    path('candidate_view_college', views.candidate_view_college),
    path('upload_resume/<id>', views.upload_resume),
    path('upload_resume_post/<id>', views.upload_resume_post),
    path('view_applied_list', views.view_applied_list),
    path('view_selected_list', views.view_selected_list),
    path('candidate_change_password', views.candidate_change_password),
    path('candidate_change_password_post', views.candidate_change_password_post),
    path('send_complaint', views.send_complaint),
    path('send_complaint_post', views.send_complaint_post),  path('send_complaint2', views.send_complaint2),
    path('send_complaint_post2', views.send_complaint_post2),
    path('view_sample_question/<id>', views.view_sample_question),
    path('handle_post/<id>', views.handle_post),
    path('get_requirements/<vacancy_id>/', views.get_requirements),

    # Face Recognition & Emotion Detection URLs
    path('capture_candidate_registration', face_views.capture_candidate_registration),
    path('start_exam_monitoring', face_views.start_exam_monitoring),
    path('process_exam_frame', face_views.process_exam_frame),
    path('end_exam_monitoring', face_views.end_exam_monitoring),
    path('get_monitoring_status', face_views.get_monitoring_status),
    path('verify_candidate_before_exam', face_views.verify_candidate_before_exam),
    path('api/detect_faces/', views.detect_faces_api, name='detect_faces_api'),
    path('api/check_proctoring/', views.check_proctoring_api, name='check_proctoring_api'),
    path('check_proctoring/', views.check_proctoring_api, name='check_proctoring_api'),
    path('api/get_violations/<int:candidate_id>/', views.get_proctoring_summary, name='get_violations_api'),
    path('api/reset_violations/<int:candidate_id>/', views.reset_violation_count, name='reset_violation_count'),
    # Exam terminated page
    path('exam-terminated/', views.exam_terminated),

path('mockinterview/<id>',views.mockinterview),
    path('api/start_session/', views.StartSessionView.as_view(), name='start_session'),
    path('api/generate_questions/', views.GenerateQuestionsView.as_view(), name='generate_questions'),
    path('api/submit_qa/', views.SubmitQAView.as_view(), name='submit_qa'),
    path('api/session/<str:session_id>/analytics/', views.SessionAnalyticsView.as_view(), name='session_analytics'),
    path('api/end_session/<str:session_id>/', views.EndSessionView.as_view(), name='end_session'),
    path('api/sessions/active_roles/', views.ActiveRolesView.as_view(), name='active_roles'),
    path('api/sessions/stop_all/', views.StopAllSessionsView.as_view(), name='stop_all_sessions'),
    path('api/health/', views.HealthCheckView.as_view(), name='health_check'),
    path('proctoring_health_check/', views.proctoring_health_check, name='proctoring_health_check'),
    path('api/deepface_health/', views.deepface_health, name='deepface_health'),
    path('api/face_analyze/', views.face_analyze, name='face_analyze'),
    path('api/emotions/save/', views.SaveEmotionSessionView.as_view(), name='save_emotion_session'),
    path('api/emotions/session/<str:session_id>/', views.GetEmotionSessionView.as_view(), name='get_emotion_session'),
    path('api/emotions/all/', views.GetAllEmotionsView.as_view(), name='get_all_emotions'),
    path('api/emotions/session/<str:session_id>/delete/', views.DeleteEmotionSessionView.as_view(), name='delete_emotion_session'),
    path('api/emotions/aggregate/<str:session_id>/', views.TriggerEmotionAggregationView.as_view(), name='trigger_emotion_aggregation'),


       ]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)