"""ByrdWay Product Engineering Studio - Windows desktop UI (Python standard library Tk).

Run: python app.py   (or double-click START_WINDOWS.bat)
All logic lives in controller.Studio; this file is presentation only.
Long operations run on a worker thread; owner decisions (API spend, approval)
are always modal dialogs on the UI thread.
"""
import gc, json, os, queue, subprocess, sys, threading, traceback

if __name__ == '__main__' and '--version' in sys.argv:
    from version import __version__
    print(__version__)
    sys.exit(0)

if __name__ == '__main__' and '--install-browser' in sys.argv:
    from browsertest import install_chromium
    ok, msg = install_chromium()
    print(msg)
    sys.exit(0 if ok else 1)

if __name__ == '__main__' and '--selftest' in sys.argv:      # headless: no GUI libraries needed
    import selftest
    sys.exit(selftest.main())

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path

from controller import Studio, next_action
from engine import ROLES, save_proposal, original_file
from ai_roles import run_review, ROLE_PROMPTS

from version import __version__, APP_NAME
APP_TITLE = f'{APP_NAME} | v{__version__}'
ROOT = Path(os.environ.get('BYRDWAY_WORKSPACE') or (Path.home() / 'Documents' / 'ByrdWay_Product_Studio'))


def open_path(p):
    p = str(p)
    if sys.platform == 'win32':
        os.startfile(p)  # noqa
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', p])
    else:
        subprocess.Popen(['xdg-open', p])


