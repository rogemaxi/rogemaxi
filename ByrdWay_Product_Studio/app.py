"""ByrdWay Product Engineering Studio - Windows desktop UI (Python standard library Tk).

Run: python app.py   (or double-click START_WINDOWS.bat)
All logic lives in controller.Studio; this file is presentation only.
Long operations run on a worker thread; owner decisions (API spend, approval)
are always modal dialogs on the UI thread.
"""
import json, os, queue, subprocess, sys, threading, traceback

if __name__ == '__main__' and '--selftest' in sys.argv:      # headless: no GUI libraries needed
    import selftest
    sys.exit(selftest.main())

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path

from controller import Studio, next_action
from engine import ROLES, save_proposal, original_file
from ai_roles import run_review, ROLE_PROMPTS

APP_TITLE = 'ByrdWay Product Engineering Studio | v0.2'
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
        self.after(150, self._poll)
        self.refresh_all()

    # ---------------------------------------------------------------- helpers
    def run_bg(self, label, fn, done=None):
        if self.busy:
            messagebox.showinfo('Busy', 'Another operation is running. Please wait.')
            return
        self.busy = True
        self.status.set(label + ' ...')

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
                    self.log_line(f'{label} FAILED: {a}')
                    messagebox.showerror(label, str(a))
                self.refresh_all()
        except queue.Empty:
            pass
        self.after(150, self._poll)

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
        bar = ttk.Frame(f)
        bar.pack(fill='x')
        self.ai_var = tk.BooleanVar(value=False)
        for text, cmd in [('Import Product…', self.import_one), ('Run Repair & Verify Job', self.run_job),
                          ('Local Audit', self.audit), ('AI Read-Only Review…', self.ai_review),
                          ('Manual Text Proposal…', self.proposal), ('Verify Originals', self.verify_originals),
                          ('Open Workspace', lambda: open_path(self.studio.root))]:
            ttk.Button(bar, text=text, command=cmd).pack(side='left', padx=2)
        ttk.Checkbutton(bar, text='Allow AI repair suggestions (asks before every paid call)',
                        variable=self.ai_var).pack(side='left', padx=8)
        self.ptree = self._tree(f, ('id', 'name', 'type', 'imported', 'sha256', 'integrity'), (110, 300, 170, 150, 200, 110))
        self.ptree.pack(fill='both', expand=True, pady=6)
        ttk.Label(f, text='Activity:').pack(anchor='w')
        self.logbox = tk.Text(f, height=9, wrap='word', font=('Consolas', 9))
        self.logbox.pack(fill='x')
        self.log_line('Ready. Import a Power Tool (HTML/ZIP) or Explainer (PDF). Originals are copied and locked; '
                      'all repairs happen on working copies.')

    def refresh_products(self):
        self.ptree.delete(*self.ptree.get_children())
        for p in self.studio.products():
            self.ptree.insert('', 'end', iid=p['id'], values=(p['id'], p['name'], p.get('product_type', ''),
                                                              p.get('imported_at', ''), p.get('sha256', '')[:16] + '…',
                                                              p.get('integrity', '')))

    def selected_pid(self):
        s = self.ptree.selection()
        if not s:
            raise ValueError('Select a product first')
        return s[0]

    def import_one(self):
        f = filedialog.askopenfilename(filetypes=[('Supported files', '*.html *.htm *.js *.css *.txt *.md *.json *.pdf *.zip')])
        if f:
            try:
                m = self.studio.import_product(f)
                self.log_line(f'IMPORTED {m["name"]} as {m["product_type"]} SHA-256 {m["sha256"]}')
                self.refresh_products()
            except Exception as e:
                messagebox.showerror('Import blocked', str(e))

    def run_job(self):
        try:
            pid = self.selected_pid()
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        ai = self.ai_var.get()
        progress = lambda m: self.q.put(('progress', None, m, None))

        def done(job):
            qa = job.get('qa') or {}
            self.log_line(f'JOB {job["id"]}: {job["status"]} (QA {qa.get("decision")}, score {qa.get("score")}, '
                          f'stop: {job.get("stop_reason")})')
            self.nb.select(1)
            self.refresh_jobs()
        self.run_bg('Repair job', lambda: self.studio.run_job(pid, ai_enabled=ai, approver=self.approver,
                                                             progress=progress), done)

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
        for text, cmd in [('Before / After Diff', self.show_diff), ('Open Evidence Folder', self.open_evidence),
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
            open_path(self.studio.job_evidence_dir(self.selected_job()))
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
            open_path(out)
        except Exception as e:
            messagebox.showerror('Export refused', str(e))
        self.refresh_jobs()

    # ---------------------------------------------------------------- builders
    def _builders_tab(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text='3. New Product Builders')
        bar = ttk.Frame(f)
        bar.pack(fill='x')
        for text, cmd in [('New Power Tool Build (blueprint)…', lambda: self.new_build('power_tool')),
                          ('New Lil Dr. Byrd Build (blueprint)…', lambda: self.new_build('lil_dr_byrd')),
                          ('Build Next Module/Chapter', self.build_next), ('Approve Selected Unit…', self.approve_unit),
                          ('Assemble & Import for QA', self.assemble), ('Register Approved Asset…', self.register_asset)]:
            ttk.Button(bar, text=text, command=cmd).pack(side='left', padx=2)
        self.btree = ttk.Treeview(f, columns=('status', 'detail'), show='tree headings', height=14)
        self.btree.heading('#0', text='build / unit')
        self.btree.heading('status', text='status')
        self.btree.heading('detail', text='verification / assets')
        self.btree.column('#0', width=260)
        self.btree.column('status', width=260)
        self.btree.column('detail', width=520)
        self.btree.pack(fill='both', expand=True, pady=6)
        self.assets_lbl = ttk.Label(f, text='')
        self.assets_lbl.pack(anchor='w')

    def refresh_builds(self):
        self.btree.delete(*self.btree.get_children())
        for s in self.studio.builds():
            node = self.btree.insert('', 'end', iid=s['id'], text=f'{s["kind"]}  {s["id"]}', open=True)
            for u in s['order']:
                x = s['units'][u]
                detail = (f'incorrect {x.get("incorrect", "-")}, unverified {x.get("unverified", "-")}, '
                          f'blocked assets {len(x.get("blocked_assets", []))}, template '
                          f'{(x.get("template") or {}).get("template_status", "-")}')
                self.btree.insert(node, 'end', iid=f'{s["id"]}::{u}', text=u, values=(x['status'], detail))
        reg = self.studio.asset_registry()
        self.assets_lbl.config(text='Approved assets: ' + (', '.join(f'{k} ({v["kind"]})' for k, v in reg.items()) or
                                                          'none registered (Lil Dr. Byrd mascot and ByrdWay template required for release)'))

    def _sel_build(self):
        s = self.btree.selection()
        if not s:
            raise ValueError('Select a build or unit')
        return s[0].split('::')

    def new_build(self, kind):
        f = filedialog.askopenfilename(title='Blueprint JSON', filetypes=[('Blueprint', '*.json')])
        if f:
            try:
                b = self.studio.new_build(f, kind)
                self.log_line(f'Build {b.id} created ({kind})')
                self.refresh_builds()
            except Exception as e:
                messagebox.showerror('Blueprint rejected', str(e))

    def build_next(self):
        try:
            bid = self._sel_build()[0]
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        self.run_bg('Build', lambda: self.studio.build_next(bid),
                    lambda r: self.log_line(f'Built {r[0]}: {r[1]["status"] if r[1] else "all units approved"}'))

    def approve_unit(self):
        try:
            sel = self._sel_build()
            if len(sel) != 2:
                raise ValueError('Select a module/chapter row')
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        bid, unit = sel
        st = [s for s in self.studio.builds() if s['id'] == bid][0]['units'][unit]
        attest = False
        if st['status'] == 'NEEDS_OWNER_REVIEW':
            attest = messagebox.askyesno('Owner review', 'Some items are unverified or AI-drafted. '
                                         'Have you personally reviewed every one?')
        if messagebox.askyesno('Approve', f'Approve {unit}? Open it first to review: {st.get("output")}'):
            try:
                self.studio.approve_unit(bid, unit, True, attest)
            except Exception as e:
                messagebox.showerror('Approval refused', str(e))
        self.refresh_builds()

    def assemble(self):
        try:
            bid = self._sel_build()[0]
        except ValueError as e:
            return messagebox.showinfo('Select', str(e))
        if messagebox.askyesno('Assemble', 'Package all approved units and import as a product for Release QA?'):
            self.run_bg('Assemble', lambda: self.studio.assemble_and_import(bid, True),
                        lambda m: self.log_line(f'Assembled and imported {m["name"]}; run a Repair & Verify job for QA'))

    def register_asset(self):
        f = filedialog.askopenfilename(title='Approved asset file')
        if not f:
            return
        aid = simpledialog.askstring('Asset id', 'Asset id (e.g. lil_dr_byrd, byrdway_template):')
        kind = simpledialog.askstring('Kind', 'Kind: mascot, logo, template, illustration, font, reference_product')
        if aid and kind and messagebox.askyesno('Confirm', 'I am the owner and this is an APPROVED asset.'):
            try:
                self.studio.register_asset(f, aid.strip(), kind.strip(), explicit=True)
            except Exception as e:
                messagebox.showerror('Asset rejected', str(e))
            self.refresh_builds()

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
        self.cost_lbl.config(text=(f'API key configured: {"YES" if self.studio.api_key_configured() else "NO (AI features disabled; local audits work offline)"}\n'
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


if __name__ == '__main__':
    App().mainloop()
