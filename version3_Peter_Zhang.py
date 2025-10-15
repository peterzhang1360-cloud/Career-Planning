#version 3: refactor, add persistence, improve UI and error handling    
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import re, datetime, csv, os, json, sys

STATE_FILE = "gradus_state.json"

COURSES = {"Science": 280, "Commerce": 210, "Engineering": 260}
CAREERS  = {
    "Science": ["Biologist", "Lab Technician"],
    "Commerce": ["Accountant", "Economist"],
    "Engineering": ["Civil Engineer", "Software Developer"],
}
FAQ = {
    "What is NCEA?": "NCEA is New Zealand’s main school qualification.",
    "What is a rank score?": "It's a number based on your Level 3 results for uni entry.",
}

# ------------ tiny ChatBot ------------
class ChatBot:
    def __init__(self): self.name=None; self.field=None
    def reply(self, text:str)->str:
        t=text.strip()
        if not t: return ""
        if t.lower()=="/help":
            return "Commands: /help /clear /save\nTry: I like Science; My score is 300 for Engineering; What is NCEA?"
        if "name is" in t.lower():
            self.name = re.split(r"name is", t, flags=re.I)[-1].strip().split()[0].capitalize()
            return f"Hi {self.name}! What are you into (Science/Commerce/Engineering)?"
        m=re.search(r"(science|commerce|engineering)", t, re.I)
        if "like" in t.lower() and m:
            self.field=m.group(1).capitalize()
            return "Careers in "+self.field+": "+", ".join(CAREERS[self.field])
        if "score" in t.lower():
            sm=re.search(r"(\d+)", t); cm=m or re.search(r"(science|commerce|engineering)", t, re.I)
            if sm and cm:
                s=int(sm.group()); c=cm.group(1).capitalize(); need=COURSES[c]
                return f"✔ Enough for {c} (need {need})." if s>=need else f"✘ Need {need-s} more for {c}."
        for q,a in FAQ.items():
            if q.lower().replace("?","") in t.lower(): return a
        if self.field and re.search(r"(career|job|suggest)", t, re.I):
            return "More: "+", ".join(CAREERS[self.field])
        return "I’m FROST 🤖 Ask NCEA / rank score / careers. Type /help."

