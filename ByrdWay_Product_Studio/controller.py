"""UI-independent application facade. The Tk UI calls only these functions,
so every user action is covered by automated tests without a display."""
from pathlib import Path
import json

import engine, release, builders, assets
from config import load_settings, save_settings
from costs import Ledger, get_api_key, store_api_key
from joblog import activity, read_activity
from orchestrator import Orchestrator


class Studio:
    def __init__(self, root):
        self.root = engine.workspace(root)

    # products
    def products(self):
        out = []
        for p in engine.inventory(self.root):
            if p.get('status') != 'MANIFEST_CORRUPTED':
                p['integrity'] = 'OK' if engine.verify_original(self.root, p['id']) else 'HASH MISMATCH'
            out.append(p)
        return out

    def import_product(self, path):
        m = engine.import_product(path, self.root)
        activity(self.root, 'Orchestrator', f'Imported {m["name"]} as {m["product_type"]}', sha256=m['sha256'])
        return m

    def local_audit(self, pid):
        return engine.create_audit(self.root, pid)

    def verify_all_originals(self):
        return {p['id']: engine.verify_original(self.root, p['id']) for p in engine.inventory(self.root)
                if p.get('status') != 'MANIFEST_CORRUPTED'}

    # jobs
    def run_job(self, pid, ai_enabled=False, approver=None, progress=None, run_browser=True, ai_client=None,
                authorization=None):
        return Orchestrator(self.root).run_repair_job(pid, ai_enabled=ai_enabled, approver=approver,
                                                      progress=progress, run_browser=run_browser, ai_client=ai_client,
                                                      authorization=authorization)

    def powerhouse(self):
        import powerhouse
        return powerhouse.organization()

    def lessons(self):
        import powerhouse
        return powerhouse.lessons_for_build(self.root)

    def job_timeline(self, job_id):
        import powerhouse
        return powerhouse.job_timeline(self.job(job_id))

    def jobs(self):
        return Orchestrator(self.root).list_jobs()

    def job(self, job_id):
        return Orchestrator(self.root).load_job(job_id)

    def job_report(self, job_id):
        p = self.root / 'jobs' / job_id / 'REPORT.md'
        return p.read_text(encoding='utf-8') if p.exists() else '(no report)'

    def job_diff(self, job_id):
        p = self.root / 'jobs' / job_id / 'changes.diff'
        return p.read_text(encoding='utf-8') if p.exists() else ''

    def job_evidence_dir(self, job_id):
        return self.root / 'jobs' / job_id

    def attest(self, job_id, item_key, owner, note):
        return release.attest(self.root, job_id, item_key, owner, note)

    def approve(self, job_id, owner, explicit=False, visual_reviewed=False):
        return release.owner_approve(self.root, job_id, owner, explicit, visual_reviewed)

    def reject(self, job_id, owner, reason):
        return release.owner_reject(self.root, job_id, owner, reason)

    def export(self, job_id, dest=None):
        return release.export_approved(self.root, job_id, dest)

    def image_findings(self, job_id):
        return release.image_findings(self.root, job_id)

    def decide_image_finding(self, job_id, item_id, verdict, owner, correction=None, replacement=None):
        return release.decide_image_finding(self.root, job_id, item_id, verdict, owner, correction,
                                            replacement=replacement)

    def repair_image_findings(self, job_id, owner, explicit=False, progress=None):
        return release.repair_confirmed_image_findings(self.root, job_id, owner, explicit, progress)

    def export_correction_sheet(self, job_id, owner, explicit=False, dest=None):
        return release.export_correction_sheet(self.root, job_id, owner, explicit, dest)

    def rerun_qa(self, job_id):
        return release.requeue_qa(self.root, job_id)

    def diagnose(self, pid, progress=None, run_browser=True):
        return Orchestrator(self.root).diagnose(pid, run_browser=run_browser, progress=progress)

    def latest_report(self, pid):
        cands = []
        for j in self.jobs():
            if j['product_id'] == pid and (self.root / 'jobs' / j['id'] / 'report.html').exists():
                p = self.root / 'jobs' / j['id'] / 'report.html'
                cands.append((p.stat().st_mtime_ns, 1, p))
        for d in (self.root / 'reports').glob('diag_*/diagnosis.json'):
            try:
                x = json.loads(d.read_text(encoding='utf-8'))
            except ValueError:
                continue
            if x.get('product_id') == pid and (d.parent / 'diagnosis.html').exists():
                p = d.parent / 'diagnosis.html'
                cands.append((p.stat().st_mtime_ns, 0, p))
        return max(cands, key=lambda c: (c[0], c[1]))[2] if cands else None

    def job_html_report(self, job_id):
        p = self.root / 'jobs' / job_id / 'report.html'
        if not p.exists():
            try:
                import report
                p = report.write_job_report(self.root, self.job(job_id))
            except Exception:
                return None
        return p

    # builders
    def new_build(self, blueprint_path, kind):
        bp = json.loads(Path(blueprint_path).read_text(encoding='utf-8'))
        return builders.Build.create(self.root, bp, kind)

    def builds(self):
        out = []
        for p in (self.root / 'builds').glob('*/state.json'):
            try:
                s = json.loads(p.read_text(encoding='utf-8'))
                bp = json.loads((p.parent / 'blueprint.json').read_text(encoding='utf-8'))
            except (ValueError, OSError):
                continue
            s['title'] = bp.get('product_title') or (bp.get('chapters') or [{}])[0].get('title', '')
            s['sample'] = builders.is_sample(bp)
            done = sum(1 for u in s['order'] if s['units'][u]['status'] == 'OWNER_APPROVED')
            s['summary'] = f'{done}/{len(s["order"])} approved' + (' — SAMPLE' if s['sample'] else '') + (
                ' — assembled' if s.get('assembled') else '')
            out.append(s)
        return sorted(out, key=lambda s: s.get('created_at', ''), reverse=True)

    def build_prerequisites(self, kind, build_id=None):
        bp = builders.Build(self.root, build_id).blueprint if build_id else None
        return builders.prerequisites(self.root, kind, bp)

    def sample_form(self, kind):
        here = Path(__file__).resolve().parent / 'samples'
        if kind == 'power_tool':
            bp = json.loads((here / 'SAMPLE_power_tool_blueprint.json').read_text(encoding='utf-8'))
            return builders.form_from_power_tool_blueprint(bp)
        bp = json.loads((here / 'SAMPLE_lil_dr_byrd_physics_blueprint.json').read_text(encoding='utf-8'))
        return builders.form_from_chapter_blueprint(bp)

    def load_blueprint_form(self, path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if data.get('_form_kind'):                      # a saved draft
            return data['_form_kind'], data['form']
        if 'modules' in data:
            return 'power_tool', builders.form_from_power_tool_blueprint(data)
        if 'chapters' in data:
            return 'lil_dr_byrd', builders.form_from_chapter_blueprint(data)
        raise ValueError('This file is not a ByrdWay blueprint (no modules or chapters found).')

    def build_form(self, build_id):
        b = builders.Build(self.root, build_id)
        kind = b.state['kind']
        bp = b.blueprint
        return kind, (builders.form_from_power_tool_blueprint(bp) if kind == 'power_tool'
                      else builders.form_from_chapter_blueprint(bp))

    def create_build_from_form(self, kind, form):
        bp = (builders.power_tool_blueprint_from_form(form) if kind == 'power_tool'
              else builders.chapter_blueprint_from_form(form))
        builders.save_blueprint(self.root, bp, kind)
        b = builders.Build.create(self.root, bp, kind)
        activity(self.root, 'Power Tool Builder' if kind == 'power_tool' else 'Lil Dr. Byrd Builder',
                 f'Build {b.id} created from form')
        return b

    def save_draft(self, kind, form):
        d = self.root / 'blueprints' / 'drafts'
        d.mkdir(parents=True, exist_ok=True)
        import re, time
        name = re.sub(r'[^A-Za-z0-9]+', '_', form.get('product_title') or (form.get('chapters') or [{}])[0].get('title') or 'draft')[:40]
        p = d / f'{kind}_{name}_{time.strftime("%Y%m%d_%H%M%S")}.json'
        engine.write_json(p, {'_form_kind': kind, 'form': form})
        return p

    def reject_unit(self, build_id, unit, reason):
        return builders.Build(self.root, build_id).reject(unit, reason)

    def assemble_and_verify(self, build_id, progress=None, run_browser=True):
        m = self.assemble_and_import(build_id, True)
        return self.run_job(m['id'], progress=progress, run_browser=run_browser)

    def build_next(self, build_id):
        b = builders.Build(self.root, build_id)
        s = b.state
        for u in s['order']:
            st = s['units'][u]['status']
            if st == 'OWNER_APPROVED':
                continue
            if s['kind'] == 'power_tool':
                return u, builders.build_power_tool_module(self.root, build_id, u)
            return u, builders.build_lil_dr_byrd_chapter(self.root, build_id, u)
        return None, None

    def construct_next(self, build_id, run_browser=True):
        """Build the next unit THROUGH the construction loop: Builder -> Build QA -> repair -> rebuild -> Chief Judge."""
        import construction, powerhouse
        s = builders.Build(self.root, build_id).state
        for u in s['order']:
            if s['units'][u]['status'] == 'OWNER_APPROVED':
                continue
            return u, construction.construct_unit(self.root, build_id, u, run_browser=run_browser,
                                                  lessons=powerhouse.lessons_for_build(self.root))
        return None, None

    def build_concept_tiles(self, toc_md, content_json, course, mascot=None):
        """Concept Tiles in the owner-approved ByrdWay format from an APPROVED table of contents + tile content,
        through independent QA (design conformance, TOC coverage, continuity, academic, Reader lessons)."""
        import byrdway_tiles, concepttiles, time
        toc = concepttiles.toc_from_blueprint_md(Path(toc_md).read_text(encoding='utf-8'))
        content = {int(k): v for k, v in json.loads(Path(content_json).read_text(encoding='utf-8')).items()}
        out = self.root / 'concept_tiles' / time.strftime('%Y%m%d_%H%M%S')
        out.mkdir(parents=True, exist_ok=True)
        rep = byrdway_tiles.build_product(toc, content, out / f'{course.replace(" ", "_").replace("+", "Plus")}_Concept_Tiles.pdf',
                                          course, mascot=Path(mascot) if mascot else None)
        (out / 'QA_REPORT.json').write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding='utf-8')
        activity(self.root, 'Concept Tiles Builder', f'built {rep["pdf"]}: {rep["decision"]}', checks=rep['mandatory_checks'], failed=rep['failed'])
        return rep

    def produce_commercial(self, spec_json):
        """30-second commercial: script -> storyboard -> local draft render -> full review -> scores -> gate.
        spec_json: {"product": {...}, "assets": {...}, "narration": optional approved-voice WAV}. Nothing is published."""
        import commercial, time
        if not commercial.ffmpeg_available():
            raise RuntimeError('ffmpeg is not installed: install it to render drafts (the commercial was not produced)')
        spec = json.loads(Path(spec_json).read_text(encoding='utf-8'))
        out = self.root / 'commercials' / time.strftime('%Y%m%d_%H%M%S')
        hist = commercial.produce_and_review(spec['product'], spec['assets'], out, narration=spec.get('narration'), root=self.root)
        activity(self.root, 'Media Division', f'commercial reviewed: {hist[-1]["score"]["decision"]}', overall=hist[-1]['score']['overall_100'])
        return hist[-1], out

    # Video platform (Blotato / Google Flow / Adobe Firefly) + Blotato social publishing: Media Division agents
    def video_platform_status(self):
        import videoplatform as vp, commercial
        import sys
        dl = Path.home() / 'Downloads'
        cands = [Path(sys.executable).parent / 'blotato_api_key.txt', Path(__file__).parent / 'blotato_api_key.txt',
                 self.root / 'blotato_api_key.txt']
        for pat in ('ByrdWay_Owner_Starter_Pack*/blotato_api_key.txt', 'ByrdWay_Owner_Starter_Pack*/*/blotato_api_key.txt'):
            cands += sorted(dl.glob(pat)) if dl.is_dir() else []
        for kf in cands:
            try:
                if vp.import_key_file(kf):
                    activity(self.root, 'Social Publisher', 'Blotato key imported from the Starter Pack into the OS secret store; file deleted')
            except Exception:
                pass
        ref = assets.registry(self.root).get(vp.CHARACTER_ASSET_ID)
        return {'blotato_key': bool(vp.get_key()), 'platforms': vp.PLATFORMS, 'channels': vp.CHANNELS,
                'character_reference': bool(ref), 'approved_voice': bool(assets.registry(self.root).get(commercial.VOICE_ASSET_ID))}

    def set_blotato_key(self, key):
        import videoplatform as vp
        vp.store_key(key)
        activity(self.root, 'Social Publisher', 'Blotato API key stored in OS secret store (value not logged)')

    def blotato_accounts(self, client=None):
        import videoplatform as vp
        r = vp.platform_setup_check(client or vp.Blotato())
        activity(self.root, 'Social Publisher', 'Blotato accounts checked',
                 connected=[k for k, v in r.items() if v['connected']])
        return r

    def commercial_brief(self, spec_json, platform='blotato'):
        """Script & Storyboard: spec {product, lines, duration} -> brief JSON + shot list TXT (paste into Flow/Firefly)."""
        import videoplatform as vp, time
        spec = json.loads(Path(spec_json).read_text(encoding='utf-8'))
        b = vp.brief(spec['product'], spec['lines'], spec.get('duration', 30), platform)
        out = self.root / 'commercials' / ('brief_' + time.strftime('%Y%m%d_%H%M%S'))
        out.mkdir(parents=True, exist_ok=True)
        (out / 'BRIEF.json').write_text(json.dumps(b, indent=1), encoding='utf-8')
        (out / 'SHOT_LIST.txt').write_text(vp.brief_text(b), encoding='utf-8')
        activity(self.root, 'Script & Storyboard', f'commercial brief for {platform}: ready={b["ready"]}')
        return b, out

    def commercial_generate_blotato(self, brief_dir, owner_confirmed=False, kind='character', client=None, progress=None):
        """Video Producer: paid Blotato generation (owner confirmed) -> wait -> download -> Commercial Reviewer."""
        import videoplatform as vp
        brief_dir = Path(brief_dir)
        b = json.loads((brief_dir / 'BRIEF.json').read_text(encoding='utf-8'))
        c = client or vp.Blotato()
        ref = assets.get_asset(self.root, vp.CHARACTER_ASSET_ID)
        char_url = c.upload(ref['file']) if ref else None
        job = vp.produce_on_blotato(c, b, owner_confirmed, kind, char_url)
        activity(self.root, 'Video Producer', f'Blotato generation started {job["visual_id"]}', owner_confirmed=True)
        (brief_dir / 'GENERATION.json').write_text(json.dumps(job, indent=1), encoding='utf-8')
        res = c.wait_visual(job['visual_id'])
        (brief_dir / 'GENERATION.json').write_text(json.dumps(dict(job, result=res), indent=1), encoding='utf-8')
        if res.get('status') != 'done':
            return {'generation': res, 'decision': 'NOT DONE - nothing re-submitted (check Blotato before trying again)'}
        mp4 = vp.download(res['mediaUrl'], brief_dir / 'platform_render.mp4', getattr(c, 'http', None) if client else None)
        return self.commercial_review(brief_dir, mp4, ai_voice=True)

    def commercial_review(self, brief_dir, mp4, voice=None, ai_voice=False):
        """Commercial Reviewer on any platform render (Blotato, Google Flow, Firefly). With the owner's Lil Dr. Byrd
        recording, the generator's audio is replaced first (dub). Writes REVIEW.json; nothing is published."""
        import videoplatform as vp
        brief_dir = Path(brief_dir)
        b = json.loads((brief_dir / 'BRIEF.json').read_text(encoding='utf-8'))
        if voice:
            mp4 = vp.dub_with_voice(mp4, voice, brief_dir / 'commercial_owner_voice.mp4')
            ai_voice = False
        r = vp.review(mp4, b, self.root, ai_voice=ai_voice)
        rec = {'mp4': str(mp4), 'brief': str(brief_dir / 'BRIEF.json'), 'decision': r['score']['decision'],
               'overall_100': r['score'].get('overall_100'), 'scores': r['score'].get('scores'), 'review': r['review'],
               'voice_check': r['voice_check'], 'score': r['score']}
        (brief_dir / 'REVIEW.json').write_text(json.dumps(rec, indent=1, default=str), encoding='utf-8')
        activity(self.root, 'Commercial Reviewer', f'review: {rec["decision"]}', overall=rec['overall_100'])
        return rec

    def commercial_publish(self, brief_dir, platforms, owner, explicit=False, scheduled_time=None, client=None,
                           first_post_override=False):
        """Social Publisher via Blotato: only after Reviewer PASS and the owner's explicit approval."""
        import videoplatform as vp
        brief_dir = Path(brief_dir)
        rec = json.loads((brief_dir / 'REVIEW.json').read_text(encoding='utf-8'))
        b = json.loads((brief_dir / 'BRIEF.json').read_text(encoding='utf-8'))
        c = client or vp.Blotato()
        prev = json.loads((brief_dir / 'PUBLISH.json').read_text(encoding='utf-8'))['results'] if (brief_dir / 'PUBLISH.json').exists() else []
        out = vp.publish(c, rec['mp4'], b['product'], platforms,
                         {'owner': owner, 'explicit': explicit is True, 'qa_decision': rec['decision'],
                          'first_post_override': first_post_override is True,
                          'data_capped_only': rec['score'].get('data_capped_only', False)},
                         ai_generated=b['platform'] != 'owner_footage', scheduled_time=scheduled_time, previous=prev)
        (brief_dir / 'PUBLISH.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
        activity(self.root, 'Social Publisher', 'published via Blotato (owner approved)', approved_by=owner,
                 results=[(r['platform'], r['status']) for r in out['results']])
        return out

    # Powerhouse Command Center: every agent with its assignment, today's work and last action (all from real state)
    ENG_LOG_ROLES = {1: ('Reader', 'Inspection'), 2: ('Academic Verifier', 'Answer Verifier'), 3: ('Diagnostician',),
                     4: ('Power Tool Repair', 'Explainer Repair', 'Repair Engineer'), 5: ('Repair Reviewer',),
                     6: ('Release QA',), 7: ('Observer',), 8: ('Curriculum Architect',),
                     9: ('Power Tool Builder', 'Lil Dr. Byrd Builder', 'Concept Tiles Builder', 'Builder'),
                     10: ('Assembler',), 11: ('Build QA',), 12: ('Chief Judge',)}

    def command_center(self):
        import powerhouse, salesintel
        try:
            self.video_platform_status()                  # first run: picks up the Starter Pack Blotato key
        except Exception:
            pass
        org = powerhouse.organization()
        acts = read_activity(self.root, 2000)
        KW = {1: ('imported', 'baseline', 'pages read', 'read '), 2: ('verif', 'academic', 'answer'), 3: ('baseline', 'finding', 'diagnos'),
              4: ('repair', 'patch'), 5: ('review', 'accepted', 'rejected', 'send back'), 6: ('release qa', 'qa decision'),
              7: ('lesson',), 8: ('blueprint', 'table of contents', 'build plan'), 9: ('built', 'build unit'), 10: ('assembl',),
              11: ('build qa', 'mastery', 'conformance'), 12: ('chief judge', 'judge')}
        def last(names, aid=None):
            for a in reversed(acts):
                msg = str(a.get('message', '')).lower()
                if a.get('role') in names or (aid and any(k in msg for k in KW.get(aid, ()))):
                    return a
            return None
        prods, jobs, builds, lessons = self.products(), self.jobs(), self.builds(), self.lessons()
        st = lambda j: str(j.get('status', ''))
        waiting = [j for j in jobs if 'AWAITING' in st(j) or 'READY' in st(j)]
        failing = [j for j in jobs if 'FAIL' in st(j) or 'BLOCKED' in st(j)]
        diag = {d.parent.name for d in (self.root / 'reports').glob('diag_*/diagnosis.json')} | {j.get('product_id') for j in jobs}
        units_open = sum(1 for b in builds for u in (b.get('units') or []) if 'APPROVED' not in str(u.get('status', '') if isinstance(u, dict) else u).upper())
        today_eng = {
            1: f'{len(prods)} product(s) protected; {max(len(prods) - len(diag), 0)} not yet read end to end',
            2: f'{len(prods)} product(s) to recompute; every answer, step and unit re-verified independently',
            3: f'{len(diag)} product(s) diagnosed; defect register per product',
            4: f'{len(failing)} job(s) sent back for repair' if failing else 'no repair waiting',
            5: f'{len(jobs)} repair job(s) on record; every fix re-read before QA',
            6: f'{len(waiting)} job(s) at QA PASS waiting for your approval' if waiting else 'no release waiting',
            7: f'{len(lessons)} lesson(s) the builders must obey',
            8: f'{len(builds)} build plan(s) from approved tables of contents',
            9: f'{units_open} unit(s) open across {len(builds)} build(s)',
            10: f'{sum(1 for b in builds if b.get("assembled"))} product(s) assembled',
            11: '9-point Mastery standard + Reader lessons checked on every unit',
            12: '100 % of mandatory checks or the unit goes back',
        }
        eng = []
        for group, agents in org['engineering'].items():
            for a in agents:
                la = last(self.ENG_LOG_ROLES.get(a['id'], (a['name'],)) + (a['name'],), a['id'])
                eng.append(dict(a, group=group, today=today_eng.get(a['id'], ''),
                                last=(f"{la['ts'][:16].replace('T', ' ')}  {la['message']}" if la else 'no action yet')))
        rd = None
        try:
            import roadmap
            dash = salesintel.dashboard(self.root)
            ss = salesintel.settings(self.root)
            cat = ss.get('catalog', [])
            rd = roadmap.assess({'weekly_units': [w['units'] for w in dash['weeks'] if w['status'] != 'IN PROGRESS'],
                                 'team_size': ss.get('team_size', 1), 'products_listed': len(cat),
                                 'products_qa_pass': len(salesintel.marketable(cat)), 'reviews': ss.get('store_reviews'),
                                 'channel_weeks_with_sales': ss.get('channel_weeks_with_sales', 0)})
        except Exception:
            dash = {'weeks': [], 'units_total': 0, 'net_total': 0, 'real_rows': 0}
        actions = (rd or {}).get('plan', {}).get('actions', [])
        rev = []
        for (k, name, job, _m), r in zip(salesintel.ROLES, org['revenue']):
            mine = [a['action'] for a in actions if a['role'] == k]
            la = last((name, {'video_producer': 'Video Producer', 'social_publisher': 'Social Publisher',
                              'script_storyboard': 'Script & Storyboard'}.get(k, name), 'Commercial Reviewer' if k == 'video_producer' else name))
            rev.append({'key': k, 'name': name, 'job': r['job'], 'status': r['status'], 'methods': r['methods'],
                        'today': mine[0] if mine else 'standing by for today\'s workflow',
                        'last': f"{la['ts'][:16].replace('T', ' ')}  {la['message']}" if la else 'no action yet'})
        cur = next((w for w in reversed(dash['weeks']) if w), None) if dash['weeks'] else None
        posts = sum(1 for a in acts if a.get('role') == 'Social Publisher' and 'published' in a.get('message', ''))
        kpis = [('Products protected', len(prods)), ('Repair jobs', len(jobs)), ('Awaiting your approval', len(waiting)),
                ('Lessons learned', len(lessons)), ('Builds in progress', len(builds)),
                ('Paid units this week', f"{cur['units'] if cur else 0} / {cur['minimum'] if cur else 125}"),
                ('Net revenue (imported)', f"${dash.get('net_total', 0)}"), ('Posts published', posts)]
        return {'kpis': kpis, 'engineering': eng, 'revenue': rev, 'feed': acts[-60:][::-1],
                'stage': (rd or {}).get('diagnosis'), 'bottleneck': (rd or {}).get('bottleneck'),
                'targets': org['sales_targets'], 'quality': org['quality_target']}

    def revenue_role(self, key):
        """Run one Revenue & Media agent's real work for today and return its deliverables."""
        import salesintel
        rep, out = salesintel.run_daily(self.root)
        ss = salesintel.settings(self.root)
        acts = [a for a in rep['roadmap']['daily_plan']['actions'] if a['role'] == key]
        res = {'assignment': acts, 'stage': rep['roadmap']['stage'], 'bottleneck': rep['roadmap']['bottleneck']}
        if key == 'offer_pricing':
            res['deliverables'] = out['offers']
        elif key == 'prospector':
            res['deliverables'] = salesintel.rank_prospects(ss.get('prospects', []))
        elif key == 'script_storyboard':
            res['deliverables'] = out['media']
        elif key == 'sales_followup':
            res['deliverables'] = out['followups']
        elif key == 'retention':
            res['deliverables'] = out['retention']
        elif key == 'revenue_tracker':
            res['deliverables'] = salesintel.dashboard(self.root)
        elif key == 'sales_qa':
            res['deliverables'] = rep['sales_qa']
        elif key in ('video_producer', 'social_publisher'):
            recs = []
            for d in sorted((self.root / 'commercials').glob('brief_*'))[-10:]:
                r = {'folder': str(d)}
                for f in ('REVIEW.json', 'PUBLISH.json'):
                    if (d / f).exists():
                        j = json.loads((d / f).read_text(encoding='utf-8'))
                        r[f[:-5].lower()] = j.get('decision') or [(x['platform'], x['status']) for x in j.get('results', [])]
                recs.append(r)
            res['deliverables'] = {'commercials': recs, 'platform': self.video_platform_status()}
        else:
            res['deliverables'] = {'methods': [m for m in salesintel.library()['methods'] if 'market_research' in m.get('roles', [])][:6]}
        activity(self.root, dict((k, n) for k, n, *_ in salesintel.ROLES)[key], 'ran today\'s assignment from the Command Center')
        return res

    # Revenue & Media Division (drafts and measurement only: nothing is sent, published, priced or paid)
    def sales_daily(self):
        import salesintel
        return salesintel.run_daily(self.root)

    def sales_dashboard(self):
        import salesintel
        return salesintel.dashboard(self.root)

    def sales_import_csv(self, path):
        import salesintel
        return salesintel.import_sales_csv(self.root, path)

    def sales_settings(self):
        import salesintel
        return salesintel.settings(self.root)

    def sales_save_settings(self, s):
        import salesintel
        return salesintel.save_settings(self.root, s)

    def sales_library(self):
        import salesintel
        return salesintel.library()

    def approve_unit(self, build_id, unit, explicit=False, attest_unsupported=False, note=''):
        return builders.Build(self.root, build_id).approve(unit, explicit, attest_unsupported, note)

    def assemble_and_import(self, build_id, explicit=False):
        out = builders.assemble(self.root, build_id, explicit)
        return self.import_product(out)

    def register_asset(self, path, asset_id, kind, note='', explicit=False):
        return assets.register_asset(self.root, path, asset_id, kind, note, explicit)

    def asset_registry(self):
        return assets.registry(self.root)

    # costs / settings
    def settings(self):
        return load_settings(self.root)

    def save_settings(self, s):
        save_settings(self.root, s)
        activity(self.root, 'Orchestrator', 'Settings updated')

    def cost_summary(self):
        return Ledger(self.root).summary(load_settings(self.root))

    def ledger(self):
        return Ledger(self.root).entries()

    def api_key_configured(self):
        return bool(get_api_key())

    def set_api_key(self, key):
        store_api_key(key)
        activity(self.root, 'Orchestrator', 'API key stored in OS secret store (value not logged)')

    # backup / logs
    def backup(self, dest=None):
        return release.backup_workspace(self.root, dest)

    def restore(self, backup_zip, confirm=False):
        return release.restore_backup(backup_zip, self.root, confirm)

    def activity(self, limit=300):
        return read_activity(self.root, limit)


def next_action(job):
    """One plain-English instruction for the owner, derived only from recorded job state."""
    qa = job.get('qa') or {}
    st = job.get('status')
    if st == 'ERROR':
        return f'Job crashed ({job.get("error")}). Send logs\\activity.jsonl to your developer.'
    if st == 'EXPORTED':
        return f'Done. Exported to {job.get("export", {}).get("dir")}. Upload to TpT yourself when ready.'
    if st == 'APPROVED':
        return 'Approved. Click "Export Approved…" to save the final product with its audit trail.'
    if st == 'REJECTED':
        return 'Rejected by owner. Nothing will be exported.'
    if st == 'AWAITING_OWNER_APPROVAL':
        extra = ' Check the before/after page images first (Open Evidence Folder).' if any(
            h.get('replace_file') for h in job.get('history', [])) else ''
        return (f'Release QA PASSED ({qa.get("score")}/100). Review "Before / After Diff", then click '
                f'"APPROVE for release…".{extra}')
    pend = [u for u in qa.get('unverified_items') or [] if isinstance(u, dict) and u.get('status') == 'PENDING_OWNER_DECISION']
    if pend:
        n = len(pend)
        return (f'The page reader found {n} possible error(s) on image pages. Click "Review Image Findings…" '
                f'and confirm or dismiss each one (a picture of each is shown).')
    if st == 'BLOCKED' and any(f.get('image_item') and f.get('decision') == 'confirmed'
                               for f in qa.get('image_findings') or []):
        return ('You confirmed error(s) on image pages. Best: click "Export Correction Sheet…" and correct them in '
                'your editable source (Canva/PPTX), then import the new PDF. Or click "Repair Confirmed on a Copy…" '
                'to have the Studio draw the corrections on a protected copy (checked by the Repair Reviewer and '
                'Release QA; you approve each corrected spot).')
    if st == 'NOT_VERIFIED':
        if qa.get('unverified_items'):
            return (f'{len(qa["unverified_items"])} question(s) cannot be checked automatically. Review them '
                    f'yourself, then use "Attest Unverifiable Item…" (or ALL).')
        miss = qa.get('missing_required_categories') or []
        if 'browser_runtime' in miss:
            return 'Browser tests could not run: use Help → Install browser engine (one-time download), then Re-run Release QA.'
        if 'academic' in miss:
            return ('No answers could be read automatically (image-only pages or an unknown answer format). '
                    'Check the content yourself and attest ALL, or send the product to your developer.')
        return 'Coverage incomplete: ' + '; '.join(qa.get('reasons', []))
    if st == 'BLOCKED':
        first = (qa.get('reasons') or ['see report'])[0]
        return f'Release BLOCKED by a defect that needs a person: {first}'
    if st == 'BELOW_TARGET':
        return 'Minor issues keep the score under 99.9. See failed checks below; fix in source or re-run.'
    return f'Status {st}.'
