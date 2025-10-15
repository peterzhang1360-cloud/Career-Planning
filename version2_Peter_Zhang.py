# version 2: improved UI, added features, better code structure
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import re, datetime, json
# -------------- Data ----------------
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
# ---------------- ChatBot Logic ----------------
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

# ---------------- UI Shell ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gradus"); self.geometry("860x540"); self.minsize(760,480)
        self.dark=False; self._build_style()
        # Layout: sidebar | main
        root = ttk.Frame(self); root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1); root.rowconfigure(1, weight=1)
        # Sidebar
        side = ttk.Frame(root, padding=10); side.grid(row=0,column=0,rowspan=2,sticky="ns")
        ttk.Label(side, text="Gradus", font=("Segoe UI",16,"bold")).pack(anchor="w", pady=(4,2))
        ttk.Label(side, text="NZ study & career helper", style="Sub.TLabel").pack(anchor="w", pady=(0,8))
        for name,cmd in [("🏠  Home",self.to_home),("📏  Check",self.to_check),("🧭  Careers",self.to_career),("❄️  FROST",self.to_frost)]:
            ttk.Button(side, text=name, command=cmd).pack(fill="x", pady=4)
        # Header
        header = ttk.Frame(root, padding=(10,10,10,6)); header.grid(row=0,column=1,sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header,text="Gradus",style="Header.TLabel").grid(row=0,column=0,sticky="w")
        ttk.Label(header,text="Fast checks • Career ideas • FROST chat",style="Sub.TLabel").grid(row=1,column=0,sticky="w")
        ttk.Button(header,text="🌙",width=3,command=self.toggle_theme).grid(row=0,column=1,rowspan=2,sticky="e")
        # Main host + status
        self.host = ttk.Frame(root, padding=10, style="Card.TFrame"); self.host.grid(row=1,column=1,sticky="nsew")
        self.status = tk.StringVar(value="Ready. Ctrl+S save chat, Ctrl+L clear.")
        ttk.Label(root, textvariable=self.status, anchor="w", padding=(10,4)).grid(row=2,column=0,columnspan=2,sticky="ew")
        # Pages
        self.pages = {cls.__name__: cls(self.host, self) for cls in (Home, Check, Careers, FROST)}
        for w in self.pages.values(): w.grid(row=0,column=0,sticky="nsew")
        self.to_home()
    # style / theme
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
    def _apply_colors(self):# apply colors to root and widgets
        if self.dark:
            self.bg="#0f172a"; self.card="#111827"; self.sub="#9ca3af"; self.accent="#6366f1"; self.accent2="#4f46e5"; fg="#e5e7eb"
        else:
            self.bg="#f7f7fb"; self.card="#ffffff"; self.sub="#555"; self.accent="#4f46e5"; self.accent2="#4338ca"; fg="#111827"
        self.configure(bg=self.bg)
        self.option_add("*Foreground", fg); self.option_add("*Background", self.bg)# default for widgets
    def toggle_theme(self):# switch light/dark
        self.dark=not self.dark; self._build_style()# reapply
        for w in self.winfo_children(): w.update()# force redraw
    # nav
    def _show(self, name):
        self.pages[name].tkraise()
    def to_home(self):   self._show("Home")
    def to_check(self):  self._show("Check")
    def to_career(self): self._show("Careers")
    def to_frost(self):  self._show("FROST")
    def set_status(self, msg): self.status.set(msg)