# ------------ App Shell ------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gradus"); self.geometry("960x640"); self.minsize(860,560)
        self.dark=False; self.username="Guest"
        self.chat_history = ""          # for export / persistence
        self.grades = []                # list of dict for export / persistence
        self._build_style()

        # Layout scaffold
        root = ttk.Frame(self); root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1); root.rowconfigure(1, weight=1)

        # Sidebar
        side = ttk.Frame(root, padding=10); side.grid(row=0,column=0,rowspan=2,sticky="ns")
        ttk.Label(side, text="Gradus", font=("Segoe UI",16,"bold")).pack(anchor="w", pady=(4,2))
        ttk.Label(side, text="NZ study • career helper", style="Sub.TLabel").pack(anchor="w", pady=(0,8))
        for name,cmd in [("🏠  Home",self.to_home),
                         ("📏  Check",self.to_check),
                         ("🧭  Careers",self.to_career),
                         ("❄️  FROST",self.to_frost),
                         ("📄  Grades",self.to_grades),
                         ("👤  Profile",self.to_profile)]:
            ttk.Button(side, text=name, command=cmd).pack(fill="x", pady=4)
        ttk.Separator(side).pack(fill="x", pady=8)
        self.user_lbl = ttk.Label(side, text=f"User: {self.username}", style="Sub.TLabel")
        self.user_lbl.pack(anchor="w")
        ttk.Button(side, text="Logout", command=self.logout).pack(fill="x", pady=(6,0))

        # Header
        header = ttk.Frame(root, padding=(10,10,10,6)); header.grid(row=0,column=1,sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header,text="Gradus",style="Header.TLabel").grid(row=0,column=0,sticky="w")
        ttk.Label(header,text="Fast checks • Career ideas • FROST chat",style="Sub.TLabel").grid(row=1,column=0,sticky="w")
        ttk.Button(header,text="🌙",width=3,command=self.toggle_theme).grid(row=0,column=1,rowspan=2,sticky="e")

        # Content + Status
        self.host = ttk.Frame(root, padding=10, style="Card.TFrame"); self.host.grid(row=1,column=1,sticky="nsew")
        self.status = tk.StringVar(value="Ready. Ctrl+S save chat • Ctrl+L clear chat • Ctrl+E export CSV • Ctrl+Q quit")
        ttk.Label(root, textvariable=self.status, anchor="w", padding=(10,4)).grid(row=2,column=0,columnspan=2,sticky="ew")

        # Keyboard shortcuts
        self.bind_all("<Control-s>", lambda e: self._delegate_shortcut("save_chat"))
        self.bind_all("<Control-l>", lambda e: self._delegate_shortcut("clear_chat"))
        self.bind_all("<Control-e>", lambda e: self._delegate_shortcut("export_csv"))
        self.bind_all("<Control-q>", lambda e: self.on_quit())

        # Pages
        self.pages = {cls.__name__: cls(self.host, self)
                      for cls in (Home, Check, Careers, FROST, Grades, Profile)}
        for w in self.pages.values(): w.grid(row=0,column=0,sticky="nsew")

        # Persistence
        self._load_state()

        # Navigation default
        self.to_home()

        # Close hook
        self.protocol("WM_DELETE_WINDOW", self.on_quit)

    # theme
    def _build_style(self):
        s=ttk.Style(self)
        try: s.theme_use("clam")
        except: pass
        self._apply_colors()
        s.configure("Header.TLabel", font=("Segoe UI",18,"bold"), background=self.bg)
        s.configure("Sub.TLabel",    font=("Segoe UI",10), foreground=self.sub, background=self.bg)
        s.configure("TFrame", background=self.bg)
        s.configure("Card.TFrame", background=self.card, relief="groove", borderwidth=1)
        s.configure("Accent.TButton", foreground="white", background=self.accent)
        s.map("Accent.TButton", background=[("active", self.accent2)])

    def _apply_colors(self):
        if self.dark:
            self.bg="#0f172a"; self.card="#111827"; self.sub="#9ca3af"; self.accent="#6366f1"; self.accent2="#4f46e5"; fg="#e5e7eb"
        else:
            self.bg="#f7f7fb"; self.card="#ffffff"; self.sub="#555"; self.accent="#4f46e5"; self.accent2="#4338ca"; fg="#111827"
        self.configure(bg=self.bg); self.option_add("*Foreground", fg); self.option_add("*Background", self.bg)

    def toggle_theme(self):
        self.dark=not self.dark; self._build_style()
        self.set_status("Theme: Dark" if self.dark else "Theme: Light")
        self._save_state()

    # nav + status + logout
    def _show(self, name): self.pages[name].tkraise()
    def to_home(self):   self._show("Home")
    def to_check(self):  self._show("Check")
    def to_career(self): self._show("Careers")
    def to_frost(self):  self._show("FROST")
    def to_grades(self): self._show("Grades")
    def to_profile(self):self._show("Profile")
    def set_status(self, msg): self.status.set(msg)

    def logout(self):
        self.username = "Guest"
        self.user_lbl.config(text=f"User: {self.username}")
        self.set_status("Logged out.")
        self._save_state()

    # persistence
    def _load_state(self):
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE,"r",encoding="utf-8") as f:
                    data=json.load(f)
                self.dark = bool(data.get("dark", self.dark))
                self._build_style()
                self.username = data.get("username","Guest")
                self.user_lbl.config(text=f"User: {self.username}")
                self.chat_history = data.get("chat_history","")
                self.grades = data.get("grades",[])
                # hydrate grades into tree if page already built later
                # defer to Grades.refresh()
                self.set_status("State loaded.")
        except Exception as e:
            self.set_status(f"Load failed: {e}")

    def _save_state(self):
        try:
            data = {
                "dark": self.dark,
                "username": self.username,
                "chat_history": self.chat_history,
                "grades": self.grades
            }
            with open(STATE_FILE,"w",encoding="utf-8") as f:
                json.dump(data,f,indent=2)
        except Exception as e:
            self.set_status(f"Save failed: {e}")

    def on_quit(self):
        self._save_state()
        self.destroy()

    # shortcuts delegate to the active page when applicable
    def _delegate_shortcut(self, action):
        cur = self.pages.get("FROST")
        if action=="save_chat" and cur and cur.winfo_ismapped():
            cur.save_chat(); return "break"
        if action=="clear_chat" and cur and cur.winfo_ismapped():
            cur.clear(); return "break"
        grd = self.pages.get("Grades")
        if action=="export_csv" and grd and grd.winfo_ismapped():
            grd.export_csv(); return "break"

