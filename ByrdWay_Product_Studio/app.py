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
        ttk.Label(top, text='Protected originals • Seven specialist roles • Independent verification • '
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
        self._poll_id = self.after(150, self._poll)
        self.refresh_all()

    def _menu(self):
        mb = tk.Menu(self)
        h = tk.Menu(mb, tearoff=0)
        h.add_command(label='Quick Start (open guide)', command=lambda: self.opener(Path(__file__).with_name('OWNER_QUICK_START.md')))
        h.add_command(label='Run self-test (checks this PC)', command=self.run_selftest)
        h.add_command(label='About / version', command=lambda: messagebox.showinfo(
            'About', f'{APP_TITLE}\nWorkspace: {self.studio.root}\nNothing is ever published automatically.'))
        mb.add_cascade(label='Help', menu=h)
        self.config(menu=mb)

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
                if kind == 'done':
                    self.status.set(label + ': done')
                    if b:
                        b(a)
                else:
                    self.status.set(label + ': FAILED')
                    self.error(f'{label} failed', a)
                self.refresh_all()
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

    def run_job(self):
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
                          ('Re-run Release QA', self.rerun_qa), ('Attest Unverifiable Item…', self.attest),
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
        self.prereq_box = tk.Text(s3, height=5, wrap='word', font=('Segoe UI', 9))
        self.prereq_box.pack(fill='x', pady=4)
        s4 = ttk.LabelFrame(f, text='Step 4 — Build one unit at a time, review it, approve it; then assemble and verify', padding=6)
        s4.pack(fill='both', expand=True, pady=4)
        bar = ttk.Frame(s4)
        bar.pack(fill='x')
        for text, cmd in [('Build next unit', self.build_next), ('Open unit to review', self.open_unit),
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
