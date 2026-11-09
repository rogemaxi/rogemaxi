"""ByrdWay Product Engineering Studio: protected, review-first local prototype."""
import hashlib, json, os, re, shutil, time, uuid, zipfile
from pathlib import Path

SUPPORTED={'.html','.htm','.js','.css','.txt','.md','.json','.pdf','.zip'}
ROLES=['Orchestrator','Power Tool Repair','Explainer Repair','Power Tool Builder','Lil Dr. Byrd Builder','Academic Verifier','Release QA']
MAX_FILE=35*1024*1024

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def workspace(root):
    root=Path(root).resolve()
    for folder in ('originals','proposals','reports','approved'):(root/folder).mkdir(parents=True,exist_ok=True)
    return root

def safe_extract_zip(src,dest):
    dest=Path(dest).resolve();dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(src) as z:
        members=z.infolist()
        if len(members)>500:raise ValueError('ZIP contains too many entries')
        if sum(m.file_size for m in members)>150*1024*1024:raise ValueError('ZIP uncompressed size exceeds limit')
        for item in members:
            p=Path(item.filename)
            if p.is_absolute() or '..' in p.parts or item.is_dir() and not item.filename.endswith('/'):raise ValueError('Unsafe ZIP entry')
            if (item.external_attr >> 16)&0o170000 == 0o120000:raise ValueError('ZIP symbolic link forbidden')
            target=(dest/p).resolve()
            if not target.is_relative_to(dest):raise ValueError('Unsafe ZIP path')
            if item.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(item) as inp,open(target,'wb') as out:shutil.copyfileobj(inp,out)

def import_product(src,root):
    src=Path(src).resolve();root=workspace(root)
    if not src.is_file() or src.suffix.lower() not in SUPPORTED:raise ValueError('Unsupported input type')
    if src.stat().st_size>MAX_FILE:raise ValueError('File exceeds 35 MB limit')
    pid=uuid.uuid4().hex[:12]; folder=root/'originals'/pid;folder.mkdir()
    dest=folder/src.name;shutil.copy2(src,dest)
    manifest={'id':pid,'name':src.name,'sha256':sha256(dest),'imported_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'ORIGINAL_LOCKED'}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if src.suffix.lower()=='.zip':safe_extract_zip(dest,folder/'unpacked')
    return manifest

def inventory(root):
    root=workspace(root);result=[]
    for p in (root/'originals').glob('*/manifest.json'):
        result.append(json.loads(p.read_text(encoding='utf-8')))
    return sorted(result,key=lambda x:x['imported_at'],reverse=True)

def original_file(root,pid):
    root=workspace(root)
    manifest=json.loads((root/'originals'/pid/'manifest.json').read_text(encoding='utf-8'))
    src=root/'originals'/pid/manifest['name']
    if sha256(src)!=manifest['sha256']:raise ValueError('Original hash mismatch: stop')
    return src,manifest

def extract_text(src,max_chars=60000):
    ext=src.suffix.lower()
    if ext=='.pdf':
        try:
            import fitz
            doc=fitz.open(src); text='\n'.join(page.get_text() for page in doc)
            if not text.strip():return '', 'Image-only PDF: manual page inspection or approved OCR is needed.'
            return text[:max_chars], ('PDF text truncated.' if len(text)>max_chars else '')
        except ImportError:return '', 'Install PyMuPDF to inspect PDF text.'
    if ext=='.zip':
        with zipfile.ZipFile(src) as z:
            texts=[]
            for name in z.namelist():
                if Path(name).suffix.lower() in {'.html','.htm','.js','.css','.txt','.md','.json'}:
                    data=z.read(name)
                    texts.append(f'\n### FILE {name}\n'+data.decode('utf-8',errors='replace')[:20000])
            alltext='\n'.join(texts)
            return alltext[:max_chars],('ZIP content truncated.' if len(alltext)>max_chars else '')
    return src.read_text(encoding='utf-8',errors='replace')[:max_chars],''

def local_audit(src):
    text,warning=extract_text(src)
    issues=[]
    if warning:issues.append({'severity':'WARNING','detail':warning})
    if not text.strip():issues.append({'severity':'BLOCKER','detail':'No machine-readable source text available for validation.'})
    if src.suffix.lower() in {'.html','.htm','.zip'}:
        if '<script' in text and 'onclick=' in text:issues.append({'severity':'INFO','detail':'Inline event handlers found; inspect browser interactions.'})
        if re.search(r'(?i)\b(todo|fixme|placeholder)\b',text):issues.append({'severity':'REVIEW','detail':'Placeholder/TODO/FIXME text found; human inspection needed.'})
    return {'issues':issues,'chars_reviewed':len(text),'source_hash':sha256(src),'text':text}

def create_audit(root,pid):
    src,m=original_file(root,pid); audit=local_audit(src)
    report={k:v for k,v in audit.items() if k!='text'}
    report.update({'product_id':pid,'product_name':m['name'],'roles':ROLES,'quality_score':'NOT_MEASURED','release':'BLOCKED_PENDING_INDEPENDENT_TESTS'})
    out=workspace(root)/'reports'/f'{pid}_audit.json';out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

def save_proposal(root,pid,proposed_text,reason):
    src,m=original_file(root,pid)
    if src.suffix.lower() not in {'.html','.htm','.js','.css','.txt','.md','.json'}:raise ValueError('Direct text proposals only; PDFs and ZIPs require source-aware editors.')
    if not proposed_text.strip():raise ValueError('Empty proposal')
    outdir=workspace(root)/'proposals'/pid;outdir.mkdir(parents=True,exist_ok=True)
    candidate=outdir/(uuid.uuid4().hex[:8]+'_'+src.name)
    candidate.write_text(proposed_text,encoding='utf-8')
    record={'product_id':pid,'original_sha256':m['sha256'],'candidate':str(candidate),'candidate_sha256':sha256(candidate),'reason':reason,'status':'AWAITING_OWNER_APPROVAL','quality_score':'NOT_MEASURED'}
    (candidate.with_suffix(candidate.suffix+'.review.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
    return record

def approve_proposal(root,pid,candidate_path,explicit_approval=False):
    if not explicit_approval:raise PermissionError('Explicit owner approval required')
    src,m=original_file(root,pid);candidate=Path(candidate_path).resolve();proposal_dir=(workspace(root)/'proposals'/pid).resolve()
    if not candidate.is_relative_to(proposal_dir):raise ValueError('Candidate outside proposal directory')
    meta=json.loads(candidate.with_suffix(candidate.suffix+'.review.json').read_text(encoding='utf-8'))
    if meta['original_sha256']!=m['sha256'] or meta['candidate_sha256']!=sha256(candidate):raise ValueError('Proposal integrity mismatch')
    approved=workspace(root)/'approved'/pid;approved.mkdir(parents=True,exist_ok=True)
    out=approved/(uuid.uuid4().hex[:8]+'_'+src.name);shutil.copy2(candidate,out)
    meta['status']='OWNER_APPROVED_COPY';meta['approved_copy']=str(out)
    candidate.with_suffix(candidate.suffix+'.review.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    return out

class Budget:
    def __init__(self,cap_usd=1.0,max_attempts=3):
        if not 0<cap_usd<=20 or not 1<=max_attempts<=5:raise ValueError('Budget limits exceeded')
        self.cap_usd=cap_usd;self.max_attempts=max_attempts
    def can_continue(self,attempts,estimated_spent):return attempts<self.max_attempts and estimated_spent<self.cap_usd