# ------------ Pages ------------
class Home(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        ttk.Label(self,text="Gradus",style="Header.TLabel").pack(anchor="w",pady=(0,6))
        ttk.Label(self,text="• Welcome to Gradus\n• Use the sidebar to open modules\n• Status bar shows tips & saves",
                  style="Sub.TLabel", justify="left").pack(anchor="w")
        ttk.Separator(self).pack(fill="x", pady=10)
        ttk.Label(self,text="[Auth Gate if not signed in]",style="Sub.TLabel").pack(anchor="w")

class Check(ttk.Frame):# simple uni entry check
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app
        ttk.Label(self,text="University Entry Check",style="Header.TLabel").grid(row=0,column=0,columnspan=4,sticky="w")
        ttk.Label(self,text="Rank score").grid(row=1,column=0,sticky="e",padx=6,pady=8)
        self.e = ttk.Entry(self,width=10); self.e.grid(row=1,column=1,sticky="w")
        ttk.Label(self,text="Target course").grid(row=1,column=2,sticky="e",padx=6)
        self.var=tk.StringVar(value=list(COURSES.keys())[0])
        ttk.Combobox(self,textvariable=self.var,values=list(COURSES.keys()),state="readonly",width=18).grid(row=1,column=3,sticky="w")
        ttk.Button(self,text="Check",style="Accent.TButton",command=self.run).grid(row=2,column=0,pady=6,sticky="w")

    def run(self):
        try:
            s=int(self.e.get()); c=self.var.get(); need=COURSES[c]
            if s>=need:
                messagebox.showinfo("Result", f"✔ Enough for {c} (need {need}).")
            else:
                messagebox.showwarning("Result", f"✘ Need {need-s} more for {c}.")
        except ValueError:
            messagebox.showerror("Error","Enter a whole number.")

class Careers(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        ttk.Label(self,text="Career Ideas",style="Header.TLabel").pack(anchor="w")
        row=ttk.Frame(self); row.pack(anchor="w", pady=8)
        self.var=tk.StringVar(value=list(CAREERS.keys())[0])
        ttk.Label(row,text="Interest").pack(side="left",padx=(0,6))
        ttk.Combobox(row,textvariable=self.var,values=list(CAREERS.keys()),state="readonly",width=20).pack(side="left")
        ttk.Button(row,text="Suggest",style="Accent.TButton",command=self.suggest).pack(side="left",padx=8)
        self.out=tk.Text(self,height=10,wrap="word",borderwidth=0)
        self.out.pack(fill="both",expand=True); self.out.configure(state="disabled")

    def suggest(self):
        f=self.var.get()
        self.out.configure(state="normal"); self.out.delete("1.0","end")
        self.out.insert("end","• "+ "\n• ".join(CAREERS[f])); self.out.configure(state="disabled")

class FROST(ttk.Frame):
    def __init__(self, parent, app:App):
        super().__init__(parent, padding=12); self.app=app; self.bot=ChatBot()
        ttk.Label(self,text="FROST Chat",style="Header.TLabel").grid(row=0,column=0,sticky="w")
        ttk.Label(self,text="Ask NCEA • rank score • careers. Enter=send; Shift+Enter=new line.",
                  style="Sub.TLabel").grid(row=1,column=0,sticky="w",pady=(0,6))
        chips=ttk.Frame(self); chips.grid(row=2,column=0,sticky="w",pady=(0,4))
        for t in ["What is NCEA?","I like Science","My score is 300 for Engineering"]:
            ttk.Button(chips,text=t,command=lambda s=t:self._quick(s)).pack(side="left",padx=4)

        self.chat=scrolledtext.ScrolledText(self,wrap="word",height=16,state="disabled",borderwidth=0)
        self.chat.grid(row=3,column=0,sticky="nsew"); self.rowconfigure(3,weight=1)
        self.chat.tag_config("user",foreground="#1f2937")
        self.chat.tag_config("bot",foreground="#0b5394")
        self.chat.tag_config("sys",foreground="#6b7280")

        row=ttk.Frame(self); row.grid(row=4,column=0,sticky="ew",pady=(6,0)); row.columnconfigure(0,weight=1)
        self.entry=tk.Text(row,height=3,wrap="word"); self.entry.grid(row=0,column=0,sticky="ew")
        btns=ttk.Frame(row); btns.grid(row=0,column=1,sticky="e",padx=(6,0))
        ttk.Button(btns,text="Send ▶",style="Accent.TButton",command=self.send).pack(side="left")
        ttk.Button(btns,text="Clear",command=self.clear).pack(side="left",padx=6)
        ttk.Button(btns,text="Copy",command=self.copy_chat).pack(side="left",padx=6)
        self.entry.bind("<Return>", self._on_enter); self.entry.bind("<Shift-Return>", lambda e: None)
        self.entry.bind("<Control-s>", self.save_chat); self.entry.bind("<Control-l>", lambda e: (self.clear(), "break"))
        self._append("sys","Hi, I’m FROST. /help for help.")

    def _append(self, role, msg):
        self.chat.configure(state="normal")
        ts=datetime.datetime.now().strftime("%H:%M")
        lab={"user":"You","bot":"FROST","sys":"System"}[role]
        line=f"[{ts}] {lab}: {msg}\n"
        self.chat.insert("end", line, role)
        self.app.chat_history += line
        self.chat.configure(state="disabled"); self.chat.see("end")
        self.app._save_state()

    def _get(self): return self.entry.get("1.0","end").strip()
    def _clr_input(self): self.entry.delete("1.0","end")
    def _quick(self, text): self._append("user", text); self._append("bot", self.bot.reply(text))

    def _on_enter(self, e):
        if e.state & 0x0001: return
        self.send(); return "break"

    def send(self, event=None):
        t=self._get()
        if not t: return
        if t.lower()=="/clear": self.clear(); return
        if t.lower()=="/save": self.save_chat(); return
        self._append("user", t); self._append("bot", self.bot.reply(t))
        self._clr_input(); self.app.set_status("Sent. Ctrl+S save, Ctrl+L clear.")

    def clear(self):
        if not messagebox.askyesno("Confirm","Clear the chat?"): return
        self.chat.configure(state="normal"); self.chat.delete("1.0","end"); self.chat.configure(state="disabled")
        self._clr_input(); self._append("sys","Chat cleared."); self.app.set_status("Chat cleared.")
        self.app.chat_history = ""
        self.app._save_state()

    def copy_chat(self):
        try:
            data = self.app.chat_history or self.chat.get("1.0","end")
            self.clipboard_clear(); self.clipboard_append(data)
            self.app.set_status("Chat copied to clipboard.")
        except Exception as e:
            self.app.set_status(f"Copy failed: {e}")

    def save_chat(self, event=None):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text","*.txt")], initialfile="frost_chat.txt")
        if not path: return
        try:
            with open(path,"w",encoding="utf-8") as f: f.write(self.app.chat_history or self.chat.get("1.0","end"))
            self.app.set_status(f"Saved chat → {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

class Grades(ttk.Frame):
    def __init__(self, parent, app:App):
        super().__init__(parent, padding=12); self.app=app
        ttk.Label(self,text="Grades (NCEA)",style="Header.TLabel").grid(row=0,column=0,sticky="w")

        # filter/search
        top=ttk.Frame(self); top.grid(row=1,column=0,sticky="ew",pady=(2,6)); top.columnconfigure(1,weight=1)
        ttk.Label(top,text="Search").grid(row=0,column=0,sticky="e",padx=4)
        self.q = ttk.Entry(top,width=30); self.q.grid(row=0,column=1,sticky="ew")
        ttk.Button(top,text="Apply",command=self.apply_filter).grid(row=0,column=2,padx=4)
        ttk.Button(top,text="Reset",command=self.reset_filter).grid(row=0,column=3)

        # form row
        form=ttk.Frame(self); form.grid(row=2,column=0,sticky="w",pady=6)
        ttk.Label(form,text="Title").grid(row=0,column=0,sticky="e"); self.e_title=ttk.Entry(form,width=24); self.e_title.grid(row=0,column=1,padx=6)
        ttk.Label(form,text="Level").grid(row=0,column=2,sticky="e"); self.var_lvl=tk.IntVar(value=3); ttk.Spinbox(form,from_=1,to=3,textvariable=self.var_lvl,width=5).grid(row=0,column=3,padx=6)
        ttk.Label(form,text="Credits").grid(row=0,column=4,sticky="e"); self.e_cred=ttk.Entry(form,width=6); self.e_cred.grid(row=0,column=5,padx=6)
        ttk.Label(form,text="Grade").grid(row=0,column=6,sticky="e"); self.var_g=tk.StringVar(value="A")
        ttk.Combobox(form,textvariable=self.var_g,values=["A","M","E","N"],state="readonly",width=5).grid(row=0,column=7,padx=6)
        ttk.Button(form,text="Add",style="Accent.TButton",command=self.add).grid(row=0,column=8,padx=(8,0))

        # table
        self.tree=ttk.Treeview(self,columns=("Title","Level","Credits","Grade"),show="headings",height=11)
        for col,w in [("Title",380),("Level",60),("Credits",80),("Grade",80)]:
            self.tree.heading(col,text=col); self.tree.column(col,width=w,anchor="center")
        self.tree.grid(row=3,column=0,sticky="nsew",pady=6); self.rowconfigure(3,weight=1)

        # totals + actions
        self.lbl_tot=ttk.Label(self,text="Totals: L1 0 | L2 0 | L3 0 | All 0"); self.lbl_tot.grid(row=4,column=0,sticky="w")
        btns=ttk.Frame(self); btns.grid(row=5,column=0,sticky="w",pady=6)
        ttk.Button(btns,text="Import CSV",command=self.import_csv).pack(side="left")
        ttk.Button(btns,text="Export CSV",command=self.export_csv).pack(side="left",padx=6)
        ttk.Button(btns,text="Remove selected",command=self.remove_sel).pack(side="left",padx=6)

        self.refresh()

    def refresh(self, rows=None):
        # clear
        for iid in self.tree.get_children(): self.tree.delete(iid)
        data = rows if rows is not None else self.app.grades
        for g in data:
            self.tree.insert("", "end", values=(g["title"], g["level"], g["credits"], g["grade"]))
        self._update_totals()

    def apply_filter(self):
        q = self.q.get().strip().lower()
        if not q: self.refresh(); return
        rows=[g for g in self.app.grades if q in g["title"].lower()]
        self.refresh(rows)
    def reset_filter(self):# reset search
        self.q.delete(0,"end"); self.refresh()
    def add(self):# add new grade
        title=self.e_title.get().strip()
        if not title: messagebox.showwarning("Missing","Enter title."); return
        try:
            credits=int(self.e_cred.get())
            level=int(self.var_lvl.get()); grade=self.var_g.get().upper()
        except ValueError:
            messagebox.showwarning("Invalid","Level/Credits must be numbers."); return
        if level not in (1,2,3) or not (1<=credits<=24):
            messagebox.showwarning("Invalid","Level 1–3; Credits 1–24."); return
        if grade not in ("A","M","E","N"):
            messagebox.showwarning("Invalid","Grade must be A/M/E/N."); return
        self.app.grades.append({"title":title,"level":level,"credits":credits,"grade":grade})
        self.e_title.delete(0,"end"); self.e_cred.delete(0,"end")
        self.refresh(); self.app._save_state()

    def remove_sel(self):# remove selected rows
        sel=self.tree.selection()
        if not sel: return
        if not messagebox.askyesno("Confirm","Remove selected record(s)?"): return
        # rebuild from remaining rows
        keep=[]
        ids=set(sel)
        for iid in self.tree.get_children():
            if iid in ids: continue
            t,l,c,g = self.tree.item(iid,"values")
            keep.append({"title":t,"level":int(l),"credits":int(c),"grade":g})
        self.app.grades=keep
        self.refresh(); self.app._save_state()
    def _update_totals(self):# compute & show totals
        lv={1:0,2:0,3:0}; total=0
        for iid in self.tree.get_children():
            _, l, c, _ = self.tree.item(iid,"values")
            l=int(l); c=int(c); lv[l]+=c; total+=c
        self.lbl_tot.config(text=f"Totals: L1 {lv[1]} | L2 {lv[2]} | L3 {lv[3]} | All {total}")
    def export_csv(self):# export to CSV
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")], initialfile="grades.csv")
        if not path: return
        try:
            with open(path,"w",newline="",encoding="utf-8") as f:
                w=csv.writer(f); w.writerow(["Title","Level","Credits","Grade"])
                for g in self.app.grades: w.writerow([g["title"],g["level"],g["credits"],g["grade"]])
            self.app.set_status(f"Exported CSV → {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
    def import_csv(self):# import from CSV
        path = filedialog.askopenfilename(filetypes=[("CSV","*.csv")])
        if not path: return
        try:
            with open(path,"r",encoding="utf-8") as f:
                r=csv.DictReader(f)
                loaded=[]
                for row in r:
                    title=row.get("Title","").strip()
                    level=int(row.get("Level","0"))
                    credits=int(row.get("Credits","0"))
                    grade=row.get("Grade","A").strip().upper()
                    if title and level in (1,2,3) and 1<=credits<=24 and grade in ("A","M","E","N"):
                        loaded.append({"title":title,"level":level,"credits":credits,"grade":grade})
            self.app.grades.extend(loaded)
            self.refresh(); self.app._save_state()
            self.app.set_status(f"Imported {len(loaded)} rows.")
        except Exception as e:
            messagebox.showerror("Import failed", str(e))
class Profile(ttk.Frame):# user profile & settings
    def __init__(self, parent, app:App):
        super().__init__(parent, padding=16); self.app=app
        ttk.Label(self,text="Profile",style="Header.TLabel").grid(row=0,column=0,columnspan=2,sticky="w")
        ttk.Label(self,text="Display name").grid(row=1,column=0,sticky="e",padx=6,pady=6)
        self.name_var=tk.StringVar(value=app.username)
        ttk.Entry(self,textvariable=self.name_var,width=24).grid(row=1,column=1,sticky="w")
        ttk.Label(self,text="Theme").grid(row=2,column=0,sticky="e",padx=6,pady=6)
        self.theme=tk.StringVar(value="dark" if app.dark else "light")
        row=ttk.Frame(self); row.grid(row=2,column=1,sticky="w")
        ttk.Radiobutton(row,text="Light",value="light",variable=self.theme).pack(side="left")
        ttk.Radiobutton(row,text="Dark", value="dark", variable=self.theme).pack(side="left", padx=8)
        ttk.Button(self,text="Apply",style="Accent.TButton",command=self.apply).grid(row=3,column=1,sticky="w",pady=6)
        ttk.Separator(self).grid(row=4,column=0,columnspan=2,sticky="ew",pady=10)
        ttk.Button(self,text="Export my data",command=self.export_all).grid(row=5,column=1,sticky="w")

    def apply(self):# apply changes
        self.app.username = self.name_var.get().strip() or "Guest"
        self.app.user_lbl.config(text=f"User: {self.app.username}")
        want_dark = (self.theme.get()=="dark")
        if want_dark != self.app.dark:
            self.app.toggle_theme()
        self.app.set_status("Profile applied.")
        self.app._save_state()

    def export_all(self):# export chat + grades to folder
        folder = filedialog.askdirectory()
        if not folder: return
        try:
            # export chat
            chat_path=os.path.join(folder,"frost_chat.txt")
            with open(chat_path,"w",encoding="utf-8") as f: f.write(self.app.chat_history)
            # export grades
            grades_path=os.path.join(folder,"grades.csv")
            with open(grades_path,"w",newline="",encoding="utf-8") as f:
                w=csv.writer(f); w.writerow(["Title","Level","Credits","Grade"])
                for g in self.app.grades: w.writerow([g["title"],g["level"],g["credits"],g["grade"]])
            self.app.set_status(f"Exported chat & grades → {os.path.basename(folder)}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

# ------------ Run ------------
if __name__=="__main__":
    App().mainloop()

