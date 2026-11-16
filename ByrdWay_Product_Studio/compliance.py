"""Pre-send / post-send compliance for promotional email drafts (Sales & Follow-up role).

The Powerhouse NEVER sends email. It drafts; the owner sends from their own mail account. Before a draft may be
marked READY TO SEND it must pass every check below (US CAN-SPAM essentials + owner rules + duplicate prevention);
after the owner sends, record_sent() logs it so the same message can never be queued to the same person twice.
Opt-outs are permanent and checked on every draft. Records live in the private workspace (never in the repo/ZIP).
"""
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[a-z]{2,}$', re.I)
DECEPTIVE_SUBJECT = re.compile(r'^\s*(re|fwd?)\s*:', re.I)


def _path(root, name):
    from engine import workspace
    p = workspace(root) / 'sales' / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load(root, name, default):
    p = _path(root, name)
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default


def _save(root, name, data):
    _path(root, name).write_text(json.dumps(data, indent=1), encoding='utf-8')


def opt_out(root, email, note=''):
    s = _load(root, 'optouts.json', {})
    s[email.strip().lower()] = {'at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'note': note}
    _save(root, 'optouts.json', s)


def message_key(recipient, campaign):
    return hashlib.sha256(f'{recipient.strip().lower()}|{campaign.strip().lower()}'.encode()).hexdigest()[:20]


def presend_check(root, draft, catalog, sender):
    """draft: {recipient_email, recipient_name, recipient_verified_source, campaign, subject, body, product_title,
    product_url, price_mentioned (or None), relationship: 'opted_in'|'business_cold'}
    sender: {name, email, postal_address}. Returns {'ready': bool, 'problems': [...], 'checks': {...}}."""
    import salesintel
    P, C = [], {}
    rcpt = (draft.get('recipient_email') or '').strip().lower()
    C['recipient_email_valid'] = bool(EMAIL_RE.match(rcpt))
    C['recipient_identity_verified'] = bool(draft.get('recipient_verified_source'))
    C['not_opted_out'] = rcpt not in _load(root, 'optouts.json', {})
    sent = _load(root, 'sent.json', {})
    C['not_a_duplicate'] = message_key(rcpt, draft.get('campaign', '')) not in sent
    prev = [v for v in sent.values() if v['recipient'] == rcpt]
    C['contact_frequency_ok'] = not prev or (dt.date.today() - dt.date.fromisoformat(max(v['date'] for v in prev))).days >= 7
    prod = next((p for p in catalog if p.get('title') == draft.get('product_title')), None)
    C['product_marketable'] = bool(prod and prod.get('qa') == 'PASS' and prod.get('owner_approved') is True)
    C['listing_url_matches_catalog'] = bool(prod and prod.get('url') and draft.get('product_url') == prod.get('url')
                                           and str(prod.get('url')).startswith('https://www.teacherspayteachers.com/'))
    pm = draft.get('price_mentioned')
    C['price_matches_listing'] = pm is None or (prod is not None and prod.get('price') is not None
                                                and abs(float(pm) - float(prod['price'])) < 0.005)
    C['sender_identified'] = bool(sender.get('name') and EMAIL_RE.match(sender.get('email') or ''))
    body = draft.get('body') or ''
    C['postal_address_in_message'] = bool(sender.get('postal_address')) and sender['postal_address'] in body
    C['opt_out_instruction'] = bool(re.search(r'unsubscribe|opt[- ]?out|reply\s+["\']?stop', body, re.I))
    C['subject_not_deceptive'] = bool(draft.get('subject')) and not DECEPTIVE_SUBJECT.match(draft['subject'])
    C['identified_as_promotional'] = draft.get('relationship') == 'opted_in' or bool(
        re.search(r'promotion|advertisement|offer|resource', body, re.I))
    qa = salesintel.qa_text(f"{draft.get('subject', '')}\n{body}")
    C['sales_qa_clean'] = not qa
    labels = {'recipient_email_valid': 'recipient email address is not valid',
              'recipient_identity_verified': 'recipient not verified (record where the address came from: a public, permitted source)',
              'not_opted_out': 'recipient opted out - never contact again',
              'not_a_duplicate': 'this campaign was already sent to this recipient',
              'contact_frequency_ok': 'contacted in the last 7 days',
              'product_marketable': 'product is not Studio QA PASS + owner approved',
              'listing_url_matches_catalog': 'product link is not the exact TpT listing from the catalog',
              'price_matches_listing': 'price in the message does not match the listing',
              'sender_identified': 'sender name/email missing',
              'postal_address_in_message': 'physical postal address missing from the message (CAN-SPAM)',
              'opt_out_instruction': 'no clear opt-out instruction (CAN-SPAM)',
              'subject_not_deceptive': 'subject is missing or fakes a reply/forward',
              'identified_as_promotional': 'cold promotional message must be identifiable as an offer/advertisement',
              'sales_qa_clean': 'Sales QA: ' + '; '.join(qa)}
    P = [labels[k] for k, ok in C.items() if not ok]
    return {'ready': not P, 'problems': P, 'checks': C, 'sends_email': False,
            'rule': 'The app never sends. Owner sends from their own account, then records it (post-send QA).'}


def record_sent(root, draft, sent_by, checks_result):
    """Post-send QA: only a draft that passed presend_check may be recorded; the record blocks any duplicate."""
    if not checks_result.get('ready'):
        raise PermissionError('draft did not pass pre-send QA: ' + '; '.join(checks_result.get('problems', [])))
    sent = _load(root, 'sent.json', {})
    k = message_key(draft['recipient_email'], draft['campaign'])
    if k in sent:
        raise PermissionError('duplicate: already recorded as sent')
    sent[k] = {'recipient': draft['recipient_email'].strip().lower(), 'campaign': draft['campaign'],
               'product': draft.get('product_title'), 'date': dt.date.today().isoformat(), 'sent_by': sent_by}
    _save(root, 'sent.json', sent)
    return sent[k]


# ------------------------------------------------------------------ SECRET / DISTRIBUTION / PRESSURE TEST
PT_FIELDS = ['hypothesis', 'audience', 'offer', 'product_url', 'exposure', 'clicks', 'responses',
             'verified_orders', 'paid_units', 'seller_proceeds', 'decision']
DECISIONS = ('CONTINUE', 'MODIFY', 'STOP', 'PENDING')


def pressure_test(root, rec):
    """Record or update one pressure test. Numbers must come from real sources (TpT report, Blotato analytics, the
    owner's inbox); anything not yet measured stays None and is shown as NOT MEASURED - never estimated."""
    tests = _load(root, 'pressure_tests.json', [])
    rid = rec.get('id') or f"PT{len(tests) + 1:03d}"
    if rec.get('decision', 'PENDING') not in DECISIONS:
        raise ValueError(f'decision must be one of {DECISIONS}')
    if not str(rec.get('product_url', '')).startswith('https://www.teacherspayteachers.com/'):
        raise ValueError('every pressure test points at the exact TpT product page')
    row = {k: rec.get(k) for k in PT_FIELDS}
    row.update(id=rid, secret=rec.get('secret'), updated=dt.date.today().isoformat(),
               sources={k: rec.get('sources', {}).get(k) for k in ('exposure', 'clicks', 'verified_orders', 'paid_units', 'seller_proceeds')})
    for k in ('exposure', 'clicks', 'responses', 'verified_orders', 'paid_units', 'seller_proceeds'):
        if row[k] is not None and not row['sources'].get(k) and k not in ('responses',):
            raise ValueError(f'{k} needs its source (e.g. "TpT sales report 2026-11-20")')
    row['decision'] = row['decision'] or 'PENDING'
    tests = [t for t in tests if t['id'] != rid] + [row]
    _save(root, 'pressure_tests.json', tests)
    return row


def pressure_tests(root):
    out = []
    for t in _load(root, 'pressure_tests.json', []):
        r = dict(t)
        for k in ('exposure', 'clicks', 'responses', 'verified_orders', 'paid_units', 'seller_proceeds'):
            if r[k] is None:
                r[k] = 'NOT MEASURED'
        c, e = t.get('clicks'), t.get('exposure')
        r['click_rate'] = round(c / e, 4) if c is not None and e else 'NOT MEASURED'
        out.append(r)
    return out