# ---------------- Pages ----------------
class Home(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        ttk.Label(self,text="Welcome to Gradus 👋",style="Header.TLabel").pack(anchor="w",pady=(0,6))
        ttk.Label(self,text="Pick a module on the left.",style="Sub.TLabel").pack(anchor="w")
class Check(ttk.Frame):#Check if rank score meets course requirements
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        ttk.Label(self,text="University Entry Check",style="Header.TLabel").grid(row=0,column=0,columnspan=4,sticky="w")
        ttk.Label(self,text="Rank score").grid(row=1,column=0,sticky="e",padx=6,pady=8)
        self.e = ttk.Entry(self,width=10); self.e.grid(row=1,column=1,sticky="w")
        ttk.Label(self,text="Target course").grid(row=1,column=2,sticky="e",padx=6)
        self.var=tk.StringVar(value=list(COURSES.keys())[0])
        ttk.Combobox(self,textvariable=self.var,values=list(COURSES.keys()),state="readonly",width=18).grid(row=1,column=3,sticky="w")
        ttk.Button(self,text="Check",style="Accent.TButton",command=self.run).grid(row=2,column=0,pady=6,sticky="w")
    def run(self):# Validate input and show result via messagebox.
        try:
            s=int(self.e.get()); c=self.var.get(); need=COURSES[c]
            messagebox.showinfo("Result", f"✔ Enough for {c} (need {need}).") if s>=need \
                else messagebox.showwarning("Result", f"✘ Need {need-s} more for {c}.")
        except: messagebox.showerror("Error","Enter a whole number.")
class Careers(ttk.Frame):#Suggest careers based on interest
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
    def suggest(self):# Show careers in text box
        f=self.var.get()
        self.out.configure(state="normal"); self.out.delete("1.0","end")
        self.out.insert("end","• "+ "\n• ".join(CAREERS[f])); self.out.configure(state="disabled")
class FROST(ttk.Frame):#    Chat with FROST bot
    def __init__(self, parent, app:App):
        super().__init__(parent, padding=12); self.app=app; self.bot=ChatBot()
        ttk.Label(self,text="FROST Chat",style="Header.TLabel").grid(row=0,column=0,sticky="w")
        ttk.Label(self,text="Ask NCEA, rank scores, careers. Enter=send; Shift+Enter=new line.",
                  style="Sub.TLabel").grid(row=1,column=0,sticky="w",pady=(0,6))
        # Quick chips
        chips=ttk.Frame(self); chips.grid(row=2,column=0,sticky="w",pady=(0,4))
        for t in ["What is NCEA?","I like Science","My score is 300 for Engineering"]:
            ttk.Button(chips,text=t,command=lambda s=t:self._quick(s)).pack(side="left",padx=4)
        # Chat
        self.chat=scrolledtext.ScrolledText(self,wrap="word",height=16,state="disabled",borderwidth=0)
        self.chat.grid(row=3,column=0,sticky="nsew"); self.rowconfigure(3,weight=1)
        self.chat.tag_config("user",foreground="#1f2937"); self.chat.tag_config("bot",foreground="#0b5394"); self.chat.tag_config("sys",foreground="#6b7280")
        # Input row
        row=ttk.Frame(self); row.grid(row=4,column=0,sticky="ew",pady=(6,0)); row.columnconfigure(0,weight=1)
        self.entry=tk.Text(row,height=3,wrap="word"); self.entry.grid(row=0,column=0,sticky="ew")
        btns=ttk.Frame(row); btns.grid(row=0,column=1,sticky="e",padx=(6,0))
        ttk.Button(btns,text="Send ▶",style="Accent.TButton",command=self.send).pack(side="left")
        ttk.Button(btns,text="Clear",command=self.clear).pack(side="left",padx=6)
        self.entry.bind("<Return>", self._on_enter); self.entry.bind("<Shift-Return>", lambda e: None)
        self.entry.bind("<Control-s>", self.save_chat); self.entry.bind("<Control-l>", lambda e: (self.clear(), "break"))
        self._append("sys","Hi, I’m FROST. /help for help.")
    # helpers
    def _append(self, role, msg):
        self.chat.configure(state="normal")
        ts=datetime.datetime.now().strftime("%H:%M")
        lab={"user":"You","bot":"FROST","sys":"System"}[role]
        self.chat.insert("end", f"[{ts}] {lab}: ", role); self.chat.insert("end", msg+"\n")
        self.chat.configure(state="disabled"); self.chat.see("end")
    def _get(self): return self.entry.get("1.0","end").strip()
    def _clr_input(self): self.entry.delete("1.0","end")
    def _quick(self, text): self._append("user", text); self._append("bot", self.bot.reply(text))
    # actions
    def _on_enter(self, e):
        if e.state & 0x0001: return  # Shift
        self.send(); return "break"
    def send(self, event=None):
        t=self._get()
        if not t: return
        if t.lower()=="/clear": self.clear(); return
        if t.lower()=="/save": self.save_chat(); return
        self._append("user", t); self._append("bot", self.bot.reply(t))
        self._clr_input(); self.app.set_status("Sent. Ctrl+S save, Ctrl+L clear.")
    def clear(self):
        self.chat.configure(state="normal"); self.chat.delete("1.0","end"); self.chat.configure(state="disabled")
        self._clr_input(); self._append("sys","Chat cleared."); self.app.set_status("Chat cleared.")
    def save_chat(self, event=None):
        with open("frost_chat.txt","w",encoding="utf-8") as f:
            f.write(self.chat.get("1.0","end"))
        self.app.set_status("Saved to frost_chat.txt")

# ---------------- Run ----------------
if __name__=="__main__":
    App().mainloop()
