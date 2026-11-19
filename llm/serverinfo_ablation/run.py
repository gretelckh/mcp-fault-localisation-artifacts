"""Verify archived Study A serverInfo predictions or run the counterfactual experiment."""
import argparse, ast, csv, hashlib, json, os, random, re, threading, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

folder = Path(__file__).resolve().parent
archive = folder.parents[1]
prefix = (folder/'prompt.txt').read_text(encoding='utf8')
surface = {x['issue']: x['surface_text'] for x in map(json.loads,(folder/'inputs.jsonl').read_text(encoding='utf8').splitlines())}
with (archive/'data/active_bugs_339.csv').open(encoding='utf8',newline='') as f:
    truth = {int(x['issue'][1:]): x['origin_layer'] for x in csv.DictReader(f) if x['reproduction_status']=='reproduced'}
assert len(surface)==72 and surface.keys()==truth.keys()

# Match the two serialized forms in this frozen source dataset and fail on any other occurrence.
meta = re.compile(r"(?<=meta=\{)'io\.modelcontextprotocol/serverInfo': \{'name': '[^'\r\n]*', 'version': '[^'\r\n]*'\}")
wire = re.compile(r',"serverInfo":\{"name":"[^"\r\n]*","version":"[^"\r\n]*"\}')
changed = {}
for n,s in surface.items():
    hits = list(meta.finditer(s))+list(wire.finditer(s))
    assert len(hits)==s.count('serverInfo') and len(hits)<=1, n
    if not hits:
        changed[n]=s
        continue
    hit=hits[0]
    new=s[:hit.start()]+s[hit.end():]
    assert new[:hit.start()]+hit[0]+new[hit.start():]==s
    if hit.re is meta:
        m=re.search(r'meta=(\{\})',new)
        assert m and ast.literal_eval(m[1])=={}
    else:
        old_line=next(line for line in s.splitlines() if '"serverInfo"' in line)
        new_line=next(line for line in new.splitlines() if '"protocolVersion"' in line)
        old_wire=json.loads(old_line[old_line.index('{'):])
        del old_wire['result']['serverInfo']
        assert old_wire==json.loads(new_line[new_line.index('{'):])
    changed[n]=new
affected={n for n in surface if changed[n]!=surface[n]}
assert len(affected)==36

def prompt(n,arm):
    return prefix + (changed[n] if arm=='stripped' else surface[n])
def fingerprint(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()
for n in surface:
    assert prompt(n,'asis')==prompt(n,'noop')
    assert (prompt(n,'asis')!=prompt(n,'stripped'))==(n in affected)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('mode', choices=['verify', 'run'])
parser.add_argument('--output', type=Path, default=Path('serverinfo_rerun.jsonl'))
args = parser.parse_args()
arms = ('asis', 'stripped', 'noop')
jobs = [(n, arm, rep) for rep in range(1, 4) for n in sorted(surface) for arm in arms]
random.Random(20261119).shuffle(jobs)

if args.mode == 'verify':
    responses = {}
    for line in (folder/'responses.jsonl').read_text(encoding='utf8').splitlines():
        row = json.loads(line)
        n, arm, repeat = key = (row['issue'], row['arm'], row['repeat'])
        assert key not in responses and row['input_sha256'] == fingerprint(prompt(n, arm))
        assert row['has_field'] == (n in affected)
        assert row['model'] == 'CS/DeepSeek-V4-Flash-FP8'
        assert row['raw'].strip() == row['pred'] and row['pred'] in {'Host','Client','Server','Transport'}
        responses[key] = row
    assert set(responses) == set(jobs)
    for arm in arms:
        rows = [responses[key] for key in jobs if key[1] == arm]
        hits = sum(row['pred'] == truth[row['issue']] for row in rows)
        server = sum(row['pred'] == 'Server' for row in rows)
        assert (hits, server) == (123, 183)
        print(f'{arm}: {hits}/{len(rows)} correct, {server}/{len(rows)} predicted Server')
    for n in surface:
        predicted = {responses[n, arm, rep]['pred'] for arm in arms for rep in (1, 2, 3)}
        assert len(predicted) == 1
    print('Verified 648 prompt hashes and responses, 36 changed inputs, and zero label changes.')
    raise SystemExit

from openai import OpenAI

settings = {k: os.environ[k] for k in ('LLM_BASE_URL', 'LLM_API_KEY', 'LLM_MODEL')}
client = OpenAI(base_url=settings['LLM_BASE_URL'], api_key=settings['LLM_API_KEY'], timeout=40, max_retries=0)
dest = args.output
if dest.resolve() == (folder/'responses.jsonl').resolve():
    parser.error('Choose a separate output file for new requests.')
seen={}
if dest.exists():
    for line in dest.read_text(encoding='utf8').splitlines():
        row=json.loads(line)
        key=(row['issue'],row['arm'],row['repeat'])
        assert row['input_sha256']==fingerprint(prompt(row['issue'],row['arm']))
        seen[key]=row
pending=[job for job in jobs if job not in seen or 'error' in seen[job]]
lock=threading.Lock()
next_start=0.0
def predict(job):
    global next_start
    n,arm,rep=job
    content=prompt(n,arm)
    row=dict(issue=n,arm=arm,repeat=rep,input_sha256=fingerprint(content),has_field=n in affected)
    for attempt in range(5):
        with lock:
            wait=max(0,next_start-time.monotonic())
            if wait: time.sleep(wait)
            next_start=time.monotonic()+3.3
        try:
            result=client.chat.completions.create(model=settings['LLM_MODEL'],messages=[dict(role='user',content=content)],temperature=0,max_tokens=16)
            raw=result.choices[0].message.content or ''
            match=re.search(r'\b(Host|Client|Server|Transport)\b',raw)
            return row | dict(pred=match[1] if match else None,raw=raw,model=result.model,finish=result.choices[0].finish_reason)
        except Exception as exc:
            status=getattr(exc,'status_code',None)
            error=type(exc).__name__
            if status in (401,403,404): break
            with lock:
                next_start=max(next_start,time.monotonic()+(min(12*2**attempt,60) if status==429 else min(3*2**attempt,15)))
    return row | dict(error=error,status=status)

with dest.open('a',encoding='utf8') as f, ThreadPoolExecutor(max_workers=2) as pool:
    for i,row in enumerate(pool.map(predict,pending),1):
        seen[row['issue'],row['arm'],row['repeat']]=row
        f.write(json.dumps(row,ensure_ascii=False)+'\n')
        f.flush()
        if i<=3 or i%25==0 or i==len(pending):
            print('processed',i,'of',len(pending),'complete',sum('error' not in v for v in seen.values()),flush=True)
        if row.get('status') in (401,403,404):
            raise SystemExit(f"endpoint rejected request with HTTP {row['status']}")
for arm in arms:
    results=[x for x in seen.values() if x['arm']==arm and 'error' not in x]
    print(arm,len(results),'correct',sum(x['pred']==truth[x['issue']] for x in results),'Server',sum(x['pred']=='Server' for x in results),'invalid',sum(x['pred'] is None for x in results))
raise SystemExit(any(job not in seen or 'error' in seen[job] for job in jobs))
