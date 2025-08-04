import tkinter as tk
from tkinter import ttk, messagebox

COURSES = {
    "Science": 280,
    "Commerce": 210,
    "Engineering": 260
}
CAREERS = {
    "Science": ["Biologist", "Lab Technician"],
    "Commerce": ["Accountant", "Economist"],
    "Engineering": ["Civil Engineer", "Software Developer"]
}
FAQ = {
    "What is NCEA?": "NCEA is New Zealand’s main school qualification.",
    "What is a rank score?": "It's a number based on your Level 3 results for uni entry."
}
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gradus Simple")
        self.geometry("400x400")
        btns = tk.Frame(self)
        btns.pack()
        tk.Button(btns, text="Home", command=self.show_home).pack(side="left", padx=5)
        tk.Button(btns, text="Check", command=self.show_check).pack(side="left", padx=5)
        tk.Button(btns, text="Careers", command=self.show_career).pack(side="left", padx=5)
        tk.Button(btns, text="FROST", command=self.show_frost).pack(side="left", padx=5)
        self.frames = {}
        for F in (Home, Check, Careers, FROST):
            page = F(self)
            self.frames[F.__name__] = page
            page.pack(fill="both", expand=True)
        self.show_home()
    def show_home(self):
        self._raise("Home")
    def show_check(self):
        self._raise("Check")
    def show_career(self):
        self._raise("Careers")
    def show_frost(self):
        self._raise("FROST")

    def _raise(self, name):
        for f in self.frames.values():
            f.pack_forget()
        self.frames[name].pack(fill="both", expand=True)
class Home(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Welcome to Gradus!", font=("Arial", 18)).pack(pady=30)
        tk.Label(self, text="Your career helper!").pack()
class Check(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Enter your rank score:").pack(pady=10)
        self.entry = tk.Entry(self)
        self.entry.pack()
        self.var = tk.StringVar()
        ttk.Combobox(self, textvariable=self.var, values=list(COURSES.keys()), state="readonly").pack(pady=5)
        self.var.set(list(COURSES.keys())[0])
        tk.Button(self, text="Check", command=self.check).pack(pady=10)
    def check(self):
        try:
            score = int(self.entry.get())
            course = self.var.get()
            if score >= COURSES[course]:
                messagebox.showinfo("Result", "✔ Entry met!")
            else:
                messagebox.showwarning("Result", "✘ Not enough score.")
        except:
            messagebox.showerror("Error", "Please enter a valid number.")
class Careers(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Choose your interest:").pack(pady=10)
        self.var = tk.StringVar()
        ttk.Combobox(self, textvariable=self.var, values=list(CAREERS.keys()), state="readonly").pack(pady=5)
        self.var.set(list(CAREERS.keys())[0])
        tk.Button(self, text="Suggest", command=self.suggest).pack(pady=10)
    def suggest(self):
        field = self.var.get()
        result = "\n".join(CAREERS[field])
        messagebox.showinfo("Careers", result)
class FROST(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="FROST Q&A", font=("Arial", 14)).pack(pady=10)
        for q, a in FAQ.items():
            tk.Label(self, text=f"Q: {q}", font=("Arial", 10, "bold")).pack(anchor="w", padx=10)
            tk.Label(self, text=f"A: {a}", wraplength=380, justify="left").pack(anchor="w", padx=20, pady=3)
if __name__ == "__main__":
    App().mainloop()
