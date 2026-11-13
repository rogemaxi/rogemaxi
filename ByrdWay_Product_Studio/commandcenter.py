"""BYRD POWERHOUSE COMMAND CENTER - the first screen of the app.

Every one of the 22 agents is a card with its assignment, today's work (computed from the real workspace),
its last recorded action, its honest status and a RUN button that starts the agent's real job. A scoreboard
and a live activity feed sit above and beside the cards. Nothing here publishes, sends or spends on its own.
"""
import json
import tkinter as tk
from tkinter import ttk

NAVY, NAVY2, GOLD, CREAM, INK, MUTED = '#0f2240', '#1b3561', '#f2c14e', '#fbf7ed', '#16324a', '#5b6b7d'
GREEN, AMBER, RED, WHITE = '#2e8b57', '#d99a06', '#c0392b', '#ffffff'
CHIP = {'WORKING': GREEN, 'PARTIAL': AMBER, 'MISSING': RED}
FONT = 'Segoe UI'


def _status(a):
    st = a['status']
    if isinstance(st, dict):
        vals = set(st.values())
        return 'WORKING' if vals == {'WORKING'} else 'MISSING' if 'MISSING' in vals else 'PARTIAL'
    return st


class CommandCenter(tk.Frame):
    COLS = 3

    def __init__(self, parent, app):
        super().__init__(parent, bg=CREAM)
        self.app = app
        self.data = None
        self._build_shell()
        self.refresh()

    # ------------------------------------------------------------------ layout
    def _build_shell(self):
        head = tk.Frame(self, bg=NAVY, padx=16, pady=10)
        head.pack(fill='x')
        left = tk.Frame(head, bg=NAVY)
        left.pack(side='left', fill='x', expand=True)
        tk.Label(left, text='BYRD POWERHOUSE  COMMAND CENTER', bg=NAVY, fg=GOLD, font=(FONT, 20, 'bold')).pack(anchor='w')
        tk.Label(left, text='22 agents  |  Engineering Division (12)  +  Revenue & Media Division (10)  |  '
                            'You approve every release, post, price and payment', bg=NAVY, fg=WHITE, font=(FONT, 10)).pack(anchor='w')
        right = tk.Frame(head, bg=NAVY)
        right.pack(side='right')
        self.stage_lbl = tk.Label(right, text='', bg=NAVY, fg=WHITE, font=(FONT, 10, 'bold'), justify='right')
        self.stage_lbl.pack(anchor='e')
        tk.Button(right, text='Refresh', command=self.refresh, bg=GOLD, fg=NAVY, relief='flat', font=(FONT, 9, 'bold'),
                  padx=10).pack(anchor='e', pady=(4, 0))

        self.kpi = tk.Frame(self, bg=CREAM, padx=10, pady=8)
        self.kpi.pack(fill='x')

        body = tk.Frame(self, bg=CREAM)
        body.pack(fill='both', expand=True, padx=10, pady=(0, 8))
        side = tk.Frame(body, bg=WHITE, width=380, highlightbackground='#d9d2c0', highlightthickness=1)
        side.pack(side='right', fill='y', padx=(8, 0))
        side.pack_propagate(False)
        tk.Label(side, text='AGENT OUTPUT', bg=WHITE, fg=NAVY, font=(FONT, 11, 'bold')).pack(anchor='w', padx=10, pady=(8, 2))
        self.out = tk.Text(side, height=16, wrap='word', font=(FONT, 9), bg=WHITE, fg=INK, relief='flat', padx=8)
        self.out.pack(fill='both', expand=True)
        tk.Label(side, text='LIVE ACTIVITY', bg=WHITE, fg=NAVY, font=(FONT, 11, 'bold')).pack(anchor='w', padx=10, pady=(8, 2))
        self.feed = tk.Listbox(side, height=12, font=(FONT, 8), bg=CREAM, fg=INK, relief='flat', activestyle='none')
        self.feed.pack(fill='both', expand=False, padx=6, pady=(0, 8))

        wrap = tk.Frame(body, bg=CREAM)
        wrap.pack(side='left', fill='both', expand=True)
        self.canvas = tk.Canvas(wrap, bg=CREAM, highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.grid_frame = tk.Frame(self.canvas, bg=CREAM)
        self._win = self.canvas.create_window((0, 0), window=self.grid_frame, anchor='nw')
        self.grid_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.bind_all('<MouseWheel>', self._wheel)

    def _wheel(self, e):
        try:
            if str(self.app.nb.select()) == str(self):
                self.canvas.yview_scroll(int(-e.delta / 120), 'units')
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ content
    def refresh(self):
        try:
            self.data = self.app.studio.command_center()
        except Exception as e:                      # never let the dashboard crash the app
            self.say(f'Command Center could not read the workspace: {e}')
            return
        d = self.data
        st, bn = d.get('stage') or {}, d.get('bottleneck') or {}
        self.stage_lbl.config(text=(f"Scaling stage {st.get('stage', '?')}: {st.get('name', '?')}"
                                    + (' (provisional)' if st.get('provisional') else '')
                                    + f"\nToday's bottleneck: {bn.get('constraint', '?')}"))
        for w in self.kpi.winfo_children():
            w.destroy()
        for i, (label, val) in enumerate(d['kpis']):
            t = tk.Frame(self.kpi, bg=WHITE, padx=10, pady=6, highlightbackground='#d9d2c0', highlightthickness=1)
            t.grid(row=0, column=i, sticky='nsew', padx=3)
            self.kpi.columnconfigure(i, weight=1)
            tk.Label(t, text=str(val), bg=WHITE, fg=NAVY, font=(FONT, 16, 'bold')).pack(anchor='w')
            tk.Label(t, text=label, bg=WHITE, fg=MUTED, font=(FONT, 8)).pack(anchor='w')
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self._section('ENGINEERING DIVISION', 'Detect -> Repair -> QA loop -> Learn -> Build -> Build QA -> Chief Judge',
                      d['engineering'], 'eng')
        self._section('REVENUE & MEDIA DIVISION', d['targets'], d['revenue'], 'rev')
        self.feed.delete(0, 'end')
        for a in d['feed']:
            self.feed.insert('end', f"{a.get('ts', '')[5:16].replace('T', ' ')}  {a.get('role', '')}: {a.get('message', '')}")
        if not d['feed']:
            self.feed.insert('end', 'No agent activity yet - press RUN on any agent.')

    def _section(self, title, sub, agents, kind):
        hdr = tk.Frame(self.grid_frame, bg=CREAM)
        hdr.pack(fill='x', pady=(10, 4))
        tk.Label(hdr, text=title, bg=CREAM, fg=NAVY, font=(FONT, 13, 'bold')).pack(anchor='w')
        tk.Label(hdr, text=sub, bg=CREAM, fg=MUTED, font=(FONT, 9), wraplength=900, justify='left').pack(anchor='w')
        g = tk.Frame(self.grid_frame, bg=CREAM)
        g.pack(fill='x')
        for c in range(self.COLS):
            g.columnconfigure(c, weight=1, uniform='card')
        for i, a in enumerate(agents):
            self._card(g, a, kind, i).grid(row=i // self.COLS, column=i % self.COLS, sticky='nsew', padx=4, pady=4)

    def _card(self, parent, a, kind, i):
        status = _status(a)
        c = tk.Frame(parent, bg=WHITE, highlightbackground=GOLD if kind == 'rev' else NAVY2, highlightthickness=2, padx=10, pady=8)
        top = tk.Frame(c, bg=WHITE)
        top.pack(fill='x')
        num = a['id'] if kind == 'eng' else 12 + i + 1
        tk.Label(top, text=f' {num} ', bg=NAVY if kind == 'eng' else GOLD, fg=GOLD if kind == 'eng' else NAVY,
                 font=(FONT, 10, 'bold')).pack(side='left')
        tk.Label(top, text=' ' + a['name'], bg=WHITE, fg=NAVY, font=(FONT, 11, 'bold')).pack(side='left')
        tk.Label(top, text=f' {status} ', bg=CHIP.get(status, MUTED), fg=WHITE, font=(FONT, 8, 'bold')).pack(side='right')
        if kind == 'eng':
            tk.Label(c, text=a['group'], bg=WHITE, fg=MUTED, font=(FONT, 8)).pack(anchor='w')
        tk.Label(c, text=a['job'], bg=WHITE, fg=INK, font=(FONT, 9), wraplength=300, justify='left').pack(anchor='w', pady=(4, 2))
        tk.Label(c, text='TODAY: ' + a['today'], bg=WHITE, fg=NAVY2, font=(FONT, 9, 'bold'), wraplength=300,
                 justify='left').pack(anchor='w')
        tk.Label(c, text='LAST: ' + a['last'], bg=WHITE, fg=MUTED, font=(FONT, 8), wraplength=300, justify='left').pack(anchor='w', pady=(2, 4))
        bar = tk.Frame(c, bg=WHITE)
        bar.pack(fill='x')
        tk.Button(bar, text='RUN', bg=NAVY, fg=GOLD, activebackground=NAVY2, activeforeground=GOLD, relief='flat',
                  font=(FONT, 9, 'bold'), padx=14, command=lambda: self.run(a, kind)).pack(side='left')
        tk.Button(bar, text='Details', bg=CREAM, fg=NAVY, relief='flat', font=(FONT, 9), padx=8,
                  command=lambda: self.details(a, kind)).pack(side='left', padx=6)
        return c

    # ------------------------------------------------------------------ actions
    def say(self, text):
        self.out.delete('1.0', 'end')
        self.out.insert('end', text)

    def details(self, a, kind):
        if kind == 'eng':
            fam = '\n'.join(f'  {k}: {v}' for k, v in a['status'].items())
            self.say(f"{a['id']}. {a['name']}  ({a['group']})\n\nASSIGNMENT\n{a['job']}\n\nTODAY\n{a['today']}\n\n"
                     f"STATUS BY PRODUCT FAMILY\n{fam}\n\nCODE\n{a['code']}\n\nLAST ACTION\n{a['last']}")
        else:
            self.say(f"{a['name']}  [{a['status']}]\n\nASSIGNMENT\n{a['job']}\n\nTODAY\n{a['today']}\n\n"
                     f"METHODS APPLIED (strategy library)\n{', '.join(a['methods'])}\n\nLAST ACTION\n{a['last']}")

    ENG_RUN = {1: 'diagnose', 2: 'diagnose', 3: 'diagnose', 4: 'run_job', 5: 'run_job', 6: 'run_job',
               7: 'powerhouse_lessons', 8: 'bp_new', 9: 'build_next', 10: 'assemble', 11: 'construct_next', 12: 'construct_next'}
    REV_RUN = {'video_producer': 'vp_generate', 'social_publisher': 'vp_publish', 'script_storyboard': 'vp_brief'}

    def run(self, a, kind):
        app = self.app
        if kind == 'eng':
            name = self.ENG_RUN[a['id']]
            if name in ('diagnose', 'run_job') and not app.ptree.selection():
                app.nb.select(app.products_frame)
                return app.status.set(f"{a['name']}: choose a product in the Products tab (or Import one), then press RUN again.")
            if name in ('build_next', 'assemble', 'construct_next') and not app.btree.selection():
                app.nb.select(app.builders_frame)
                return app.status.set(f"{a['name']}: choose a build in New Product Builders (or create one from a blueprint).")
            self.say(f"{a['name']} is working...  (see the live activity feed)")
            getattr(app, name)()
            return
        if a['key'] in self.REV_RUN:
            self.say(f"{a['name']} - {a['today']}")
            return getattr(app, self.REV_RUN[a['key']])()

        def done(res):
            L = [f"{a['name'].upper()} - today's assignment"]
            L += [f"  #{x['priority']}: {x['action']}\n     measured by: {x['metric']}  ({', '.join(x['methods'])})" for x in res['assignment']] \
                or ['  (no priority action for this role today)']
            bn = res.get('bottleneck') or {}
            L += ['', f"Bottleneck: {bn.get('constraint')} - {bn.get('why')}", '', 'DELIVERABLES:']
            L += [json.dumps(res['deliverables'], indent=1, ensure_ascii=False, default=str)[:6000]]
            self.say('\n'.join(L))
            self.refresh()
        app.run_bg(a['name'], lambda: app.studio.revenue_role(a['key']), done)
