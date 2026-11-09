"""Run with python app.py. Windows desktop UI, Python standard library."""
import os,tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from engine import workspace,import_product,inventory,create_audit,original_file,save_proposal,ROLES
from ai_roles import run_review

ROOT=workspace(Path.home()/'Documents'/'ByrdWay_Product_Studio')
class Studio(tk.Tk):
 def __init__(self):
  super().__init__();self.title('ByrdWay Product Engineering Studio | Prototype 0.1');self.geometry('950x650')
  self.configure(bg='#f6f8fc');self.products=[]
  top=ttk.Frame(self,padding=12);top.pack(fill='x')
  ttk.Label(top,text='BYRDWAY PRODUCT ENGINEERING STUDIO',font=('Segoe UI',17,'bold')).pack(anchor='w')
  ttk.Label(top,text='Protected originals • Seven specialist roles • Owner approval • No automatic publishing').pack(anchor='w')
  bar=ttk.Frame(self,padding=8);bar.pack(fill='x')
  ttk.Button(bar,text='Import Product',command=self.import_one).pack(side='left',padx=3)
  ttk.Button(bar,text='Local Audit',command=self.audit).pack(side='left',padx=3)
  ttk.Button(bar,text='AI Read-Only Review',command=self.ai_review).pack(side='left',padx=3)
  ttk.Button(bar,text='Create Text Repair Proposal',command=self.proposal).pack(side='left',padx=3)
  ttk.Button(bar,text='Refresh',command=self.refresh).pack(side='left',padx=3)
  ttk.Button(bar,text='Open Workspace',command=self.open_workspace).pack(side='left',padx=3)
  ttk.Label(self,text='Imported products (originals remain unchanged):',padding=8).pack(anchor='w')
  self.lst=tk.Listbox(self,height=8);self.lst.pack(fill='x',padx=12)
  ttk.Label(self,text='Audit and review log:',padding=8).pack(anchor='w')
  self.log=tk.Text(self,wrap='word',font=('Consolas',10));self.log.pack(fill='both',expand=True,padx=12,pady=(0,12))
  self.write('Ready. Import a Power Tool HTML/ZIP or Explainer PDF. API review is optional and incurs usage charges.\n')
  self.refresh()
 def write(self,s):self.log.insert('end',s+'\n');self.log.see('end')
 def refresh(self):
  self.products=inventory(ROOT);self.lst.delete(0,'end')
  for p in self.products:self.lst.insert('end',f"{p['id']} | {p['name']} | LOCKED")
 def selected(self):
  idx=self.lst.curselection()
  if not idx:raise ValueError('Select a product first')
  return self.products[idx[0]]['id']
 def import_one(self):
  f=filedialog.askopenfilename(filetypes=[('Supported files','*.html *.htm *.js *.css *.txt *.md *.json *.pdf *.zip')])
  if f:
   try:p=import_product(f,ROOT);self.refresh();self.write('IMPORTED '+p['name']+' SHA256 '+p['sha256'])
   except Exception as e:messagebox.showerror('Import blocked',str(e))
 def audit(self):
  try:r=create_audit(ROOT,self.selected());self.write('LOCAL AUDIT '+str(r))
  except Exception as e:messagebox.showerror('Audit blocked',str(e))
 def ai_review(self):
  try:
   pid=self.selected();role=simpledialog.askstring('Specialist role','Enter one of:\n'+'\n'.join(ROLES[1:]))
   if not role:return
   if not messagebox.askyesno('API cost approval','This action sends extracted product text to OpenAI and incurs API usage. Continue?'):return
   self.write('Review requested; waiting for response...');self.update()
   response=run_review(ROOT,pid,role)
   out=ROOT/'reports'/f'{pid}_{role.replace(" ","_")}.txt';out.write_text(response,encoding='utf-8')
   self.write(response+'\nSaved review: '+str(out))
  except Exception as e:messagebox.showerror('AI review blocked',str(e))
 def proposal(self):
  try:
   pid=self.selected();src,_=original_file(ROOT,pid)
   if src.suffix.lower() not in {'.html','.htm','.js','.css','.txt','.md','.json'}:raise ValueError('Only editable text source can use this prototype proposal editor. PDFs/ZIPs need source-aware repair.')
   editor=tk.Toplevel(self);editor.title('Review candidate: original is never overwritten');editor.geometry('900x600')
   t=tk.Text(editor,wrap='none');t.pack(fill='both',expand=True)
   t.insert('1.0',src.read_text(encoding='utf-8',errors='replace'))
   def save():
    reason=simpledialog.askstring('Change reason','What verified defect is being corrected?')
    if not reason:return
    rec=save_proposal(ROOT,pid,t.get('1.0','end-1c'),reason)
    self.write('PROPOSAL SAVED (NOT RELEASED): '+rec['candidate']);editor.destroy()
   ttk.Button(editor,text='Save proposed copy (not published)',command=save).pack(pady=5)
  except Exception as e:messagebox.showerror('Proposal blocked',str(e))
 def open_workspace(self):
  import subprocess,sys
  if sys.platform=='win32':os.startfile(ROOT)
  else:subprocess.Popen(['xdg-open',str(ROOT)])
if __name__=='__main__':Studio().mainloop()
