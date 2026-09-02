import os, importlib, sys
sys.path.insert(0, r'c:\Users\Administrator\OneDrive\Desktop\PROJECT\CareerMatch')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CareerMatch.settings')
try:
    import django
    django.setup()
    m = importlib.import_module('CareerMatch_app.views')
    print('OK: exam_terminated exists=', hasattr(m, 'exam_terminated'))
except Exception as e:
    import traceback
    print('IMPORT ERROR')
    traceback.print_exc()
