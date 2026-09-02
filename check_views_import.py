import importlib, sys
sys.path.insert(0, r'c:\Users\Administrator\OneDrive\Desktop\PROJECT\CareerMatch')
try:
    importlib.invalidate_caches()
    m = importlib.import_module('CareerMatch_app.views')
    importlib.reload(m)
    print('OK: exam_terminated exists=', hasattr(m, 'exam_terminated'))
except Exception as e:
    import traceback
    print('IMPORT ERROR')
    traceback.print_exc()
