"""Optional OpenAI-powered review. Read-only; never automatically patches files."""
import json,os
from engine import extract_text,original_file,Budget

ROLE_PROMPTS={
'Power Tool Repair':'Audit interactive HTML/JS math and science Power Tool for definite errors. Never claim to have run browser tests. Return precise locations and minimal correction suggestions.',
'Explainer Repair':'Audit written mathematics/science explanations and answer keys. Flag provable defects with independently worked solutions. Preserve approved design.',
'Power Tool Builder':'Outline a new Power Tool module based only on provided approved blueprint; mark missing specifications.',
'Lil Dr. Byrd Builder':'Outline a Lil Dr. Byrd Explainer chapter, preserving approved character identity and academic rigor. Do not invent the mascot image.',
'Academic Verifier':'Independently verify mathematical and scientific claims. Provide calculations and mark uncertainty; do not assert 99.9% quality.',
'Release QA':'Review proposed changes for regression risks, missing tests, locked assets and acceptance blockers.'}

def run_review(root,pid,role,model='gpt-4.1-mini',max_output_tokens=1200):
    if role not in ROLE_PROMPTS:raise ValueError('Unknown specialist role')
    if not os.environ.get('OPENAI_API_KEY'):raise RuntimeError('OPENAI_API_KEY not configured; no API call made')
    try:from openai import OpenAI
    except ImportError:raise RuntimeError('Install optional dependency: pip install openai')
    src,_=original_file(root,pid)
    content,warning=extract_text(src,max_chars=12000)
    if not content.strip():raise RuntimeError('No extractable source. Review manually; no API call made.')
    client=OpenAI(timeout=35,max_retries=0)
    result=client.responses.create(model=model,max_output_tokens=max_output_tokens,instructions=(
        'You are a ByrdWay specialist. This is READ-ONLY. No tools, no code execution, no publication. '
        'Separate verified defects from possible defects; never invent test results. '
        'Output concise numbered findings with exact evidence and smallest safe correction. '+ROLE_PROMPTS[role]),
        input=f'Filename: {src.name}\nWarning: {warning}\nContent:\n{content}')
    return result.output_text
