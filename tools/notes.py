# Adam's markup notes for Claude: the pins and circled areas he drops on parts in the sim (Markup mode), with their state.
#   python3 tools/notes.py            open and answered notes, from the running sim (or scenes/autosave.json)
#   python3 tools/notes.py --all      resolved ones too
#   python3 tools/notes.py FILE.json  from a saved scene
# Answer a note from the sim's own page (so the open tab keeps it):  Markup.reply('P3', 'text')  in the browser console.
import json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
args = [a for a in sys.argv[1:] if not a.startswith('--')]
show_all = '--all' in sys.argv
if args:
    J = json.load(open(args[0]))
else:
    try:
        with urllib.request.urlopen('http://localhost:8765/autosave', timeout=3) as r: J = json.load(r)
    except Exception:
        J = json.load(open(os.path.join(ROOT, 'scenes', 'autosave.json')))
st = J['state']
names = {d['id']: d['name'] for d in st.get('drawn', [])}
names.update({k: v.get('name') for k, v in st.get('info', {}).items() if v.get('name')})
TAG = {'open': 'waiting on Claude', 'answered': 'Claude answered', 'resolved': 'resolved'}
pins = st.get('pins', [])
order = {'open': 0, 'answered': 1, 'resolved': 2}
shown = sorted((p for p in pins if show_all or p.get('status', 'open') != 'resolved'), key=lambda p: (order.get(p.get('status', 'open'), 0), int(p['id'][1:] or 0)))
n = {k: sum(1 for p in pins if p.get('status', 'open') == k) for k in TAG}
print(f"scene saved {J.get('savedAt', '?')} · {n['open']} waiting on Claude · {n['answered']} answered · {n['resolved']} resolved")
for p in shown:
    where = p.get('w') or p['at']
    kind = f"area Ø {2 * p['r']:.1f} mm" if p.get('r') else 'spot'
    print(f"\n{p['id']} [{TAG.get(p.get('status', 'open'), 'waiting on Claude')}] {kind} on {names.get(p['part'], p['part'])} ({p['part']})")
    print(f"   at ({', '.join(f'{v:.2f}' for v in where)}) mm{' in the movement' if p.get('w') else ' in the part'}")
    print(f"   Adam: {p.get('note') or '(no note)'}")
    if p.get('reply'): print(f"   Claude: {p['reply']}")
if not shown: print('no notes' + ('' if show_all else ' open or answered'))
