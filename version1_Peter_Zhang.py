# file: gradus_simple_version1.py
# A simple Tkinter app with navigation, rank checking, career suggestions, and FAQ.
"""
A minimal Tkinter app ("Gradus Simple") that:
- Navigates between pages (Home, Check, Careers, FROST).
- Checks a rank score against course thresholds.
- Suggests careers by field.
- Shows a small FAQ area.
Comments focus on the *why* behind key choices; logic unchanged.
"""
import tkinter as tk
from tkinter import ttk, messagebox
# Centralized data so UI logic stays simple and easy to change later.
COURSES = {
    "Science": 280,
    "Commerce": 210,
    "Engineering": 260,}
CAREERS = {
    "Science": ["Biologist", "Lab Technician"],
    "Commerce": ["Accountant", "Economist"],
    "Engineering": ["Civil Engineer", "Software Developer"],}
FAQ = {
    "What is NCEA?": "NCEA is New Zealand’s main school qualification.",
    "What is a rank score?": "It's a number based on your Level 3 results for uni entry.",}
class App(tk.Tk):#Root window managing navigation and page lifecycle
    def __init__(self):
        super().__init__()
        self.title("Gradus Simple")
        self.geometry("400x400") # Put navigation in its own frame to avoid layout jitter when pages switch.
        btns = tk.Frame(self)
        btns.pack() # Simple top-nav; commands just raise the corresponding page.
        tk.Button(btns, text="Home", command=self.show_home).pack(side="left", padx=5)
        tk.Button(btns, text="Check", command=self.show_check).pack(side="left", padx=5)
        tk.Button(btns, text="Careers", command=self.show_career).pack(side="left", padx=5)
        tk.Button(btns, text="FROST", command=self.show_frost).pack(side="left", padx=5)
        self.frames = {} # Keep instances to avoid recreating widgets (faster and preserves state).
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
    def _raise(self, name: str):
        #how one page at a time using pack/forget.Why: Simpler than grid_forget/destroy for small apps and preserves widget state.
        for f in self.frames.values():
            f.pack_forget()
        self.frames[name].pack(fill="both", expand=True)
class Home(tk.Frame):#Landing page for a friendly first impression
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Welcome to Gradus!", font=("Arial", 18)).pack(pady=30)
        tk.Label(self, text="Your career helper!").pack()
class Check(tk.Frame):#Check if rank score meets course requirements 
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Enter your rank score:").pack(pady=10)
        self.entry = tk.Entry(self)
        self.entry.pack()
        # StringVar + readonly Combobox to prevent arbitrary edits; ensures valid keys for COURSES.
        self.var = tk.StringVar()
        ttk.Combobox(
            self,
            textvariable=self.var,
            values=list(COURSES.keys()),
            state="readonly",
        ).pack(pady=5)
        self.var.set(list(COURSES.keys())[0])
        tk.Button(self, text="Check", command=self.check).pack(pady=10)
    def check(self): # Validate input and show result via messagebox.
        try:
            score = int(self.entry.get())
            course = self.var.get()
            if score >= COURSES[course]:
                messagebox.showinfo("Result", "✔ Entry met!")
            else:
                messagebox.showwarning("Result", "✘ Not enough score.")
        except Exception:
            # Keep broad except to match original behavior; avoids crashing on non-integers/empty input.
            messagebox.showerror("Error", "Please enter a valid number.")


class Careers(tk.Frame):#Suggest careers based on selected field
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Choose your interest:").pack(pady=10)
        # Readonly to keep selections within known keys (consistent with CAREERS mapping).
        self.var = tk.StringVar()
        ttk.Combobox(
            self,
            textvariable=self.var,
            values=list(CAREERS.keys()),
            state="readonly",
        ).pack(pady=5)
        self.var.set(list(CAREERS.keys())[0])
        tk.Button(self, text="Suggest", command=self.suggest).pack(pady=10)

    def suggest(self):# Show careers for selected field in a messagebox.
        field = self.var.get()
        result = "\n".join(CAREERS[field])
        messagebox.showinfo("Careers", result)


class FROST(tk.Frame):# Simple FAQ display for common questions
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="FROST Q&A", font=("Arial", 14)).pack(pady=10)
        # Wrap and left-align for better readability within a narrow window.
        for q, a in FAQ.items():
            tk.Label(self, text=f"Q: {q}", font=("Arial", 10, "bold")).pack(
                anchor="w", padx=10)
            tk.Label(self, text=f"A: {a}", wraplength=380, justify="left").pack(
                anchor="w", padx=20, pady=3 )

# Entry point to run the app
if __name__ == "__main__":
    App().mainloop()
