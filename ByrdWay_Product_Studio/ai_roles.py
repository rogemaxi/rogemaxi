"""Optional OpenAI-powered specialist assistance.

* read-only review (run_review) and patch SUGGESTIONS (propose_patches);
* never patches files itself: suggestions are applied only to a working copy by
  the orchestrator and must then pass deterministic tests + independent
  academic verification + Release QA;
* every call goes through costs.BudgetGuard (estimate, caps, owner approval,
  ledger). No key -> no call. Claude/Anthropic is not used at runtime.
"""
import json, re
from engine import extract_text, original_file
from config import load_settings
from costs import BudgetGuard, get_api_key

ROLE_PROMPTS = {
    'Power Tool Repair': 'Audit interactive HTML/JS math and science Power Tool for definite errors. Never claim to have run browser tests. Return precise locations and minimal correction suggestions.',
    'Explainer Repair': 'Audit written mathematics/science explanations and answer keys. Flag provable defects with independently worked solutions. Preserve approved design.',
    'Power Tool Builder': 'Outline a new Power Tool module based only on provided approved blueprint; mark missing specifications.',
    'Lil Dr. Byrd Builder': 'Outline a Lil Dr. Byrd Explainer chapter, preserving approved character identity and academic rigor. Do not invent the mascot image.',
    'Academic Verifier': 'Independently verify mathematical and scientific claims. Provide calculations and mark uncertainty; do not assert 99.9% quality.',
    'Release QA': 'Review proposed changes for regression risks, missing tests, locked assets and acceptance blockers.'}

ROLE_COMPLEXITY = {'Power Tool Repair': 'standard', 'Explainer Repair': 'standard',
                   'Power Tool Builder': 'complex', 'Lil Dr. Byrd Builder': 'complex',
                   'Academic Verifier': 'complex', 'Release QA': 'simple'}

BASE_INSTRUCTIONS = ('You are a ByrdWay specialist. This is READ-ONLY. No tools, no code execution, '
                     'no publication. Separate verified defects from possible defects; never invent '
                     'test results. Output concise numbered findings with exact evidence and smallest '
                     'safe correction. ')


def model_for(settings, role, model=None):
    return model or settings['models'][ROLE_COMPLEXITY.get(role, 'standard')]


def _client(settings, client=None):
    if client is not None:
        return client
    key = get_api_key()
    if not key:
        raise RuntimeError('OPENAI_API_KEY not configured; no API call made')
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError('Install optional dependency: pip install openai')
    return OpenAI(api_key=key, timeout=settings['ai']['timeout_seconds'], max_retries=0)


def run_review(root, pid, role, model=None, max_output_tokens=None, approver=None,
               job_id=None, client=None):
    if role not in ROLE_PROMPTS:
        raise ValueError('Unknown specialist role')
    settings = load_settings(root)
    if client is None and not get_api_key():
        raise RuntimeError('OPENAI_API_KEY not configured; no API call made')
    src, _ = original_file(root, pid)
    content, warning = extract_text(src, max_chars=settings['ai']['max_input_chars'])
    if not content.strip():
        raise RuntimeError('No extractable source. Review manually; no API call made.')
    model = model_for(settings, role, model)
    max_output_tokens = max_output_tokens or settings['ai']['max_output_tokens']
    instructions = BASE_INSTRUCTIONS + ROLE_PROMPTS[role]
    payload = f'Filename: {src.name}\nWarning: {warning}\nContent:\n{content}'
    c = _client(settings, client)
    guard = BudgetGuard(root, settings)
    result = guard.paid_call(job_id or f'review_{pid}', role, model,
                             len(instructions) + len(payload), max_output_tokens, approver,
                             lambda: c.responses.create(model=model, max_output_tokens=max_output_tokens,
                                                        instructions=instructions, input=payload),
                             input_bytes=len((instructions + payload).encode('utf-8')))
    return result.output_text


PATCH_SCHEMA_HINT = ('Return ONLY JSON: {"patches":[{"file":"relative/path","find":"exact existing text",'
                     '"replace":"new text","reason":"verified defect being fixed"}]}. "find" must occur '
                     'exactly once in the file. Make the smallest possible change. If unsure, return '
                     '{"patches":[]}.')


def propose_patches(root, job_id, files, defects, approver, client=None, model=None):
    """Ask the model for minimal patch suggestions for unresolved defects.

    files: {relative_path: text}. Returns list of patch dicts (unvalidated;
    the orchestrator validates and tests every one).
    """
    settings = load_settings(root)
    model = model_for(settings, 'Power Tool Repair', model)
    budget_chars = settings['ai']['max_input_chars']
    parts, used = [], 0
    for path, text in files.items():
        chunk = f'\n### FILE {path}\n{text}'
        if used + len(chunk) > budget_chars:
            chunk = chunk[:max(0, budget_chars - used)]
        parts.append(chunk)
        used += len(chunk)
        if used >= budget_chars:
            break
    defect_text = json.dumps([{k: d.get(k) for k in ('id', 'severity', 'file', 'detail')}
                              for d in defects], indent=1)[:3000]
    instructions = BASE_INSTRUCTIONS + ROLE_PROMPTS['Power Tool Repair'] + ' ' + PATCH_SCHEMA_HINT
    payload = f'Unresolved defects:\n{defect_text}\nSource:\n{"".join(parts)}'
    c = _client(settings, client)
    max_out = settings['ai']['max_output_tokens']
    guard = BudgetGuard(root, settings)
    resp = guard.paid_call(job_id, 'Power Tool Repair', model, len(instructions) + len(payload),
                           max_out, approver,
                           lambda: c.responses.create(model=model, max_output_tokens=max_out,
                                                      instructions=instructions, input=payload),
                           input_bytes=len((instructions + payload).encode('utf-8')))
    return parse_patch_json(getattr(resp, 'output_text', '') or '')


def parse_patch_json(text):
    m = re.search(r'\{.*\}', text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return []
    out = []
    for p in data.get('patches', []) if isinstance(data, dict) else []:
        if isinstance(p, dict) and all(isinstance(p.get(k), str) for k in ('file', 'find', 'replace')):
            out.append({'file': p['file'], 'find': p['find'], 'replace': p['replace'],
                        'reason': str(p.get('reason', ''))[:300], 'source': 'ai_suggestion'})
    return out
