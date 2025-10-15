# file: gradus_twostage.py
# -*- coding: utf-8 -*-
"""
Gradus — two-stage startup:
1) A dedicated LoginApp(Tk) starts first (centered), handles Login/Register
2) On success: destroy LoginApp, then create MainApp(Tk) for the real UI
Also: softer dark theme palette.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import re, datetime, csv, os, json, sys, hashlib, secrets

USERS_FILE  = "gradus_users.json"

COURSES = {"Science": 280, "Commerce": 210, "Engineering": 260}
CAREERS  = {
    "Science": ["Biologist", "Lab Technician", "Chemist", "Physicist"],
    "Commerce": ["Accountant", "Economist", "Financial Analyst", "Auditor"],
    "Engineering": ["Civil Engineer", "Software Developer", "Mechanical", "Electrical"],
}
FAQ = {
    "What is NCEA?": "NCEA is New Zealand’s main school qualification.",
    "What is a rank score?": "It's a number based on your Level 3 results for uni entry.",
}

# ---------------- utils ----------------
def center_window(win: tk.Tk | tk.Toplevel):
    win.update_idletasks()
    w = win.winfo_reqwidth()
    h = win.winfo_reqheight()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max(0, (sw - w)//2)
    y = max(0, (sh - h)//2)
    win.geometry(f"{w}x{h}+{x}+{y}")

# ---------------- user store ----------------
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
def _hash_pw(pw: str, salt: str)->str: return hashlib.sha256((salt+pw).encode("utf-8")).hexdigest()

class UserStore:
    """
    {
      "users": {
        "<username>": {
          "salt": "...",
          "pw": "...sha256...",
          "state": {"dark": false, "chat_history": "", "grades": []}
        }
      }
    }
    """
    def __init__(self, path=USERS_FILE):
        self.path = path
        self.data = {"users": {}}
        self._load_or_init()

    def _load_or_init(self):
        if os.path.exists(self.path):
            try:
                with open(self.path,"r",encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                try: os.replace(self.path, self.path+".corrupt.bak")
                except: pass
                self.data = {"users": {}}
        if "users" not in self.data: self.data["users"]={}
        if "demo" not in self.data["users"]:
            self.create_user("demo","student123")
        self._save()

    def _save(self):
        with open(self.path,"w",encoding="utf-8") as f: json.dump(self.data,f,indent=2)

    def create_user(self, username:str, password:str):
        if not USERNAME_RE.match(username):
            raise ValueError("Username must be 3–32 chars (letters/digits/_).")
        if username in self.data["users"]:
            raise ValueError("Username already exists.")
        if len(password)<8:
            raise ValueError("Password must be at least 8 characters.")
        salt = secrets.token_hex(16)
        self.data["users"][username] = {"salt":salt, "pw":_hash_pw(password,salt),
                                        "state":{"dark":False,"chat_history":"","grades":[]}}
        self._save()

    def verify(self, username:str, password:str)->bool:
        u = self.data["users"].get(username)
        if not u: return False
        return _hash_pw(password,u["salt"])==u["pw"]

    def change_password(self, username:str, old_pw:str, new_pw:str):
        if not self.verify(username, old_pw): raise ValueError("Current password incorrect.")
        if len(new_pw)<8: raise ValueError("New password must be at least 8 characters.")
        salt = secrets.token_hex(16)
        self.data["users"][username]["salt"]=salt
        self.data["users"][username]["pw"]=_hash_pw(new_pw,salt)
        self._save()

    def get_state(self, username:str)->dict:
        u = self.data["users"].get(username)
        if not u: raise ValueError("User does not exist.")
        st = u.get("state") or {}
        st.setdefault("dark", False); st.setdefault("chat_history",""); st.setdefault("grades",[])
        return st

    def save_state(self, username:str, state:dict):
        if username not in self.data["users"]: raise ValueError("User does not exist.")
        self.data["users"][username]["state"] = {
            "dark": bool(state.get("dark", False)),
            "chat_history": state.get("chat_history","") or "",
            "grades": state.get("grades",[]) or []
        }
        self._save()

# ---------------- tiny bot ----------------
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

# ---------------- Login root app ----------------
class LoginApp(tk.Tk):
    def __init__(self, store:UserStore):
        super().__init__()
        self.store = store
        self.result_username = None
        self.title("Sign in • Gradus")
        self.resizable(False, False)

        nb = ttk.Notebook(self)
        f_login = ttk.Frame(nb, padding=12)
        f_reg   = ttk.Frame(nb, padding=12)
        nb.add(f_login, text="Login")
        nb.add(f_reg,   text="Register")
        nb.pack(fill="both", expand=True)

        # login tab
        self.u_login=tk.StringVar(); self.p_login=tk.StringVar()
        ttk.Label(f_login, text="Username").grid(row=0,column=0,sticky="e",padx=6,pady=6)
        ttk.Entry(f_login, textvariable=self.u_login, width=28).grid(row=0,column=1,sticky="w")
        ttk.Label(f_login, text="Password").grid(row=1,column=0,sticky="e",padx=6,pady=6)
        e_pw=ttk.Entry(f_login, textvariable=self.p_login, show="•", width=28); e_pw.grid(row=1,column=1,sticky="w")
        row=ttk.Frame(f_login); row.grid(row=2, column=1, sticky="e", pady=(6,0))
        ttk.Button(row, text="Login", style="Accent.TButton", command=self._do_login).pack(side="left", padx=(0,6))
        ttk.Button(row, text="Exit",  command=self._exit).pack(side="left")
        e_pw.bind("<Return>", lambda e: self._do_login())

        # register tab
        self.u_reg=tk.StringVar(); self.p_reg=tk.StringVar(); self.p_reg2=tk.StringVar()
        ttk.Label(f_reg, text="Username").grid(row=0,column=0,sticky="e",padx=6,pady=6)
        ttk.Entry(f_reg, textvariable=self.u_reg, width=28).grid(row=0,column=1,sticky="w")
        ttk.Label(f_reg, text="Password").grid(row=1,column=0,sticky="e",padx=6,pady=6)
        ttk.Entry(f_reg, textvariable=self.p_reg, show="•", width=28).grid(row=1,column=1,sticky="w")
        ttk.Label(f_reg, text="Confirm").grid(row=2,column=0,sticky="e",padx=6,pady=6)
        ttk.Entry(f_reg, textvariable=self.p_reg2, show="•", width=28).grid(row=2,column=1,sticky="w")
        ttk.Label(f_reg, text="Username: 3–32 letters/digits/_  •  Password: ≥ 8 chars", foreground="#6b7280")\
            .grid(row=3,column=1,sticky="w")
        ttk.Button(f_reg, text="Create account", style="Accent.TButton", command=self._do_register)\
            .grid(row=4,column=1,sticky="e",pady=6)

        # theme (basic; main theme lives in MainApp)
        s=ttk.Style(self)
        try: s.theme_use("clam")
        except: pass

        center_window(self)

    def _do_login(self):
        u,p = self.u_login.get().strip(), self.p_login.get()
        if not u or not p: messagebox.showwarning("Login","Enter both username and password."); return
        if not self.store.verify(u,p): messagebox.showerror("Login failed","Invalid username or password."); return
        self.result_username = u
        self.destroy()  #  destroys the login root; we'll start MainApp afterwards

    def _do_register(self):# register a new user
        u,p1,p2 = self.u_reg.get().strip(), self.p_reg.get(), self.p_reg2.get()
        if not USERNAME_RE.match(u):
            messagebox.showwarning("Register","Username must be 3–32 chars (letters/digits/_)."); return
        if len(p1)<8: messagebox.showwarning("Register","Password must be at least 8 characters."); return
        if p1!=p2: messagebox.showwarning("Register","Passwords do not match."); return
        try:
            self.store.create_user(u,p1)
        except ValueError as e:
            messagebox.showerror("Register", str(e)); return
        messagebox.showinfo("Register","Account created. Please login on the Login tab.")

    def _exit(self):
        self.result_username = None
        self.destroy()

# ---------------- Main root app ----------------
class MainApp(tk.Tk):
    def __init__(self, username:str, store:UserStore):
        super().__init__()
        self.title("Gradus"); self.geometry("980x660"); self.minsize(880,580)
        self.username = username
        self.store = store

        st = store.get_state(username)
        self.dark = bool(st.get("dark", False))
        self.chat_history = st.get("chat_history","")
        self.grades = st.get("grades",[])

        self._build_style()

        # Layout
        root = ttk.Frame(self); root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1); root.rowconfigure(1, weight=1)

        # Sidebar
        side = ttk.Frame(root, padding=10); side.grid(row=0,column=0,rowspan=2,sticky="ns")
        ttk.Label(side, text="Gradus", font=("Segoe UI",16,"bold")).pack(anchor="w", pady=(4,2))
        ttk.Label(side, text="NZ study • career helper", style="Sub.TLabel").pack(anchor="w", pady=(0,8))
        for name,cmd in [("🏠  Home",self.to_home),("📏  Check",self.to_check),("🧭  Careers",self.to_career),
                         ("❄️  FROST",self.to_frost),("📄  Grades",self.to_grades),("👤  Profile",self.to_profile)]:
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

        self.host = ttk.Frame(root, padding=10, style="Card.TFrame"); self.host.grid(row=1,column=1,sticky="nsew")
        self.status = tk.StringVar(value="Ready. Ctrl+S save chat • Ctrl+L clear chat • Ctrl+E export CSV • Ctrl+Q quit")
        ttk.Label(root, textvariable=self.status, anchor="w", padding=(10,4)).grid(row=2,column=0,columnspan=2,sticky="ew")

        # shortcuts
        self.bind_all("<Control-s>", lambda e: self._delegate("save_chat"))
        self.bind_all("<Control-l>", lambda e: self._delegate("clear_chat"))
        self.bind_all("<Control-e>", lambda e: self._delegate("export_csv"))
        self.bind_all("<Control-q>", lambda e: self.on_quit())

        # pages
        self.pages = {cls.__name__: cls(self.host, self) for cls in (Home, Check, Careers, FROST, Grades, Profile)}
        for w in self.pages.values(): w.grid(row=0,column=0,sticky="nsew")

        center_window(self)
        self.to_home()
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
            # Softer dark palette
            self.bg     = "#0f1420"  # deep blue-gray
            self.card   = "#161c2c"  # slightly lighter
            self.sub    = "#9aa5b1"  # muted secondary
            self.accent = "#7a88ff"  # soft indigo
            self.accent2= "#6f7bf5"
            fg          = "#e6edf3"  # soft white
        else:
            self.bg     = "#f7f7fb"  # very light gray
            self.card   = "#ffffff"  # white
            self.sub    = "#555555"  #  muted dark
            self.accent = "#4f46e5"  # vibrant indigo
            self.accent2= "#4338ca"  # darker indigo
            fg          = "#111827"   # very dark gray
        self.configure(bg=self.bg); self.option_add("*Foreground", fg); self.option_add("*Background", self.bg)

    def toggle_theme(self):
        self.dark = not self.dark
        self._build_style()
        self.set_status("Theme: Dark" if self.dark else "Theme: Light")
        self._save_state()

    # persistence
    def _save_state(self):
        try:
            self.store.save_state(self.username, {
                "dark": self.dark,
                "chat_history": self.chat_history,
                "grades": self.grades
            })
        except Exception as e:
            self.set_status(f"Save failed: {e}")

    # nav / status
    def _show(self, k): self.pages[k].tkraise()
    def to_home(self): self._show("Home")
    def to_check(self): self._show("Check")
    def to_career(self): self._show("Careers")
    def to_frost(self): self._show("FROST")
    def to_grades(self): self._show("Grades")
    def to_profile(self): self._show("Profile")
    def set_status(self, msg): self.status.set(msg)

    # shortcuts
    def _delegate(self, action):
        cur = self.pages.get("FROST")
        if action=="save_chat" and cur and cur.winfo_ismapped(): cur.save_chat(); return "break"
        if action=="clear_chat" and cur and cur.winfo_ismapped(): cur.clear(); return "break"
        grd = self.pages.get("Grades")
        if action=="export_csv" and grd and grd.winfo_ismapped(): grd.export_csv(); return "break"

    # logout / quit
    def logout(self):
        # Destroy current main root and re-run the whole two-stage flow
        self.on_quit()
        # Relaunch login -> main
        run_app(self.store)

    def on_quit(self):
        self._save_state()
        self.destroy()

# ---------------- pages ----------------
class Home(ttk.Frame):
    def __init__(self, parent, app:MainApp):
        super().__init__(parent, padding=16)
        ttk.Label(self,text="Gradus",style="Header.TLabel").pack(anchor="w",pady=(0,6))
        ttk.Label(self,text="• Welcome to Gradus\n• Use the sidebar to open modules\n• Status bar shows tips & saves",
                  style="Sub.TLabel", justify="left").pack(anchor="w")
        ttk.Separator(self).pack(fill="x", pady=10)
        ttk.Label(self,text="[Two-stage start • main opens after login only]",style="Sub.TLabel").pack(anchor="w")

class Check(ttk.Frame):#    simple uni entry check
    def __init__(self, parent, app:MainApp):
        super().__init__(parent, padding=16); self.app=app
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
            messagebox.showinfo("Result", f"✔ Enough for {c} (need {need}).") if s>=need \
                else messagebox.showwarning("Result", f"✘ Need {need-s} more for {c}.")
        except ValueError:
            messagebox.showerror("Error","Enter a whole number.")

class Careers(ttk.Frame):#  career suggestions for interest areas
    def __init__(self, parent, app:MainApp):
        super().__init__(parent, padding=16)
        ttk.Label(self,text="Career Ideas",style="Header.TLabel").pack(anchor="w")
        row=ttk.Frame(self); row.pack(anchor="w", pady=8)
        self.var=tk.StringVar(value=list(CAREERS.keys())[0])
        ttk.Label(row,text="Interest").pack(side="left",padx=(0,6))
        ttk.Combobox(row,textvariable=self.var,values=list(CAREERS.keys()),state="readonly",width=20).pack(side="left")
        ttk.Button(row,text="Suggest",style="Accent.TButton",command=self.suggest).pack(side="left",padx=8)
        self.out=tk.Text(self,height=10,wrap="word",borderwidth=0)
        self.out.pack(fill="both",expand=True); self.out.configure(state="disabled")
    def suggest(self):# suggest careers for selected interest
        f=self.var.get()
        self.out.configure(state="normal"); self.out.delete("1.0","end")
        self.out.insert("end","• "+ "\n• ".join(CAREERS[f])); self.out.configure(state="disabled")

class FROST(ttk.Frame):# simple chatbot interface
    def __init__(self, parent, app:MainApp):
        super().__init__(parent, padding=12); self.app=app; self.bot=ChatBot()
        ttk.Label(self,text="FROST Chat",style="Header.TLabel").grid(row=0,column=0,sticky="w")
        ttk.Label(self,text="Ask NCEA • rank score • careers. Enter=send; Shift+Enter=new line.",style="Sub.TLabel")\
            .grid(row=1,column=0,sticky="w",pady=(0,6))
        chips=ttk.Frame(self); chips.grid(row=2,column=0,sticky="w",pady=(0,4))
        for t in ["What is NCEA?","I like Science","My score is 300 for Engineering"]:
            ttk.Button(chips,text=t,command=lambda s=t:self._quick(s)).pack(side="left",padx=4)
        self.chat=scrolledtext.ScrolledText(self,wrap="word",height=16,state="disabled",borderwidth=0)
        self.chat.grid(row=3,column=0,sticky="nsew"); self.rowconfigure(3,weight=1)
        self.chat.tag_config("user",foreground="#1f2937"); self.chat.tag_config("bot",foreground="#0b5394"); self.chat.tag_config("sys",foreground="#6b7280")
        row=ttk.Frame(self); row.grid(row=4,column=0,sticky="ew",pady=(6,0)); row.columnconfigure(0,weight=1)
        self.entry=tk.Text(row,height=3,wrap="word"); self.entry.grid(row=0,column=0,sticky="ew")
        btns=ttk.Frame(row); btns.grid(row=0,column=1,sticky="e",padx=(6,0))
        ttk.Button(btns,text="Send ▶",style="Accent.TButton",command=self.send).pack(side="left")
        ttk.Button(btns,text="Clear",command=self.clear).pack(side="left",padx=6)
        ttk.Button(btns,text="Copy",command=self.copy_chat).pack(side="left",padx=6)
        self.entry.bind("<Return>", self._on_enter); self.entry.bind("<Shift-Return>", lambda e: None)
        self.entry.bind("<Control-s>", self.save_chat); self.entry.bind("<Control-l>", lambda e: (self.clear(), "break"))
        self._append("sys","Hi, I’m FROST. /help for help.")
    def _append(self, role, msg):# append a message to chat area and history
        self.chat.configure(state="normal")
        ts=datetime.datetime.now().strftime("%H:%M")
        lab={"user":"You","bot":"FROST","sys":"System"}[role]
        line=f"[{ts}] {lab}: {msg}\n"
        self.chat.insert("end", line, role); self.chat.configure(state="disabled"); self.chat.see("end")
        self.app.chat_history += line; self.app._save_state()
    def _get(self): return self.entry.get("1.0","end").strip()# get input box text
    def _clr_input(self): self.entry.delete("1.0","end")# clear input box
    def _quick(self, text): self._append("user", text); self._append("bot", self.bot.reply(text))# quick button
    def _on_enter(self, e):
        if e.state & 0x0001: return
        self.send(); return "break"
    def send(self, event=None):# send user input to bot
        t=self._get()
        if not t: return
        if t.lower()=="/clear": self.clear(); return
        if t.lower()=="/save": self.save_chat(); return
        self._append("user", t); self._append("bot", self.bot.reply(t))
        self._clr_input(); self.app.set_status("Sent. Ctrl+S save, Ctrl+L clear.")
    def clear(self):# clear chat history
        if not messagebox.askyesno("Confirm","Clear the chat?"): return
        self.chat.configure(state="normal"); self.chat.delete("1.0","end"); self.chat.configure(state="disabled")
        self._clr_input(); self._append("sys","Chat cleared."); self.app.set_status("Chat cleared.")
        self.app.chat_history = ""; self.app._save_state()
    def copy_chat(self):# copy chat to clipboard
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

class Grades(ttk.Frame):# NCEA grades manager
    def __init__(self, parent, app:MainApp):
        super().__init__(parent, padding=12); self.app=app
        ttk.Label(self,text="Grades (NCEA)",style="Header.TLabel").grid(row=0,column=0,sticky="w")
        top=ttk.Frame(self); top.grid(row=1,column=0,sticky="ew",pady=(2,6)); top.columnconfigure(1,weight=1)
        ttk.Label(top,text="Search").grid(row=0,column=0,sticky="e",padx=4)
        self.q = ttk.Entry(top,width=30); self.q.grid(row=0,column=1,sticky="ew")
        ttk.Button(top,text="Apply",command=self.apply_filter).grid(row=0,column=2,padx=4)
        ttk.Button(top,text="Reset",command=self.reset_filter).grid(row=0,column=3)
        form=ttk.Frame(self); form.grid(row=2,column=0,sticky="w",pady=6)
        ttk.Label(form,text="Title").grid(row=0,column=0,sticky="e"); self.e_title=ttk.Entry(form,width=24); self.e_title.grid(row=0,column=1,padx=6)
        ttk.Label(form,text="Level").grid(row=0,column=2,sticky="e"); self.var_lvl=tk.IntVar(value=3); ttk.Spinbox(form,from_=1,to=3,textvariable=self.var_lvl,width=5).grid(row=0,column=3,padx=6)
        ttk.Label(form,text="Credits").grid(row=0,column=4,sticky="e"); self.e_cred=ttk.Entry(form,width=6); self.e_cred.grid(row=0,column=5,padx=6)
        ttk.Label(form,text="Grade").grid(row=0,column=6,sticky="e"); self.var_g=tk.StringVar(value="A")
        ttk.Combobox(form,textvariable=self.var_g,values=["A","M","E","N"],state="readonly",width=5).grid(row=0,column=7,padx=6)
        ttk.Button(form,text="Add",style="Accent.TButton",command=self.add).grid(row=0,column=8,padx=(8,0))
        self.tree=ttk.Treeview(self,columns=("Title","Level","Credits","Grade"),show="headings",height=11)
        for col,w in [("Title",380),("Level",60),("Credits",80),("Grade",80)]:
            self.tree.heading(col,text=col); self.tree.column(col,width=w,anchor="center")
        self.tree.grid(row=3,column=0,sticky="nsew",pady=6); self.rowconfigure(3,weight=1)
        self.lbl_tot=ttk.Label(self,text="Totals: L1 0 | L2 0 | L3 0 | All 0"); self.lbl_tot.grid(row=4,column=0,sticky="w")
        btns=ttk.Frame(self); btns.grid(row=5,column=0,sticky="w",pady=6)
        ttk.Button(btns,text="Import CSV",command=self.import_csv).pack(side="left")
        ttk.Button(btns,text="Export CSV",command=self.export_csv).pack(side="left",padx=6)
        ttk.Button(btns,text="Remove selected",command=self.remove_sel).pack(side="left",padx=6)
        self.refresh()
    def refresh(self, rows=None):# refresh table contents
        for iid in self.tree.get_children(): self.tree.delete(iid)
        data = rows if rows is not None else self.app.grades
        for g in data:
            self.tree.insert("", "end", values=(g["title"], g["level"], g["credits"], g["grade"]))
        self._update_totals()
    def apply_filter(self):#    filter by title substring
        q = self.q.get().strip().lower()
        if not q: self.refresh(); return
        rows=[g for g in self.app.grades if q in g["title"].lower()]
        self.refresh(rows)
    def reset_filter(self): self.q.delete(0,"end"); self.refresh()
    def add(self):# add a new grade
        title=self.e_title.get().strip()
        if not title: messagebox.showwarning("Missing","Enter title."); return
        try:
            credits=int(self.e_cred.get()); level=int(self.var_lvl.get()); grade=self.var_g.get().upper()
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
        keep=[]; ids=set(sel)
        for iid in self.tree.get_children():
            if iid in ids: continue
            t,l,c,g = self.tree.item(iid,"values")
            keep.append({"title":t,"level":int(l),"credits":int(c),"grade":g})
        self.app.grades=keep; self.refresh(); self.app._save_state()
    def _update_totals(self):# compute and show totals
        lv={1:0,2:0,3:0}; total=0
        for iid in self.tree.get_children():
            _, l, c, _ = self.tree.item(iid,"values")
            l=int(l); c=int(c); lv[l]+=c; total+=c
        self.lbl_tot.config(text=f"Totals: L1 {lv[1]} | L2 {lv[2]} | L3 {lv[3]} | All {total}")
    def export_csv(self):# export to a CSV file (Title, Level, Credits, Grade)
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")], initialfile="grades.csv")
        if not path: return
        try:
            with open(path,"w",newline="",encoding="utf-8") as f:
                w=csv.writer(f); w.writerow(["Title","Level","Credits","Grade"])
                for g in self.app.grades: w.writerow([g["title"],g["level"],g["credits"],g["grade"]])
            self.app.set_status(f"Exported CSV → {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
    def import_csv(self):# import from a CSV file (Title, Level, Credits, Grade)
        path = filedialog.askopenfilename(filetypes=[("CSV","*.csv")])
        if not path: return
        try:
            with open(path,"r",encoding="utf-8") as f:
                r=csv.DictReader(f)
                loaded=[]
                for row in r:
                    title=row.get("Title","").strip()
                    level=int(row.get("Level","0")); credits=int(row.get("Credits","0"))
                    grade=row.get("Grade","A").strip().upper()
                    if title and level in (1,2,3) and 1<=credits<=24 and grade in ("A","M","E","N"):
                        loaded.append({"title":title,"level":level,"credits":credits,"grade":grade})
            self.app.grades.extend(loaded); self.refresh(); self.app._save_state()
            self.app.set_status(f"Imported {len(loaded)} rows.")
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

class Profile(ttk.Frame):# user settings
    def __init__(self, parent, app:MainApp):
        super().__init__(parent, padding=16); self.app=app
        ttk.Label(self,text="Profile",style="Header.TLabel").grid(row=0,column=0,columnspan=2,sticky="w")
        ttk.Label(self,text="Theme").grid(row=1,column=0,sticky="e",padx=6,pady=6)
        self.theme=tk.StringVar(value="dark" if app.dark else "light")
        row=ttk.Frame(self); row.grid(row=1,column=1,sticky="w")
        ttk.Radiobutton(row,text="Light",value="light",variable=self.theme).pack(side="left")
        ttk.Radiobutton(row,text="Dark", value="dark", variable=self.theme).pack(side="left", padx=8)
        ttk.Button(self,text="Apply",style="Accent.TButton",command=self.apply).grid(row=2,column=1,sticky="w",pady=6)
        ttk.Separator(self).grid(row=3,column=0,columnspan=2,sticky="ew",pady=10)
        # change password
        ttk.Label(self,text="Change password",style="Sub.TLabel").grid(row=4,column=0,sticky="w",pady=(0,6))
        ttk.Label(self,text="Current").grid(row=5,column=0,sticky="e",padx=6,pady=3)
        ttk.Label(self,text="New").grid(row=6,column=0,sticky="e",padx=6,pady=3)
        ttk.Label(self,text="Confirm").grid(row=7,column=0,sticky="e",padx=6,pady=3)
        self.cur_pw=tk.StringVar(); self.new_pw=tk.StringVar(); self.new_pw2=tk.StringVar()
        ttk.Entry(self,textvariable=self.cur_pw, show="•", width=24).grid(row=5,column=1,sticky="w")
        ttk.Entry(self,textvariable=self.new_pw, show="•", width=24).grid(row=6,column=1,sticky="w")
        ttk.Entry(self,textvariable=self.new_pw2, show="•", width=24).grid(row=7,column=1,sticky="w")
        ttk.Button(self,text="Update password",command=self.change_pw).grid(row=8,column=1,sticky="w",pady=6)
        ttk.Separator(self).grid(row=9,column=0,columnspan=2,sticky="ew",pady=10)
        ttk.Button(self,text="Export my data",command=self.export_all).grid(row=10,column=1,sticky="w")

    def apply(self):# apply theme
        want_dark = (self.theme.get()=="dark")
        if want_dark != self.app.dark:
            self.app.toggle_theme()
        else:
            self.app._save_state()
        self.app.set_status("Profile applied.")

    def change_pw(self):# change password
        cur, n1, n2 = self.cur_pw.get(), self.new_pw.get(), self.new_pw2.get()
        if n1 != n2:
            messagebox.showwarning("Change password","New passwords do not match."); return
        try:
            self.app.store.change_password(self.app.username, cur, n1)
            self.cur_pw.set(""); self.new_pw.set(""); self.new_pw2.set("")
            messagebox.showinfo("Change password","Password updated.")
        except ValueError as e:
            messagebox.showerror("Change password", str(e))

    def export_all(self):# export chat + grades to a folder
        folder = filedialog.askdirectory()
        if not folder: return
        try:
            chat_path=os.path.join(folder,"frost_chat.txt")
            with open(chat_path,"w",encoding="utf-8") as f: f.write(self.app.chat_history)
            grades_path=os.path.join(folder,"grades.csv")
            with open(grades_path,"w",newline="",encoding="utf-8") as f:
                w=csv.writer(f); w.writerow(["Title","Level","Credits","Grade"])
                for g in self.app.grades: w.writerow([g["title"],g["level"],g["credits"],g["grade"]])
            self.app.set_status(f"Exported chat & grades → {os.path.basename(folder)}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

# ---------------- orchestration ----------------
def run_app(store:UserStore):
    # 1) login root
    login = LoginApp(store)
    center_window(login)
    login.mainloop()
    if not login.result_username:
        sys.exit(0)
    # 2) main root
    app = MainApp(login.result_username, store)
    app.mainloop()
# ---------------- Run ----------------
if __name__=="__main__":
    store = UserStore()
    run_app(store)
