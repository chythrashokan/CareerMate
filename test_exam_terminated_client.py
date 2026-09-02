import os, importlib, sys
sys.path.insert(0, r'c:\Users\Administrator\OneDrive\Desktop\PROJECT\CareerMatch')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CareerMatch.settings')
try:
    import django
    django.setup()
    from django.test import Client
    c = Client()
    resp = c.get('/exam-terminated/')
    print('STATUS', resp.status_code)
    print('LENGTH', len(resp.content))
    print(resp.content.decode('utf-8')[:500])
except Exception as e:
    import traceback
    print('ERROR')
    traceback.print_exc()
