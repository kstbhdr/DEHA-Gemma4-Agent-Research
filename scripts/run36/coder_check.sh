python3 - <<'PEOF'
import subprocess as s, sys, os, py_compile
def sh(c):
    return s.run(c, shell=True, capture_output=True, text=True)
def istest(f):
    b = os.path.basename(f)
    return f.startswith(('tests/', 'test/', 'testing/', 'docs/')) or b.startswith('test_') or b == 'conftest.py'
files = sh('git diff --name-only').stdout.split() + sh('git ls-files --others --exclude-standard').stdout.split()
ok = True
for f in [x for x in files if istest(x)]:
    sh('git checkout -- ' + f + ' 2>/dev/null || rm -f ' + f)
    print('TEST_FILE_EDIT_REVERTED ' + f + ': never edit tests; edit the library source file instead')
src = [x for x in files if x.endswith('.py') and not istest(x) and os.path.exists(x)]
if not src:
    print('NO_SOURCE_CHANGE_YET: no library .py file is changed (did edit_file return an error?)')
    ok = False
for f in src:
    m = f[4:] if f.startswith('src/') else f
    m = m[:-3].replace('/', '.')
    m = m[:-9] if m.endswith('.__init__') else m
    err = ''
    try:
        py_compile.compile(f, doraise=True)
    except Exception as e:
        err = str(e)
    if not err:
        r = s.run([sys.executable, '-c', 'import importlib.util as u, sys; m = sys.argv[1]; u.find_spec(m.split(chr(46))[0]) and __import__(m)', m], capture_output=True, text=True)
        err = r.stderr[-800:] if r.returncode else ''
    if err:
        ok = False
        sh('git checkout -- ' + f + ' 2>/dev/null || rm -f ' + f)
        print('COMPILE_OR_IMPORT_FAILED_REVERTING ' + f + ' (the whole file was reverted, redo ALL your changes to it):' + chr(10) + err)
        continue
    d = sh('git diff -U0 -- ' + f).stdout.splitlines()
    add = [x for x in d if x.startswith('+') and not x.startswith('+++')]
    if any(x.startswith('-') and not x.startswith('---') and x[1:].strip().startswith(('import ', 'from ')) for x in d):
        ok = False
        print('IMPORT_REMOVED ' + f + ': run git checkout -- ' + f + ' and redo the edit keeping every import line')
    if any(len(a) > 20 and a == c for a, c in zip(add, add[1:])):
        ok = False
        print('DUPLICATE_LINES ' + f + ': a line was written twice in a row; run git checkout -- ' + f + ' and redo the edit')
    print(sh('git diff -U3 -- ' + f).stdout[-2500:])
if ok:
    print('SYNTAX_AND_IMPORT_OK')
if os.path.exists('/tmp/deha_repro.py'):
    r = sh('timeout 60 python3 /tmp/deha_repro.py')
    o = (r.stdout + r.stderr)[-1200:]
    if r.returncode == 0:
        print('REPRO_PASS (the issue example now behaves correctly)')
    elif 'AssertionError' in o:
        print('REPRO_FAIL (the issue example still fails; fix your edit):' + chr(10) + o)
    else:
        print('REPRO_INVALID (the repro script itself crashed; ignore it):' + chr(10) + o[-300:])
PEOF