class App(tk.Tk):
    def __init__(self, root=ROOT):
        super().__init__()
        self.studio = Studio(root)
        self.title(APP_TITLE)
        self.geometry('1180x760')
        self.minsize(900, 600)
        self.q = queue.Queue()
        self.busy = False
        self.opener = open_path          # tests replace this to avoid launching external programs
        self._menu()
        style = ttk.Style(self)
        try:
            style.theme_use('vista' if sys.platform == 'win32' else 'clam')
        except tk.TclError:
            pass
        top = ttk.Frame(self, padding=(12, 10))
        top.pack(fill='x')
        ttk.Label(top, text='BYRDWAY PRODUCT ENGINEERING STUDIO', font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        ttk.Label(top, text='BYRD POWERHOUSE: 12 engineering agents • Protected originals • Independent verification • '
                            'Owner approval • Nothing is ever published automatically').pack(anchor='w')
        self.status = tk.StringVar(value='Ready.')
        ttk.Label(self, textvariable=self.status, relief='sunken', anchor='w', padding=4).pack(side='bottom', fill='x')
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill='both', expand=True, padx=8, pady=4)
        self._products_tab()
        self._jobs_tab()
        self._builders_tab()
        self._costs_tab()
        self._backup_tab()
        self._logs_tab()
        self._powerhouse_tab()
        self._revenue_tab()
        self._poll_id = self.after(150, self._poll)
        self.refresh_all()

    def _menu(self):
        mb = tk.Menu(self)
        h = tk.Menu(mb, tearoff=0)
        h.add_command(label='Quick Start (open guide)', command=lambda: self.opener(Path(__file__).with_name('OWNER_QUICK_START.md')))
        h.add_command(label='Install browser engine (one-time, ~150 MB download)…', command=self.install_browser)
        h.add_command(label='Run self-test (checks this PC)', command=self.run_selftest)
        h.add_command(label='About / version', command=lambda: messagebox.showinfo(
            'About', f'{APP_TITLE}\nWorkspace: {self.studio.root}\nNothing is ever published automatically.'))
        mb.add_cascade(label='Help', menu=h)
        self.config(menu=mb)

    def install_browser(self):
        if not messagebox.askyesno('Install browser engine',
                                   'Power Tool interaction tests need the Chromium browser engine (about 150 MB, '
                                   'downloaded once from Microsoft\'s Playwright servers). Download it now?'):
            return
        from browsertest import install_chromium
        def done(r):
            (messagebox.showinfo if r[0] else messagebox.showerror)('Browser engine', r[1])
            self.log_line(('Browser engine: ' if r[0] else 'Browser engine NOT installed: ') + r[1])
        self.run_bg('Installing browser engine', install_chromium, done)

    def run_selftest(self):
        import selftest
        def done(r):
            bad = [c for c in r['checks'] if not c['passed']]
            (messagebox.showinfo if not bad else messagebox.showerror)(
                'Self-test', f'Self-test {"PASSED" if not bad else "FAILED"} ({len(r["checks"]) - len(bad)}/'
                             f'{len(r["checks"])} checks, version {r["version"]}).' +
                             ''.join(f'\n✖ {c["check"]}: {c["detail"]}' for c in bad))
        self.run_bg('Self-test', lambda: selftest.run(self.studio.root / 'reports' / 'selftest_report.json'), done)

    def error(self, title, e):
        """Show an understandable error and record it in the activity log."""
        from joblog import activity
        try:
            activity(self.studio.root, 'UI', f'{title}: {e}', level='ERROR')
        except Exception:
            pass
        self.log_line(f'{title}: {e}')
        messagebox.showerror(title, f'{e}\n\n(Recorded in tab 6, Activity & Error Log.)')

    # ---------------------------------------------------------------- helpers
    def run_bg(self, label, fn, done=None):
        if self.busy:
            messagebox.showinfo('Busy', 'Another operation is running. Please wait.')
            return
        self.busy = True
        self.status.set(label + ' ...')
        # Collect Tk garbage on the UI thread NOW. If Python's garbage collector later ran on the worker
        # thread and freed Tk variables (e.g. from a closed editor window), Tk would abort the program.
        gc.collect()

        def work():
            try:
                res = fn()
                self.q.put(('done', label, res, done))
            except Exception as e:
                self.q.put(('error', label, e, traceback.format_exc()))
        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        try:
            while True:
                kind, label, a, b = self.q.get_nowait()
                if kind == 'progress':
                    self.status.set(a)
                    self.log_line(a)
                    continue
                if kind == 'call':
                    a()
                    continue
                self.busy = False
                self.refresh_all()          # refresh FIRST so the completion step acts on the current screen
                if kind == 'done':
                    self.status.set(label + ': done')
                    if b:
                        b(a)
                else:
                    self.status.set(label + ': FAILED')
                    self.error(f'{label} failed', a)
        except queue.Empty:
            pass
        if not getattr(self, '_closing', False):
            self._poll_id = self.after(150, self._poll)

    def destroy(self):
        self._closing = True
        try:
            self.after_cancel(self._poll_id)
        except Exception:
            pass
        super().destroy()
        gc.collect()

    def on_ui(self, fn):
        """Run fn on the UI thread and wait for its result (used for spend approval)."""
        box, ev = {}, threading.Event()

        def call():
            try:
                box['r'] = fn()
            finally:
                ev.set()
        self.q.put(('call', None, call, None))
        ev.wait()
        return box.get('r')

    def approver(self, info):
        def ask():
            return messagebox.askyesno(
                'Approve paid OpenAI call?',
                f'Role: {info["role"]}\nModel: {info["model"]}\nEstimated maximum cost: ${info["estimate_usd"]:.4f}\n'
                f'(≈{info["input_chars"]} characters sent, ≤{info["max_output_tokens"]} output tokens)\n\n'
                'Product text will be sent to OpenAI. Approve this ONE call?')
        return self.on_ui(ask) is True

    def log_line(self, s):
        self.logbox.insert('end', s + '\n')
        self.logbox.see('end')

    def refresh_all(self):
        for f in (self.refresh_products, self.refresh_jobs, self.refresh_builds, self.refresh_costs, self.refresh_logs):
            try:
                f()
            except Exception as e:
                self.status.set(f'Refresh error: {e}')

    @staticmethod
    def _tree(parent, cols, widths):
        t = ttk.Treeview(parent, columns=cols, show='headings', selectmode='browse', height=10)
        for c, w in zip(cols, widths):
            t.heading(c, text=c)
            t.column(c, width=w, anchor='w')
        return t

    # --------------------------------------------------------------- products
    def _products_tab(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text='1. Products')
        ttk.Label(f, text='Workflow:  ① Import  →  ② Diagnose (changes nothing)  →  read the report  →  '
                          '③ Repair a Copy & Verify  →  tab 2: Approve  →  Export', font=('Segoe UI', 10, 'bold'),
                  foreground='#0b3d91').pack(anchor='w', pady=(0, 6))
        bar = ttk.Frame(f)
        bar.pack(fill='x')
        self.ai_var = tk.BooleanVar(value=False)
        for text, cmd in [('① Import Product…', self.import_one), ('② Diagnose (no changes)', self.diagnose),
                          ('③ Repair a Copy & Verify', self.run_job), ('Open Latest Report', self.open_latest_report)]:
            ttk.Button(bar, text=text, command=cmd).pack(side='left', padx=2)
        more = ttk.Menubutton(bar, text='More tools ▾')
        m = tk.Menu(more, tearoff=0)
        for text, cmd in [('Local text audit', self.audit), ('AI read-only review (paid, asks first)…', self.ai_review),
                          ('Manual text proposal (single HTML/JS/CSS file)…', self.proposal),
                          ('Verify originals are unchanged', self.verify_originals),
                          ('Open workspace folder', lambda: self.opener(self.studio.root))]:
            m.add_command(label=text, command=cmd)
        more['menu'] = m
        more.pack(side='left', padx=8)
        ttk.Checkbutton(bar, text='Allow AI suggestions when automatic fixes run out (asks before every paid call)',
                        variable=self.ai_var).pack(side='left', padx=8)
        self.ptree = self._tree(f, ('id', 'name', 'type', 'imported', 'sha256', 'integrity'), (110, 300, 170, 150, 200, 110))
        self.ptree.pack(fill='both', expand=True, pady=6)
        ttk.Label(f, text='Activity:').pack(anchor='w')
        self.logbox = tk.Text(f, height=8, wrap='word', font=('Consolas', 9))
        self.logbox.pack(fill='x')
        self.log_line('Ready. Import a Power Tool (HTML/ZIP) or Explainer (PDF). Originals are copied and locked; '
                      'all repairs happen on copies. Help menu → Quick Start.')

    def refresh_products(self):
        sel = self.ptree.selection()
        self.ptree.delete(*self.ptree.get_children())
        for p in self.studio.products():
            self.ptree.insert('', 'end', iid=p['id'], values=(p['id'], p['name'], p.get('product_type', ''),
                                                              p.get('imported_at', ''), p.get('sha256', '')[:16] + '…',
                                                              p.get('integrity', '')))
        if sel and self.ptree.exists(sel[0]):
            self.ptree.selection_set(sel[0])

    def selected_pid(self):
        s = self.ptree.selection()
        if not s:
            raise ValueError('Select a product in the list first (click its row).')
        return s[0]

    def import_one(self):
        f = filedialog.askopenfilename(title='Choose a product to import (a copy is made; your file is not changed)',
                                       filetypes=[('ByrdWay products', '*.zip *.html *.htm *.pdf'),
                                                  ('Other text sources', '*.js *.css *.txt *.md *.json')])
        if f:
            try:
                m = self.studio.import_product(f)
                self.log_line(f'IMPORTED {m["name"]} as {m["product_type"]} SHA-256 {m["sha256"]}')
                self.refresh_products()
                self.ptree.selection_set(m['id'])
                self.status.set(f'Imported {m["name"]}. Next: ② Diagnose.')
            except Exception as e:
                self.error('Import blocked', e)

    def diagnose(self):
        try:
            pid = self.selected_pid()
        except ValueError as e:
            return messagebox.showinfo('Select a product', str(e))

        def done(d):
            self.log_line(f'DIAGNOSIS {d["product_name"]}: {len(d["findings"])} findings, '
                          f'{d["proposed_corrections"]} correctable automatically, {d["needs_person"]} need a person.')
            self.opener(self.studio.root / 'reports' / d['id'] / 'diagnosis.html')
        self.run_bg('Diagnose', lambda: self.studio.diagnose(pid, progress=self.progress), done)

    def progress(self, m):
        self.q.put(('progress', None, m, None))

    def run_job(self, done_extra=None):
        try:
            pid = self.selected_pid()
        except ValueError as e:
            return messagebox.showinfo('Select a product', str(e))
        if not messagebox.askyesno('Repair a copy', 'Apply the proposed corrections to a COPY of this product, then '
                                   're-test it independently?\n\nYour original is never changed and nothing is '
                                   'released until you approve it in tab 2.'):
            return
        ai = self.ai_var.get()

        def done(job):
            qa = job.get('qa') or {}
            self.log_line(f'JOB {job["id"]}: {job["status"]} (QA {qa.get("decision")}, score {qa.get("score")})')
            self.nb.select(1)
            self.refresh_jobs()
            if self.jtree.exists(job['id']):
                self.jtree.selection_set(job['id'])
                self.show_job()
            rep = self.studio.job_evidence_dir(job['id']) / 'report.html'
            if rep.exists():
                self.opener(rep)
            done_extra and done_extra(job)
        from engine import utcnow
        auth = {'by': os.environ.get('USERNAME') or os.environ.get('USER') or 'owner',
                'method': 'owner confirmed "Repair a copy" dialog', 'at': utcnow()}
        self.run_bg('Repair & verify', lambda: self.studio.run_job(pid, ai_enabled=ai, approver=self.approver,
                                                                  authorization=auth,
                                                                  progress=self.progress), done)

    def open_latest_report(self):
        try:
            pid = self.selected_pid()
        except ValueError as e:
            return messagebox.showinfo('Select a product', str(e))
        p = self.studio.latest_report(pid)
        if p:
            self.opener(p)
        else:
            messagebox.showinfo('No report yet', 'No report for this product yet. Click ② Diagnose first.')

    def audit(self):
        try:
            r = self.studio.local_audit(self.selected_pid())
            self.log_line('LOCAL AUDIT ' + json.dumps(r)[:1500])
        except Exception as e:
            messagebox.showerror('Audit blocked', str(e))

    def ai_review(self):
        try:
            pid = self.selected_pid()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        role = simpledialog.askstring('Specialist role', 'Enter one of:\n' + '\n'.join(ROLE_PROMPTS))
        if not role:
            return

        def go():
            text = run_review(self.studio.root, pid, role.strip(), approver=self.approver)
            out = self.studio.root / 'reports' / f'{pid}_{role.strip().replace(" ", "_")}.txt'
            out.write_text(text, encoding='utf-8')
            return text, out
        self.run_bg('AI review', go, lambda r: self.log_line(r[0] + f'\nSaved (advice only, not verified): {r[1]}'))

    def proposal(self):
        try:
            pid = self.selected_pid()
            src, _ = original_file(self.studio.root, pid)
            if src.suffix.lower() not in {'.html', '.htm', '.js', '.css', '.txt', '.md', '.json'}:
                raise ValueError('Manual editor is for single text files. Use "Run Repair & Verify Job" for ZIP/PDF.')
        except Exception as e:
            return messagebox.showerror('Proposal blocked', str(e))
        ed = tk.Toplevel(self)
        ed.title('Manual proposal: the original is never overwritten')
        ed.geometry('900x600')
        t = tk.Text(ed, wrap='none')
        t.pack(fill='both', expand=True)
        t.insert('1.0', src.read_text(encoding='utf-8', errors='replace'))

        def save():
            reason = simpledialog.askstring('Change reason', 'What verified defect is being corrected?', parent=ed)
            if not reason:
                return
            rec = save_proposal(self.studio.root, pid, t.get('1.0', 'end-1c'), reason)
            self.log_line('PROPOSAL SAVED (NOT RELEASED, not QA-tested): ' + rec['candidate'])
            ed.destroy()
        ttk.Button(ed, text='Save proposed copy (not published)', command=save).pack(pady=5)

    def verify_originals(self):
        r = self.studio.verify_all_originals()
        bad = [k for k, v in r.items() if not v]
        messagebox.showinfo('Originals', f'{len(r) - len(bad)} of {len(r)} originals match their SHA-256 fingerprint.'
                                         + (f'\nMISMATCH: {bad}' if bad else ''))
        self.refresh_products()

    # -------------------------------------------------------------------- jobs
    def _jobs_tab(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text='2. Jobs, QA & Approval')
        bar = ttk.Frame(f)
        bar.pack(fill='x')
        for text, cmd in [('Open Readable Report', self.open_job_report), ('Before / After Diff', self.show_diff), ('Open Evidence Folder', self.open_evidence),
                          ('Re-run Release QA', self.rerun_qa), ('Review Image Findings…', self.review_image_findings),
                          ('Repair Confirmed on a Copy…', self.repair_confirmed),
                          ('Export Correction Sheet…', self.export_correction_sheet),
                          ('Attest Unverifiable Item…', self.attest),
                          ('APPROVE for release…', self.approve), ('Reject…', self.reject),
                          ('Export Approved…', self.export)]:
            ttk.Button(bar, text=text, command=cmd).pack(side='left', padx=2)
        pane = ttk.PanedWindow(f, orient='vertical')
        pane.pack(fill='both', expand=True, pady=6)
        self.jtree = self._tree(pane, ('job', 'product', 'status', 'QA decision', 'score', 'stop reason'),
                                (190, 260, 190, 120, 70, 230))
        self.jtree.bind('<<TreeviewSelect>>', lambda e: self.show_job())
        pane.add(self.jtree, weight=1)
        self.jtext = tk.Text(pane, wrap='word', font=('Consolas', 9))
        pane.add(self.jtext, weight=2)

    def refresh_jobs(self):
        sel = self.jtree.selection()
        self.jtree.delete(*self.jtree.get_children())
        for j in self.studio.jobs():
            qa = j.get('qa') or {}
            self.jtree.insert('', 'end', iid=j['id'], values=(j['id'], j['product_name'], j['status'],
                                                              qa.get('decision', ''), qa.get('score', ''),
                                                              j.get('stop_reason') or ''))
        if sel and self.jtree.exists(sel[0]):
            self.jtree.selection_set(sel[0])

    def selected_job(self):
        s = self.jtree.selection()
        if not s:
            raise ValueError('Select a job first')
        return s[0]

    def show_job(self):
        try:
            jid = self.selected_job()
        except ValueError:
            return
        j = self.studio.job(jid)
        qa = j.get('qa') or {}
        lines = ['NEXT STEP: ' + next_action(j), '', self.studio.job_report(jid), '', '=== Release QA checks ===']
        for c in qa.get('checks', []):
            mark = {True: 'PASS', False: 'FAIL', None: 'NOT RUN'}[c[3]]
            lines.append(f'[{mark:7}] {c[2]:8} {c[0]}  {c[4]}')
        if qa.get('unverified_items'):
            lines += ['', '=== Items needing owner attestation (copy the key) ===']
            lines += [f'{u["key"]}  ->  {u["status"]}: {u["evidence"]}' for u in qa['unverified_items']]
        self.jtext.delete('1.0', 'end')
        self.jtext.insert('1.0', '\n'.join(lines))
        color = {'AWAITING_OWNER_APPROVAL': '#e6f4ea', 'APPROVED': '#e6f4ea', 'EXPORTED': '#e6f4ea',
                 'BLOCKED': '#fde8e8', 'ERROR': '#fde8e8'}.get(j['status'], '#fff8e1')
        self.jtext.tag_configure('next', background=color, font=('Segoe UI', 11, 'bold'))
        self.jtext.tag_add('next', '1.0', '1.end')

    def review_image_findings(self):
        try:
            jid = self.selected_job()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        items = self.studio.image_findings(jid)
        if not items:
            return messagebox.showinfo('Image findings', 'The page reader found no possible errors on image pages '
                                                         'in this job (or the product has no image pages).')
        self.image_dialog = ImageFindingsDialog(self, jid, items)
        return self.image_dialog

    def repair_confirmed(self, done=None):
        try:
            jid = self.selected_job()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        if not any(i['decision'] == 'confirmed' for i in self.studio.image_findings(jid)):
            return messagebox.showinfo('Repair', 'Confirm at least one finding in "Review Image Findings…" first.')
        owner = simpledialog.askstring('Repair on a copy', 'Your name (authorizes this repair):')
        if not owner:
            return
        if not messagebox.askyesno('Authorize repair', 'Correct the CONFIRMED findings on a protected COPY?\n\n'
                                   'Your original file is never changed. Each correction is drawn over the picture '
                                   '(Helvetica - the original font cannot be reproduced without the editable source), '
                                   'checked by an independent Repair Reviewer and by Release QA. You review every '
                                   'corrected spot before approving.'):
            return

        def finished(j):
            self.refresh_jobs()
            if self.jtree.exists(j['id']):
                self.jtree.selection_set(j['id'])
                self.show_job()
            rv = j.get('repair_reviews') or []
            self.log_line(f'Repair job {j["id"]}: {sum(1 for r in rv if r["accepted"])} corrected, '
                          f'{sum(1 for r in rv if not r["accepted"])} blocked; QA {j.get("qa", {}).get("decision")}')
            done and done(j)
        self.run_bg('Repairing confirmed findings on a copy',
                    lambda: self.studio.repair_image_findings(jid, owner, True, progress=self.progress), finished)

    def export_correction_sheet(self):
        try:
            jid = self.selected_job()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        if not any(i['decision'] == 'confirmed' for i in self.studio.image_findings(jid)):
            return messagebox.showinfo('Correction sheet', 'Confirm at least one finding in "Review Image Findings…" first.')
        owner = simpledialog.askstring('Correction sheet', 'Your name (approves these corrections):')
        if not owner:
            return
        if not messagebox.askyesno('Approve corrections', 'Export the confirmed corrections as a correction sheet and '
                                   'an annotated review copy?\n\nYour product file is NOT changed; you make the '
                                   'corrections in your editable source.'):
            return
        try:
            out = self.studio.export_correction_sheet(jid, owner, True)
            self.log_line(f'Correction sheet exported: {out}')
            self.opener(out / 'correction_sheet.html')
        except Exception as e:
            self.error('Correction sheet not exported', e)

    def open_job_report(self):
        try:
            jid = self.selected_job()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        p = self.studio.job_html_report(jid)
        if p:
            self.opener(p)
        else:
            messagebox.showinfo('Report', 'This job has no report (it may have failed). See tab 6 for details.')

    def show_diff(self):
        try:
            jid = self.selected_job()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        w = tk.Toplevel(self)
        w.title(f'Before / After changes - job {jid}')
        w.geometry('1000x650')
        t = tk.Text(w, wrap='none', font=('Consolas', 10))
        t.pack(fill='both', expand=True)
        t.tag_configure('add', foreground='#116611')
        t.tag_configure('del', foreground='#aa1111')
        diff = self.studio.job_diff(jid) or '(no changes)'
        for line in diff.splitlines():
            tag = 'add' if line.startswith('+') and not line.startswith('+++') else (
                'del' if line.startswith('-') and not line.startswith('---') else '')
            t.insert('end', line + '\n', tag)
        ttk.Label(w, text='Screenshots and page renders: use "Open Evidence Folder" (evidence/ and qa/visual*).').pack()

    def open_evidence(self):
        try:
            self.opener(self.studio.job_evidence_dir(self.selected_job()))
        except Exception as e:
            messagebox.showinfo('Evidence', str(e))

    def rerun_qa(self):
        try:
            jid = self.selected_job()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        self.run_bg('Release QA', lambda: self.studio.rerun_qa(jid), lambda j: self.show_job())

    def attest(self):
        try:
            jid = self.selected_job()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        key = simpledialog.askstring('Attestation', 'Item key to attest (from the list), or ALL:')
        if not key:
            return
        owner = simpledialog.askstring('Attestation', 'Your name:')
        note = simpledialog.askstring('Attestation', 'What did you personally check?')
        if owner and note:
            self.run_bg('Attestation', lambda: self.studio.attest(jid, key.strip(), owner, note), lambda j: self.show_job())

    def approve(self):
        try:
            jid = self.selected_job()
            j = self.studio.job(jid)
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        qa = j.get('qa') or {}
        if qa.get('decision') != 'PASS':
            return messagebox.showerror('Release blocked',
                                        f'Release QA decision is {qa.get("decision")}. Approval is not possible.\n\n'
                                        + '\n'.join(qa.get('reasons', [])[:12]))
        owner = simpledialog.askstring('Owner approval', 'Type your full name to approve this candidate:')
        if not owner:
            return
        visual = False
        if any(h.get('replace_file') for h in j.get('history', [])):
            visual = messagebox.askyesno('Visual review', 'This candidate contains reconstructed PDF regions.\n'
                                         'Have you personally reviewed the before/after page images?')
            if not visual:
                return messagebox.showinfo('Review the pages first',
                                           'Open the Readable Report (or Evidence Folder) and compare the BEFORE and '
                                           'AFTER page images of the corrected pages, then approve again.')
        if not messagebox.askyesno('Confirm approval', f'Approve candidate {Path(j["candidate"]).name}\n'
                                   f'QA score {qa.get("score")}\nfor export? (Nothing is published.)'):
            return
        try:
            self.studio.approve(jid, owner, True, visual)
            self.log_line(f'APPROVED {jid} by {owner}')
        except Exception as e:
            messagebox.showerror('Approval refused', str(e))
        self.refresh_jobs()

    def reject(self):
        try:
            jid = self.selected_job()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        reason = simpledialog.askstring('Reject', 'Reason for rejection:')
        if reason:
            self.studio.reject(jid, os.environ.get('USERNAME', 'owner'), reason)
            self.refresh_jobs()

    def export(self):
        try:
            jid = self.selected_job()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        dest = filedialog.askdirectory(title='Choose export folder (Cancel = workspace exports/)')
        try:
            out = self.studio.export(jid, Path(dest) / jid if dest else None)
            messagebox.showinfo('Exported', f'Exported with audit trail and SHA256SUMS to:\n{out}\n\nNothing was uploaded.')
            self.opener(out)
        except Exception as e:
            messagebox.showerror('Export refused', str(e))
        self.refresh_jobs()

    # ---------------------------------------------------------------- builders
    def _builders_tab(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text='3. New Product Builders')
        s1 = ttk.LabelFrame(f, text='Step 1 — What are you building?', padding=6)
        s1.pack(fill='x')
        self.kind_var = tk.StringVar(value='power_tool')
        ttk.Radiobutton(s1, text='Interactive Power Tool (HTML)', value='power_tool', variable=self.kind_var,
                        command=self.refresh_prereqs).pack(side='left', padx=6)
        ttk.Radiobutton(s1, text='Lil Dr. Byrd Explainer (print PDF)', value='lil_dr_byrd', variable=self.kind_var,
                        command=self.refresh_prereqs).pack(side='left', padx=6)
        s2 = ttk.LabelFrame(f, text='Step 2 — Content plan ("blueprint"): type your approved content into a form', padding=6)
        s2.pack(fill='x', pady=4)
        for text, cmd in [('Create new blueprint (form)…', self.bp_new), ('Open saved blueprint / draft…', self.bp_open),
                          ('Practice with the sample (format example only)…', self.bp_sample)]:
            ttk.Button(s2, text=text, command=cmd).pack(side='left', padx=2)
        s3 = ttk.LabelFrame(f, text='Step 3 — Approved assets & readiness checklist', padding=6)
        s3.pack(fill='x', pady=4)
        row = ttk.Frame(s3)
        row.pack(fill='x')
        ttk.Button(row, text='Register approved page template…', command=self.register_template).pack(side='left', padx=2)
        ttk.Button(row, text='Register Lil Dr. Byrd image…', command=self.register_mascot).pack(side='left', padx=2)
        ttk.Button(row, text='Register other approved asset…', command=self.register_asset).pack(side='left', padx=2)
        ttk.Button(row, text='Build Concept Tiles (approved ByrdWay format)…', command=self.build_concept_tiles).pack(side='left', padx=2)
        self.prereq_box = tk.Text(s3, height=5, wrap='word', font=('Segoe UI', 9))
        self.prereq_box.pack(fill='x', pady=4)
        s4 = ttk.LabelFrame(f, text='Step 4 — Build one unit at a time, review it, approve it; then assemble and verify', padding=6)
        s4.pack(fill='both', expand=True, pady=4)
        bar = ttk.Frame(s4)
        bar.pack(fill='x')
        for text, cmd in [('Build next unit', self.build_next), ('Build next unit with QA loop', self.construct_next),
                          ('Open unit to review', self.open_unit),
                          ('Approve unit…', self.approve_unit), ('Reject unit…', self.reject_unit),
                          ('Edit blueprint (new version)…', self.bp_edit_build),
                          ('Assemble, verify & send to Jobs', self.assemble)]:
            ttk.Button(bar, text=text, command=cmd).pack(side='left', padx=2)
        self.btree = ttk.Treeview(s4, columns=('status', 'detail'), show='tree headings', height=9)
        self.btree.heading('#0', text='build / unit')
        self.btree.heading('status', text='status')
        self.btree.heading('detail', text='verification / assets')
        self.btree.column('#0', width=300)
        self.btree.column('status', width=260)
        self.btree.column('detail', width=520)
        self.btree.bind('<<TreeviewSelect>>', lambda e: self.refresh_prereqs())
        self.btree.pack(fill='both', expand=True, pady=4)

    def refresh_builds(self):
        sel = self.btree.selection()
        self.btree.delete(*self.btree.get_children())
        for s in self.studio.builds():
            title = s.get('title') or ''
            node = self.btree.insert('', 'end', iid=s['id'], open=True,
                                     text=f'{"Power Tool" if s["kind"] == "power_tool" else "Lil Dr. Byrd"}: {title} ({s["id"]})',
                                     values=(s.get('summary', ''), ''))
            for u in s['order']:
                x = s['units'][u]
                detail = (f'answers wrong {x.get("incorrect", "-")}, unverified {x.get("unverified", "-")}, '
                          f'missing assets {len(x.get("blocked_assets", []))}, layout '
                          f'{(x.get("template") or {}).get("template_status", "-")}')
                self.btree.insert(node, 'end', iid=f'{s["id"]}::{u}', text=f'  {u}', values=(x['status'], detail))
        if sel and self.btree.exists(sel[0]):
            self.btree.selection_set(sel[0])
        self.refresh_prereqs()

    def refresh_prereqs(self):
        bid = None
        s = self.btree.selection()
        if s:
            bid = s[0].split('::')[0]
            st = [b for b in self.studio.builds() if b['id'] == bid]
            if st:
                self.kind_var.set(st[0]['kind'])
        rows = self.studio.build_prerequisites(self.kind_var.get(), bid)
        self.prereq_box.delete('1.0', 'end')
        self.prereq_box.insert('end', ('For the selected build:\n' if bid else 'Before you build:\n'))
        for label, ok, why in rows:
            self.prereq_box.insert('end', f'{"✔" if ok else "✖"}  {label}' + ('' if ok else f'  —  {why}') + '\n')

    def _sel_build(self, unit_required=False):
        s = self.btree.selection()
        if not s:
            raise ValueError('Select a build (or one of its units) in the Step 4 list first.')
        parts = s[0].split('::')
        if unit_required and len(parts) != 2:
            raise ValueError('Select a unit row (the indented line under a build).')
        return parts

    # blueprint creation / opening
    def bp_new(self):
        self._open_editor(self.kind_var.get(), None)

    def bp_sample(self):
        kind = self.kind_var.get()
        if not messagebox.askokcancel('Sample = format example only',
                                      'The sample shows HOW to fill in a blueprint. It is NOT approved ByrdWay content.\n\n'
                                      'Anything built from it stays marked SAMPLE and Release QA will block it. '
                                      'Replace the text with your approved material and untick "Sample" before building '
                                      'a real product.'):
            return
        self._open_editor(kind, self.studio.sample_form(kind))

    def bp_open(self):
        if not messagebox.askokcancel('Open a saved blueprint',
                                      'Choose a blueprint or draft saved by this Studio (in the workspace "blueprints" '
                                      'folder) or a blueprint .json prepared by your team.\n\nIt opens in the form so you '
                                      'can check it before building.'):
            return
        p = filedialog.askopenfilename(title='Open blueprint or draft', initialdir=str(self.studio.root / 'blueprints'),
                                       filetypes=[('Blueprints and drafts', '*.json')])
        if not p:
            return
        try:
            kind, form = self.studio.load_blueprint_form(p)
        except Exception as e:
            return self.error('Blueprint could not be opened', e)
        self.kind_var.set(kind)
        self._open_editor(kind, form)

    def bp_edit_build(self):
        try:
            bid = self._sel_build()[0]
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        kind, form = self.studio.build_form(bid)
        messagebox.showinfo('Edit = new version', 'Your edits will create a NEW build. The current build and its approvals '
                                                  'are kept unchanged for your records.')
        self._open_editor(kind, form)

    def _open_editor(self, kind, form):
        self.editor = BlueprintEditor(self, kind, form, self._editor_saved)
        return self.editor

    def _editor_saved(self, kind, form, create_build):
        if create_build:
            b = self.studio.create_build_from_form(kind, form)
            self.log_line(f'Build {b.id} created. Next: check Step 3, then "Build next unit".')
            self.refresh_builds()
            self.btree.selection_set(b.id)
            self.refresh_prereqs()
            return b
        p = self.studio.save_draft(kind, form)
        self.log_line(f'Draft saved: {p}')
        return p

    # assets
    def register_template(self):
        if not messagebox.askokcancel('Approved page template',
                                      'Choose the APPROVED ByrdWay HTML page design for Power Tools.\n\nRequirement: an '
                                      '.html file containing the placeholder {{CONTENT}} where module content goes '
                                      '(optional {{TITLE}} and {{SCRIPT}}). Without it, modules use a provisional layout '
                                      'and release is blocked.'):
            return
        f = filedialog.askopenfilename(title='Approved ByrdWay template (.html)', filetypes=[('HTML template', '*.html *.htm')])
        if f:
            self._register_asset_file(f, 'byrdway_template', 'template')

    def register_mascot(self):
        if not messagebox.askokcancel('Approved Lil Dr. Byrd image',
                                      'Choose YOUR approved Lil Dr. Byrd artwork file (PNG or JPG).\n\nThe Studio never '
                                      'draws or substitutes the mascot. Once registered it is locked and fingerprinted; '
                                      'it cannot be replaced silently.'):
            return
        f = filedialog.askopenfilename(title='Approved Lil Dr. Byrd image', filetypes=[('Images', '*.png *.jpg *.jpeg')])
        if f:
            self._register_asset_file(f, 'lil_dr_byrd', 'mascot')

    def register_asset(self):
        f = filedialog.askopenfilename(title='Approved asset file')
        if not f:
            return
        aid = simpledialog.askstring('Asset id', 'Short id (lowercase, e.g. physics_diagram_1):')
        kind = simpledialog.askstring('Kind', 'Kind: mascot, logo, template, illustration, font, reference_product')
        if aid and kind:
            self._register_asset_file(f, aid.strip(), kind.strip())

    def _register_asset_file(self, f, aid, kind):
        if not messagebox.askyesno('Confirm', f'I am the owner and "{Path(f).name}" is APPROVED for use as {kind} "{aid}".'):
            return
        try:
            self.studio.register_asset(f, aid, kind, explicit=True)
            self.log_line(f'Registered approved {kind}: {aid}')
        except Exception as e:
            self.error('Asset not registered', e)
        self.refresh_builds()

    # building
    def build_next(self):
        try:
            bid = self._sel_build()[0]
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))

        def done(r):
            if r[0] is None:
                self.log_line('All units are approved. Next: "Assemble, verify & send to Jobs".')
            else:
                self.log_line(f'Built {r[0]}: {r[1]["status"]}. Next: "Open unit to review", then approve or reject.')
                if self.btree.exists(f'{bid}::{r[0]}'):
                    self.btree.selection_set(f'{bid}::{r[0]}')
        self.run_bg('Build', lambda: self.studio.build_next(bid), done)

    def build_concept_tiles(self):
        toc = filedialog.askopenfilename(title='Approved table of contents (.md)', filetypes=[('Markdown', '*.md')])
        if not toc:
            return
        content = filedialog.askopenfilename(title='Tile content (.json)', filetypes=[('JSON', '*.json')])
        if not content:
            return
        course = simpledialog.askstring('Course', 'Course name for the footer (e.g. Physics + Honors):') or 'ByrdWay Concept Tiles'
        mascot = filedialog.askopenfilename(title='Approved Lil Dr. Byrd image (optional)', filetypes=[('Image', '*.png *.jpg')]) or None

        def done(rep):
            self.log_line(f'Concept Tiles: {rep["decision"]} - {rep["mandatory_checks"] - rep["failed"]}/{rep["mandatory_checks"]} '
                          f'mandatory checks, {rep["pages"]} pages: {rep["pdf"]}')
            for f in rep['failures'][:15]:
                self.log_line(f'   SEND BACK: {f[0]}: {f[2]}')
        self.run_bg('Concept Tiles', lambda: self.studio.build_concept_tiles(toc, content, course, mascot), done)

    def construct_next(self):
        """Builder -> independent Build QA (academic, Reader lessons, code, browser, Mastery standard) -> repair ->
        rebuild -> Chief Judge. A PASS unit still waits for the owner's approval."""
        try:
            bid = self._sel_build()[0]
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))

        def done(r):
            if r[0] is None:
                return self.log_line('All units are approved. Next: "Assemble, verify & send to Jobs".')
            c = r[1]['construction']
            j = c['chief_judge']
            self.log_line(f'{r[0]}: {j["decision"]} - {j["passed"]}/{j["mandatory_checks"]} mandatory checks, '
                          f'{len(c["rounds"])} round(s).')
            for f in (c['rounds'][-1].get('failed') or [])[:12]:
                self.log_line('   SEND BACK: ' + f)
        self.run_bg('Build with QA loop', lambda: self.studio.construct_next(bid), done)

    def open_unit(self):
        try:
            bid, unit = self._sel_build(unit_required=True)
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        st = [s for s in self.studio.builds() if s['id'] == bid][0]['units'][unit]
        if not st.get('output'):
            return messagebox.showinfo('Not built yet', 'This unit has not been built yet. Click "Build next unit".')
        self.opener(st['output'])

    def approve_unit(self):
        try:
            bid, unit = self._sel_build(unit_required=True)
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        st = [s for s in self.studio.builds() if s['id'] == bid][0]['units'][unit]
        if st['status'] in ('NOT_BUILT',):
            return messagebox.showinfo('Not built yet', 'Build this unit first.')
        if st['status'].startswith('BLOCKED'):
            return messagebox.showerror('Cannot approve', f'{unit} is {st["status"]}. ' + {
                'BLOCKED_ACADEMIC_DEFECT': 'An answer in the blueprint is mathematically wrong. Open the unit, fix the '
                                           'answer with "Edit blueprint (new version)…", and rebuild.',
                'BLOCKED_MISSING_APPROVED_ASSET': 'An approved asset (for example the Lil Dr. Byrd image) is not '
                                                  'registered. Register it in Step 3, then build the unit again.'}.get(st['status'], ''))
        attest = False
        if st['status'] == 'NEEDS_OWNER_REVIEW':
            attest = messagebox.askyesno('Your review is required',
                                         'Some answers could not be checked automatically, or the content is SAMPLE / '
                                         'AI-drafted.\n\nHave you personally reviewed every item in this unit?')
            if not attest:
                return
        if messagebox.askyesno('Approve unit', f'Approve {unit}? (Use "Open unit to review" first.)'):
            try:
                self.studio.approve_unit(bid, unit, True, attest)
                self.log_line(f'Approved {unit}. Next: "Build next unit".')
            except Exception as e:
                self.error('Approval refused', e)
        self.refresh_builds()

    def reject_unit(self):
        try:
            bid, unit = self._sel_build(unit_required=True)
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        reason = simpledialog.askstring('Reject unit', 'What needs to change?')
        if reason:
            self.studio.reject_unit(bid, unit, reason)
            self.log_line(f'Rejected {unit}: {reason}. Use "Edit blueprint (new version)…" to correct it.')
            self.refresh_builds()

    def assemble(self):
        try:
            bid = self._sel_build()[0]
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        st = [s for s in self.studio.builds() if s['id'] == bid][0]
        pending = [u for u in st['order'] if st['units'][u]['status'] != 'OWNER_APPROVED']
        if pending:
            return messagebox.showinfo('Not ready', f'Approve every unit first. Still waiting: {", ".join(pending)}')
        if not messagebox.askyesno('Assemble & verify', 'Package all approved units, import the package as a product, '
                                   'and run independent Release QA on it?'):
            return

        def done(job):
            self.log_line(f'Assembled and verified: {job["status"]}. See tab 2.')
            self.nb.select(1)
            self.refresh_jobs()
            if self.jtree.exists(job['id']):
                self.jtree.selection_set(job['id'])
                self.show_job()
        self.run_bg('Assemble & verify', lambda: self.studio.assemble_and_verify(bid, progress=self.progress), done)

    # ------------------------------------------------------------ costs/settings
    def _costs_tab(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text='4. API Costs & Settings')
        self.cost_lbl = ttk.Label(f, text='', justify='left', font=('Segoe UI', 10))
        self.cost_lbl.pack(anchor='w')
        form = ttk.LabelFrame(f, text='Limits (USD)', padding=8)
        form.pack(fill='x', pady=6)
        self.vars = {}
        fields = [('budget', 'funded_usd', 'Owner-authorized funding (what you added to OpenAI)'),
                  ('budget', 'reserve_usd', 'Reserve never to spend'), ('budget', 'max_job_usd', 'Max per job'),
                  ('budget', 'max_daily_usd', 'Max per day'), ('repair', 'max_iterations', 'Max repair iterations'),
                  ('repair', 'max_runtime_seconds', 'Max job runtime (s)')]
        for i, (sec, key, label) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky='w')
            v = tk.StringVar()
            self.vars[(sec, key)] = v
            ttk.Entry(form, textvariable=v, width=12).grid(row=i, column=1, sticky='w', padx=6)
        ttk.Button(form, text='Save limits', command=self.save_limits).grid(row=len(fields), column=0, pady=6, sticky='w')
        ttk.Button(form, text='Store OpenAI API key in Windows Credential Manager…',
                   command=self.set_key).grid(row=len(fields), column=1, pady=6, sticky='w')
        self.ledger_box = tk.Text(f, height=12, font=('Consolas', 9))
        self.ledger_box.pack(fill='both', expand=True)

    def refresh_costs(self):
        s = self.studio.settings()
        c = self.studio.cost_summary()
        key = self.studio.api_key_configured()
        funded = float(s['budget']['funded_usd']) > float(s['budget']['reserve_usd'])
        state = ('ENABLED (each call still needs your Yes)' if key and funded else
                 'DISABLED — ' + ('no API key stored' if not key else 'no funding above the reserve is set') +
                 '. Everything except AI suggestions works offline.')
        self.cost_lbl.config(text=(f'Provider: OpenAI (only AI provider; Claude is not used at runtime)\n'
                                   f'AI processing: {state}\n'
                                   f'API key configured: {"YES" if key else "NO"}\n'
                                   f'Recorded spend: ${c["total_recorded_usd"]:.4f} total, ${c["today_usd"]:.4f} today, {c["calls"]} calls\n'
                                   f'Remaining authorized: ${c["remaining_authorized_usd"]:.4f} (funded ${c["funded_usd"]:.2f} - reserve ${c["reserve_usd"]:.2f})\n'
                                   f'{c["balance_note"]}\n'
                                   f'Models: {s["models"]}   Prices from {s["pricing_source"]} copied {s["pricing_copied_on"]} (re-check before funding).'))
        for (sec, key), v in self.vars.items():
            v.set(str(s[sec][key]))
        self.ledger_box.delete('1.0', 'end')
        for e in self.studio.ledger()[-200:]:
            self.ledger_box.insert('end', f'{e["ts"]} {e.get("status"):12} {e.get("model"):14} est ${e.get("estimate_usd", 0):.4f} '
                                          f'charged ${e.get("charged_usd", 0):.4f} {e.get("role")} job {e.get("job_id")}\n')

    def save_limits(self):
        s = self.studio.settings()
        try:
            for (sec, key), v in self.vars.items():
                s[sec][key] = int(v.get()) if key in ('max_iterations', 'max_runtime_seconds') else float(v.get())
            self.studio.save_settings(s)
            messagebox.showinfo('Saved', 'Limits saved.')
        except Exception as e:
            messagebox.showerror('Invalid', str(e))
        self.refresh_costs()

    def set_key(self):
        k = simpledialog.askstring('OpenAI API key', 'Paste key (stored in the OS secret store, never in files or logs):', show='•')
        if k:
            try:
                self.studio.set_api_key(k)
                messagebox.showinfo('Stored', 'Key stored securely.')
            except Exception as e:
                messagebox.showerror('Not stored', str(e))
        self.refresh_costs()

    # ------------------------------------------------------------- backup/logs
    def _backup_tab(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text='5. Backup & Restore')
        ttk.Label(f, text='Backups contain originals, proposals, jobs, reports, approved copies, assets, builds, '
                          'logs and settings (never API keys). Each backup is hash-verified after writing.',
                  wraplength=900).pack(anchor='w')
        ttk.Button(f, text='Create verified backup now', command=self.backup).pack(anchor='w', pady=6)
        ttk.Button(f, text='Restore from backup…', command=self.restore).pack(anchor='w')

    def backup(self):
        self.run_bg('Backup', self.studio.backup, lambda p: messagebox.showinfo('Backup', f'Verified backup written:\n{p}'))

    def restore(self):
        f = filedialog.askopenfilename(title='Backup ZIP', filetypes=[('Backup', '*.zip')])
        if f and messagebox.askyesno('Restore', 'Replace the current workspace with this backup?\n'
                                     'A safety backup of the current workspace is made first.'):
            self.run_bg('Restore', lambda: self.studio.restore(f, True),
                        lambda r: messagebox.showinfo('Restored', json.dumps(r, indent=1)))

    def _powerhouse_tab(self):
        """The Byrd Powerhouse: who the agents are, what each can do today, what they did, what they learned."""
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text='7. Byrd Powerhouse')
        self.ph_frame = f
        org = self.studio.powerhouse()
        ttk.Label(f, text='ENGINEERING DIVISION - 12 agents  (WORKING / PARTIAL / MISSING per product family)',
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        cols = ('group', 'agent', 'job', 'Power Tool', 'Lil Dr. Byrd Explainer', 'Concept Tiles')
        self.ph_tree = ttk.Treeview(f, columns=cols, show='headings', height=12)
        for c, w in zip(cols, (90, 150, 430, 90, 140, 100)):
            self.ph_tree.heading(c, text=c)
            self.ph_tree.column(c, width=w)
        for group, agents in org['engineering'].items():
            for a in agents:
                st = a['status']
                self.ph_tree.insert('', 'end', iid=f'agent{a["id"]}', values=(
                    group, f'{a["id"]}. {a["name"]}', a['job'], st['Power Tool'], st['Lil Dr. Byrd Explainer'],
                    st['Concept Tiles']))
        self.ph_tree.pack(fill='x')
        ttk.Label(f, text='REVENUE & MEDIA DIVISION - 10 roles (tab 8)', font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(8, 0))
        self.ph_rev = tk.Text(f, height=11, font=('Segoe UI', 9))
        self.ph_rev.insert('1.0', '\n'.join(f'{i:2}. {r["status"]:8} {r["name"]}: {r["job"]}  [{r["where"]}]'
                                             for i, r in enumerate(org['revenue'], 1))
                           + f'\nTargets: {org["sales_targets"]}   Quality: {org["quality_target"]}')
        self.ph_rev.pack(fill='x')
        bar = ttk.Frame(f)
        bar.pack(fill='x', pady=6)
        ttk.Button(bar, text='Feed a product to the Powerhouse (import + detect + repair + QA)…',
                   command=self.powerhouse_feed).pack(side='left')
        ttk.Button(bar, text='Show what the agents did (selected job)', command=self.powerhouse_timeline).pack(side='left', padx=6)
        ttk.Button(bar, text='Lessons learned', command=self.powerhouse_lessons).pack(side='left')
        self.ph_out = tk.Text(f, height=8, font=('Consolas', 9))
        self.ph_out.pack(fill='both', expand=True)

    def _revenue_tab(self):
        """Revenue & Media Division: 10 roles, source-linked methods, daily workflow, dashboard. Drafts only."""
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text='8. Revenue & Media')
        self.rev_frame = f
        ttk.Label(f, text='REVENUE & MEDIA DIVISION - 10 roles. The app drafts and measures; YOU approve, send and publish.',
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        bar = ttk.Frame(f)
        bar.pack(fill='x', pady=4)
        for text, cmd in [("Run today's sales workflow", self.sales_run_daily), ('Revenue dashboard', self.sales_show_dashboard),
                          ('Import TpT sales report (CSV)…', self.sales_import), ('Set Week 1 start date…', self.sales_set_week1),
                          ('Load product catalog (JSON)…', self.sales_load_catalog), ('Strategy library', self.sales_show_library)]:
            ttk.Button(bar, text=text, command=cmd).pack(side='left', padx=2)
        self.rev_out = tk.Text(f, height=30, font=('Consolas', 9), wrap='word')
        self.rev_out.pack(fill='both', expand=True)

    def _rev_print(self, lines):
        self.rev_out.delete('1.0', 'end')
        self.rev_out.insert('end', '\n'.join(lines) + '\n')
        self.nb.select(self.rev_frame)

    def sales_run_daily(self):
        def done(res):
            rep, _ = res
            L = [f"DAILY SALES WORKFLOW {rep['date']}  -  {rep['discipline']}", '']
            L += [f"  {r['role']:28} {', '.join(r['methods_applied'])}" for r in rep['roles']]
            L += ['', f"Catalog: {rep['catalog']}", f"Outputs: {rep['outputs']}",
                  f"Sales QA: {rep['sales_qa']['passed']}/{rep['sales_qa']['checks']} checks passed; blocked: {len(rep['sales_qa']['blocked'])}"]
            L += [f"   BLOCKED {b['item']}: {'; '.join(b['problems'])}" for b in rep['sales_qa']['blocked'][:10]]
            rd = rep['roadmap']
            L += ['', f"SCALING ROADMAP STAGE: {rd['stage']['stage']} {rd['stage']['name']}"
                      + (' (PROVISIONAL)' if rd['stage']['provisional'] else ''),
                  *[f'   because: {r}' for r in rd['stage']['reasons']], *[f'   unverified: {u}' for u in rd['stage']['unverified']],
                  f"BOTTLENECK: {rd['bottleneck']['constraint']} - {rd['bottleneck']['why']}. Fix: {rd['bottleneck']['fix']}",
                  'TODAY (priority order):'] + [f"  {a['priority']:2}. [{a['role']}] {a['action']}  -> metric: {a['metric']}  ({', '.join(a['methods'])})"
                                                for a in rd['daily_plan']['actions']]
            L += ['', f"Measured: {rep['measured']}", '', 'YOUR QUEUE:'] + [f'  - {q}' for q in rep['owner_queue']]
            self._rev_print(L)
        self.run_bg('Sales workflow', self.studio.sales_daily, done)

    def sales_show_dashboard(self):
        d = self.studio.sales_dashboard()
        L = [f"Week 1 starts: {d['week1_start'] or 'NOT SET (use Set Week 1 start date)'}",
             f"Real sales rows: {d['real_rows']}  (TEST rows excluded: {d['test_rows_excluded']})  units {d['units_total']}  net ${d['net_total']}",
             f"Repeat-purchase rate: {d['repeat_purchase_rate']}",
             f"1,000 units/week milestone: week {d['milestone_1000']['minimum_path_week']} (+10 %) / week {d['milestone_1000']['stretch_path_week']} (+17 %)", '',
             f"{'week':>4} {'units':>6} {'min':>6} {'stretch':>8} {'net $':>10}  status"]
        L += [f"{w['week']:>4} {w['units']:>6} {w['minimum']:>6} {w['stretch']:>8} {w['net']:>10}  {w['status']}" for w in d['weeks']]
        self._rev_print(L)

    def sales_import(self):
        p = filedialog.askopenfilename(filetypes=[('CSV', '*.csv')])
        if p:
            r = self.studio.sales_import_csv(p)
            self.log_line(f'Imported {r["imported"]} sales rows.')
            self.sales_show_dashboard()

    def sales_set_week1(self):
        from tkinter import simpledialog
        d = simpledialog.askstring('Week 1', 'Week 1 start date (YYYY-MM-DD):')
        if d:
            s = self.studio.sales_settings()
            s['week1_start'] = d.strip()
            self.studio.sales_save_settings(s)
            self.sales_show_dashboard()

    def sales_load_catalog(self):
        p = filedialog.askopenfilename(filetypes=[('JSON', '*.json')])
        if p:
            s = self.studio.sales_settings()
            s['catalog'] = json.loads(Path(p).read_text(encoding='utf-8'))
            self.studio.sales_save_settings(s)
            self.log_line(f'Catalog loaded: {len(s["catalog"])} products (only QA PASS + owner-approved ones are marketed).')

    def sales_show_library(self):
        lib = self.studio.sales_library()
        L = ['RULES:'] + [f'  - {r}' for r in lib['rules']] + ['']
        for m in lib['methods']:
            L.append(f"{m['id']:6} [{m['status']}] {m['expert']}: {m['method']}")
            L.append(f"        apply: {m['apply_at_byrdway']}")
            L.append(f"        metric: {m['metric']}   roles: {', '.join(m['roles'])}")
            L.append(f"        source: {m['source']['citation']}" + (f"  \"{m['source']['quote']}\"" if m['source'].get('quote') else ''))
        self._rev_print(L)

    def powerhouse_feed(self):
        """One click: import a product, then run the full detect -> repair -> QA loop on a protected copy."""
        before = {p['id'] for p in self.studio.products()}
        self.import_one()
        new = [p for p in self.studio.products() if p['id'] not in before]
        if not new:
            return
        self.ptree.selection_set(new[0]['id'])
        self.run_job(done_extra=lambda j: self.powerhouse_timeline(j['id']))

    def powerhouse_timeline(self, job_id=None):
        try:
            jid = job_id or self.selected_job()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        self.ph_out.delete('1.0', 'end')
        for agent, did in self.studio.job_timeline(jid):
            self.ph_out.insert('end', f'{agent:28} {did}\n')
        self.nb.select(self.ph_frame)

    def powerhouse_lessons(self):
        self.ph_out.delete('1.0', 'end')
        ls = self.studio.lessons()
        if not ls:
            self.ph_out.insert('end', 'No lessons yet: feed a product to the Powerhouse first.\n')
        for l in ls:
            self.ph_out.insert('end', f'{l["times_seen"]:4}x  {l["lesson"]:28} -> builders held to: {l["guarded_by"]}\n')

    def _logs_tab(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text='6. Activity & Error Log')
        ttk.Button(f, text='Refresh', command=self.refresh_logs).pack(anchor='w')
        self.actbox = tk.Text(f, font=('Consolas', 9))
        self.actbox.pack(fill='both', expand=True)

    def refresh_logs(self):
        self.actbox.delete('1.0', 'end')
        for e in self.studio.activity(400):
            self.actbox.insert('end', f'{e["ts"]} {e["level"]:5} {e.get("job", ""):24} {e["role"]:18} {e["message"]}\n')


class ImageFindingsDialog(tk.Toplevel):
    """Owner reviews each finding from image pages: picture of the spot, proposed correction,
    Confirm error / Not an error. Nothing is changed in the product."""

    def __init__(self, app, job_id, items):
        super().__init__(app)
        self.app, self.job_id, self.items = app, job_id, items
        self.owner = None
        self.title('Review image findings - nothing is changed in your product')
        self.geometry('1100x640')
        top = ttk.Frame(self, padding=8)
        top.pack(fill='x')
        ttk.Label(top, text='Look at each picture. Confirm real errors; dismiss misreads. Confirmed errors go on the '
                            'correction sheet for your editable source.', wraplength=1050).pack(anchor='w')
        body = ttk.PanedWindow(self, orient='horizontal')
        body.pack(fill='both', expand=True, padx=8)
        self.tree = ttk.Treeview(body, columns=('page', 'kind', 'statement', 'decision'), show='headings',
                                 selectmode='browse')
        for col, w in (('page', 50), ('kind', 60), ('statement', 260), ('decision', 100)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w)
        body.add(self.tree, weight=2)
        right = ttk.Frame(body, padding=6)
        body.add(right, weight=3)
        self.pic = ttk.Label(right)
        self.pic.pack(anchor='w', pady=4)
        self.detail = ttk.Label(right, text='', wraplength=560, justify='left')
        self.detail.pack(anchor='w', pady=4)
        ttk.Label(right, text='Correction (edit if needed):').pack(anchor='w')
        self.corr = tk.StringVar()
        ttk.Entry(right, textvariable=self.corr, width=80).pack(anchor='w', fill='x')
        ttk.Label(right, text='Exact characters that should appear on the page (used by "Repair Confirmed on a Copy"; '
                              'for a spelling error type the correct word):', wraplength=560).pack(anchor='w', pady=(6, 0))
        self.repl = tk.StringVar()
        ttk.Entry(right, textvariable=self.repl, width=30).pack(anchor='w')
        bar = ttk.Frame(right)
        bar.pack(anchor='w', pady=8)
        ttk.Button(bar, text='Confirm error', command=lambda: self.decide('confirmed')).pack(side='left', padx=2)
        ttk.Button(bar, text='Not an error (misread)', command=lambda: self.decide('dismissed')).pack(side='left', padx=2)
        ttk.Button(bar, text='Close', command=self.destroy).pack(side='left', padx=12)
        self.tree.bind('<<TreeviewSelect>>', lambda e: self.show())
        self._img = None
        self.fill()

    def fill(self):
        self.tree.delete(*self.tree.get_children())
        for it in self.items:
            self.tree.insert('', 'end', iid=it['id'], values=(it['page'], it['kind'], it['statement'],
                                                             it['decision'] or 'to decide'))
        pending = [i['id'] for i in self.items if not i['decision']]
        if pending or self.items:
            self.tree.selection_set(pending[0] if pending else self.items[0]['id'])
            self.show()

    def current(self):
        s = self.tree.selection()
        return next((i for i in self.items if s and i['id'] == s[0]), None)

    def show(self):
        it = self.current()
        if not it:
            return
        self.detail.config(text=f'{it["detail"]}\n\nProposed: {it.get("proposal") or "-"}')
        self.corr.set(it.get('correction') or it.get('proposal') or '')
        self.repl.set(it.get('replacement') or ('' if it['kind'] == 'typo' else (it.get('expected') or '')))
        self._img = None
        if it.get('crop') and Path(it['crop']).exists():
            try:
                img = tk.PhotoImage(file=it['crop'])
                k = max(1, -(-img.width() // 560))
                self._img = img.subsample(k, k) if k > 1 else img
            except tk.TclError:
                self._img = None
        self.pic.config(image=self._img or '', text='' if self._img else '(no picture)')

    def decide(self, verdict):
        it = self.current()
        if not it:
            return
        if not self.owner:
            self.owner = simpledialog.askstring('Your name', 'Your name (recorded with each decision):', parent=self)
            if not self.owner:
                return
        try:
            self.app.studio.decide_image_finding(self.job_id, it['id'], verdict, self.owner, self.corr.get().strip() or None,
                                                 replacement=self.repl.get().strip() or None)
        except Exception as e:
            return self.app.error('Decision not recorded', e)
        self.items = self.app.studio.image_findings(self.job_id)
        self.fill()
        self.app.refresh_jobs()
        if self.app.jtree.exists(self.job_id):
            self.app.jtree.selection_set(self.job_id)
            self.app.show_job()

    def destroy(self):
        super().destroy()
        gc.collect()


class BlueprintEditor(tk.Toplevel):
    """Fill-in form for a blueprint. No JSON. Plain-text lines with on-screen help."""
    PT_FIELDS = [('concepts', 'Concepts'), ('worked_examples', 'Worked examples'), ('practice', 'Practice questions'),
                 ('flashcards', 'Flashcards'), ('cheat_sheet', 'Cheat sheet')]
    CH_FIELDS = [('sections', 'Chapter text'), ('practice', 'Practice questions')]

    def __init__(self, app, kind, form, on_save):
        super().__init__(app)
        import builders
        self.B = builders
        self.app, self.kind, self.on_save = app, kind, on_save
        self.title('New Power Tool blueprint' if kind == 'power_tool' else 'New Lil Dr. Byrd chapter blueprint')
        self.geometry('1060x720')
        form = form or ({'product_title': '', 'subject': '', 'grade': '', 'modules': [{'title': 'Module 1'}]}
                        if kind == 'power_tool' else {'subject': 'Physics', 'chapters': [{'title': 'Chapter 1'}]})
        self.units = form.get('modules' if kind == 'power_tool' else 'chapters') or []
        self.cur = None
        top = ttk.Frame(self, padding=8)
        top.pack(fill='x')
        self.vars = {}
        fields = ([('product_title', 'Product title'), ('subject', 'Subject'), ('grade', 'Grade')]
                  if kind == 'power_tool' else [('subject', 'Subject')])
        for i, (k, label) in enumerate(fields):
            ttk.Label(top, text=label).grid(row=0, column=2 * i, sticky='w')
            v = tk.StringVar(value=form.get(k, ''))
            self.vars[k] = v
            ttk.Entry(top, textvariable=v, width=34 if k == 'product_title' else 16).grid(row=0, column=2 * i + 1, padx=4)
        self.honors_ok = tk.BooleanVar(value=bool(form.get('honors_approved')))
        ttk.Checkbutton(top, text='Honors content approved for this product', variable=self.honors_ok).grid(row=1, column=0, columnspan=3, sticky='w')
        if kind != 'power_tool':
            self.honors = tk.BooleanVar(value=bool(form.get('honors')))
            ttk.Checkbutton(top, text='Honors edition', variable=self.honors).grid(row=1, column=3, sticky='w')
        self.sample = tk.BooleanVar(value=bool(form.get('_sample')))
        ttk.Checkbutton(top, text='Sample / practice content (Release QA will block it)', variable=self.sample).grid(row=1, column=4, columnspan=3, sticky='w')
        body = ttk.PanedWindow(self, orient='horizontal')
        body.pack(fill='both', expand=True, padx=8)
        left = ttk.Frame(body)
        body.add(left, weight=1)
        ttk.Label(left, text='Modules' if kind == 'power_tool' else 'Chapters').pack(anchor='w')
        self.lst = tk.Listbox(left, height=12, exportselection=False)
        self.lst.pack(fill='both', expand=True)
        self.lst.bind('<<ListboxSelect>>', lambda e: self._select(self.lst.curselection()[0] if self.lst.curselection() else None))
        for t, c in [('Add', self.add_unit), ('Rename…', self.rename_unit), ('Remove', self.remove_unit)]:
            ttk.Button(left, text=t, command=c).pack(fill='x')
        right = ttk.Notebook(body)
        body.add(right, weight=4)
        self.texts = {}
        for key, label in (self.PT_FIELDS if kind == 'power_tool' else self.CH_FIELDS):
            fr = ttk.Frame(right, padding=4)
            right.add(fr, text=label)
            ttk.Label(fr, text=self.B.FORM_HELP[key], foreground='#0b3d91', justify='left').pack(anchor='w')
            t = tk.Text(fr, wrap='word', font=('Consolas', 10), undo=True)
            t.pack(fill='both', expand=True)
            self.texts[key] = t
        self.msg = ttk.Label(self, text='', foreground='#aa1111', wraplength=1000, justify='left')
        self.msg.pack(fill='x', padx=8)
        bar = ttk.Frame(self, padding=8)
        bar.pack(fill='x')
        ttk.Button(bar, text='Check for errors', command=self.validate).pack(side='left', padx=2)
        ttk.Button(bar, text='Save & create build', command=lambda: self.save(True)).pack(side='left', padx=2)
        ttk.Button(bar, text='Save draft (finish later)', command=lambda: self.save(False)).pack(side='left', padx=2)
        ttk.Button(bar, text='Cancel', command=self.destroy).pack(side='right')
        self._reload_list()
        self._select(0 if self.units else None)

    def _reload_list(self):
        self.lst.delete(0, 'end')
        for u in self.units:
            self.lst.insert('end', u.get('title') or '(untitled)')

    def _store(self):
        if self.cur is not None and self.cur < len(self.units):
            for k, t in self.texts.items():
                self.units[self.cur][k] = t.get('1.0', 'end-1c')

    def _select(self, i):
        self._store()
        self.cur = i
        for k, t in self.texts.items():
            t.delete('1.0', 'end')
            if i is not None:
                t.insert('1.0', self.units[i].get(k, ''))
        if i is not None:
            self.lst.selection_clear(0, 'end')
            self.lst.selection_set(i)

    def add_unit(self, title=None):
        self._store()
        name = title or simpledialog.askstring('Title', 'Title:', parent=self)
        if name:
            self.units.append({'title': name})
            self._reload_list()
            self._select(len(self.units) - 1)

    def rename_unit(self):
        if self.cur is None:
            return
        name = simpledialog.askstring('Rename', 'New title:', parent=self, initialvalue=self.units[self.cur].get('title', ''))
        if name:
            self.units[self.cur]['title'] = name
            self._reload_list()
            self.lst.selection_set(self.cur)

    def remove_unit(self):
        if self.cur is not None and messagebox.askyesno('Remove', 'Remove this unit from the blueprint?', parent=self):
            del self.units[self.cur]
            self.cur = None
            self._reload_list()
            self._select(0 if self.units else None)

    def form(self):
        self._store()
        f = {k: v.get() for k, v in self.vars.items()}
        f['honors_approved'] = self.honors_ok.get()
        f['_sample'] = self.sample.get()
        if self.kind == 'power_tool':
            f['modules'] = self.units
        else:
            f['honors'] = self.honors.get()
            f['chapters'] = self.units
        return f

    def validate(self):
        try:
            (self.B.power_tool_blueprint_from_form if self.kind == 'power_tool' else self.B.chapter_blueprint_from_form)(self.form())
        except self.B.FormError as e:
            self.msg.config(text='Fix before building:  ' + str(e))
            return False
        self.msg.config(text='')
        messagebox.showinfo('Blueprint', 'No errors found. You can "Save & create build".', parent=self)
        return True

    def save(self, create):
        try:
            if create:
                (self.B.power_tool_blueprint_from_form if self.kind == 'power_tool' else self.B.chapter_blueprint_from_form)(self.form())
            r = self.on_save(self.kind, self.form(), create)
        except self.B.FormError as e:
            self.msg.config(text='Fix before building:  ' + str(e))
            return None
        self.destroy()
        return r

    def destroy(self):
        super().destroy()
        gc.collect()          # free Tk variables on the UI thread (see App.run_bg)


if __name__ == '__main__':
    App().mainloop()
