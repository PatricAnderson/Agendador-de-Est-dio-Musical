# PASSO 1: ANTES DE EXECUTAR, INSTALE A BIBLIOTECA NECESSÁRIA.
# Abra o terminal e digite:
# pip install tkcalendar

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime
from tkcalendar import DateEntry

class RehearsalSchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Agendador de Ensaios do Estúdio (v2.4 Modern)")
        self.root.geometry("1200x700")
        self.root.minsize(1050, 600)

        self.data_file = "agendamentos.json"
        self.all_rehearsals_cache = []
        self.selected_rehearsal_id = None # Rastreia o ÍNDICE do item selecionado no cache

        # --- Cores e Fontes ---
        BG_COLOR = "#282a36"
        FG_COLOR = "#f8f8f2"
        WIDGET_BG = "#3b3d51"
        SELECT_BG = "#44475a"
        ACCENT_COLOR = "#bd93f9"
        PAID_BG = "#3b5b43"
        PAID_FG = "#87d79d"
        PENDING_BG = "#6e5a1b"
        PENDING_FG = "#ffcb6b"
        font_main = ("Segoe UI", 10)
        font_bold = ("Segoe UI", 11, "bold")
        
        # --- Estilo ---
        style = ttk.Style(self.root)
        style.theme_use("clam")
        
        self.root.configure(bg=BG_COLOR)
        style.configure(".", background=BG_COLOR, foreground=FG_COLOR, borderwidth=0, font=font_main)
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=font_main)
        style.configure("TButton", background=WIDGET_BG, foreground=FG_COLOR, font=font_main, padding=8, borderwidth=0)
        style.map("TButton", background=[("active", ACCENT_COLOR)])
        style.configure("TEntry", fieldbackground=WIDGET_BG, foreground=FG_COLOR, insertcolor=FG_COLOR, borderwidth=1, bordercolor=SELECT_BG, font=font_main)
        style.configure("TCombobox", fieldbackground=WIDGET_BG, foreground=FG_COLOR, selectbackground=SELECT_BG, arrowcolor=FG_COLOR, borderwidth=0)
        
        style.configure("Treeview", background=WIDGET_BG, fieldbackground=WIDGET_BG, foreground=FG_COLOR, rowheight=28, font=font_main, borderwidth=0)
        style.map("Treeview", background=[("selected", ACCENT_COLOR)])
        style.configure("Treeview.Heading", background=SELECT_BG, foreground=FG_COLOR, font=font_bold, borderwidth=0)
        style.map("Treeview.Heading", background=[("active", BG_COLOR)])

        style.configure("TLabelframe", background=BG_COLOR, bordercolor=SELECT_BG)
        style.configure("TLabelframe.Label", background=BG_COLOR, foreground=FG_COLOR, font=font_bold)

        # --- Layout Principal ---
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(expand=True, fill="both")

        # --- Frame do Formulário (Esquerda) ---
        form_frame = ttk.LabelFrame(main_frame, text="Detalhes do Ensaio", padding="15")
        form_frame.pack(side="left", fill="y", padx=(0, 20))

        self.entries = {}
        self.fields = ["Nome da Banda", "Responsável", "Data", "Horário de Entrada", "Horário de Saída", "Valor Cobrado", "Status Pagamento"]
        
        for i, field in enumerate(self.fields):
            label = ttk.Label(form_frame, text=f"{field}:", font=font_main)
            label.grid(row=i, column=0, sticky="w", pady=6, padx=5)
            
            if field == "Data":
                entry = DateEntry(form_frame, width=30, date_pattern='dd/mm/yyyy', font=font_main,
                                  background=ACCENT_COLOR, foreground=FG_COLOR, borderwidth=2,
                                  headersbackground=BG_COLOR, headersforeground=FG_COLOR,
                                  selectbackground=ACCENT_COLOR, normalbackground=WIDGET_BG,
                                  weekendbackground=WIDGET_BG, othermonthbackground=WIDGET_BG,
                                  othermonthwebackground=WIDGET_BG)
            elif field == "Status Pagamento":
                entry = ttk.Combobox(form_frame, values=["Pendente", "Pago"], state="readonly", width=28, font=font_main)
                self.root.option_add('*TCombobox*Listbox.background', WIDGET_BG)
                self.root.option_add('*TCombobox*Listbox.foreground', FG_COLOR)
                self.root.option_add('*TCombobox*Listbox.selectBackground', ACCENT_COLOR)
            else:
                entry = ttk.Entry(form_frame, width=32, font=font_main)
            
            entry.grid(row=i, column=1, sticky="ew", pady=6, padx=5)
            self.entries[field] = entry
        
        button_form_frame = ttk.Frame(form_frame)
        button_form_frame.grid(row=len(self.fields), column=0, columnspan=2, pady=20)

        # Botões sem ícones
        ttk.Button(button_form_frame, text="Adicionar", command=self.add_rehearsal).pack(side="left", padx=5)
        ttk.Button(button_form_frame, text="Atualizar", command=self.update_rehearsal).pack(side="left", padx=5)
        ttk.Button(button_form_frame, text="Limpar", command=self.clear_form).pack(side="left", padx=5)

        # --- Frame da Tabela (Direita) ---
        table_container = ttk.Frame(main_frame)
        table_container.pack(side="right", expand=True, fill="both")
        
        search_frame = ttk.Frame(table_container)
        search_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(search_frame, text="Buscar:").pack(side="left", padx=(0, 10))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(expand=True, fill="x", side="left")
        self.search_entry.bind("<KeyRelease>", self.search_rehearsals)

        table_frame = ttk.LabelFrame(table_container, text="Ensaios Agendados", padding="15")
        table_frame.pack(expand=True, fill="both")

        self.columns_map = {
            "band_name": "Banda", "contact": "Responsável", "date": "Data",
            "start_time": "Entrada", "end_time": "Saída", "price": "Valor (R$)", "status": "Status"
        }
        self.tree = ttk.Treeview(table_frame, columns=list(self.columns_map.keys()), show="headings")

        for col_id, col_text in self.columns_map.items():
            self.tree.heading(col_id, text=col_text, command=lambda c=col_id: self.sort_column(c, False))

        self.tree.column("band_name", width=150)
        self.tree.column("contact", width=150)
        self.tree.column("date", width=100, anchor="center")
        self.tree.column("start_time", width=80, anchor="center")
        self.tree.column("end_time", width=80, anchor="center")
        self.tree.column("price", width=100, anchor="e")
        self.tree.column("status", width=100, anchor="center")
        
        self.tree.tag_configure("pago", background=PAID_BG, foreground=PAID_FG)
        self.tree.tag_configure("pendente", background=PENDING_BG, foreground=PENDING_FG)

        self.tree.pack(expand=True, fill="both", side="top")
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)

        ttk.Button(table_frame, text="Deletar Ensaio", command=self.delete_rehearsal).pack(pady=15, side="bottom")

        self.load_rehearsals()

    def get_data_as_dict(self):
        data = {}
        form_to_key = {
            "Nome da Banda": "band_name", "Responsável": "contact", "Data": "date",
            "Horário de Entrada": "start_time", "Horário de Saída": "end_time",
            "Valor Cobrado": "price", "Status Pagamento": "status"
        }
        for field_name, key_name in form_to_key.items():
            value = self.entries[field_name].get()
            if not value or value == "dd/mm/aaaa":
                messagebox.showwarning("Campo Vazio", f"O campo '{field_name}' não pode estar vazio.")
                return None
            data[key_name] = value
        
        try:
            datetime.strptime(data["start_time"], "%H:%M")
            datetime.strptime(data["end_time"], "%H:%M")
        except ValueError:
            messagebox.showwarning("Formato Inválido", "O formato do horário deve ser HH:MM (ex: 14:30).")
            return None
        
        try:
            float(data["price"].replace(",", "."))
        except ValueError:
            messagebox.showwarning("Formato Inválido", "O 'Valor Cobrado' deve ser um número.")
            return None

        return data

    def check_conflict(self, new_rehearsal, updating_id=None):
        try:
            new_start = datetime.strptime(f"{new_rehearsal['date']} {new_rehearsal['start_time']}", "%d/%m/%Y %H:%M")
            new_end = datetime.strptime(f"{new_rehearsal['date']} {new_rehearsal['end_time']}", "%d/%m/%Y %H:%M")
        except ValueError:
            return False

        for i, rehearsal in enumerate(self.all_rehearsals_cache):
            if i == updating_id:
                continue
            
            existing_start = datetime.strptime(f"{rehearsal['date']} {rehearsal['start_time']}", "%d/%m/%Y %H:%M")
            existing_end = datetime.strptime(f"{rehearsal['date']} {rehearsal['end_time']}", "%d/%m/%Y %H:%M")

            if new_start < existing_end and new_end > existing_start:
                messagebox.showerror("Conflito de Horário", f"Este horário conflita com o ensaio da banda '{rehearsal['band_name']}'.")
                return True
        return False

    def save_rehearsals(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.all_rehearsals_cache, f, indent=4, ensure_ascii=False)
            
    def populate_treeview(self, rehearsals):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for rehearsal in rehearsals:
            values = tuple(rehearsal.get(col, '') for col in self.columns_map.keys())
            status_tag = str(rehearsal.get("status", "Pendente")).lower()
            self.tree.insert("", "end", values=values, tags=(status_tag,))

    def load_rehearsals(self):
        if os.path.exists(self.data_file) and os.path.getsize(self.data_file) > 0:
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.all_rehearsals_cache = json.load(f)
            except (json.JSONDecodeError, KeyError) as e:
                messagebox.showerror("Erro de Leitura", f"Não foi possível ler o arquivo de dados: {e}")
                self.all_rehearsals_cache = []
        else:
            self.all_rehearsals_cache = []
        
        self.populate_treeview(self.all_rehearsals_cache)
        self.sort_column("date", False)

    def add_rehearsal(self):
        new_rehearsal = self.get_data_as_dict()
        if not new_rehearsal:
            return

        if self.check_conflict(new_rehearsal):
            return

        self.all_rehearsals_cache.append(new_rehearsal)
        self.save_rehearsals()
        self.populate_treeview(self.all_rehearsals_cache)
        self.sort_column("date", False)
        self.clear_form()
        messagebox.showinfo("Sucesso", "Ensaio adicionado com sucesso!")

    def update_rehearsal(self):
        if self.selected_rehearsal_id is None:
            messagebox.showwarning("Nenhuma Seleção", "Selecione um ensaio da lista para atualizar.")
            return
            
        updated_rehearsal = self.get_data_as_dict()
        if not updated_rehearsal:
            return

        if self.check_conflict(updated_rehearsal, updating_id=self.selected_rehearsal_id):
            return
        
        self.all_rehearsals_cache[self.selected_rehearsal_id] = updated_rehearsal
        self.save_rehearsals()
        self.populate_treeview(self.all_rehearsals_cache)
        self.sort_column("date", False)
        self.clear_form()
        messagebox.showinfo("Sucesso", "Ensaio atualizado com sucesso!")
        
    def delete_rehearsal(self):
        if self.selected_rehearsal_id is None:
            messagebox.showwarning("Nenhuma Seleção", "Selecione um ensaio da lista para deletar.")
            return
        
        if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir o ensaio da banda '{self.all_rehearsals_cache[self.selected_rehearsal_id]['band_name']}'?"):
            del self.all_rehearsals_cache[self.selected_rehearsal_id]
            self.save_rehearsals()
            self.populate_treeview(self.all_rehearsals_cache)
            self.clear_form()
            messagebox.showinfo("Excluído", "Ensaio removido com sucesso.")

    def on_item_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            self.selected_rehearsal_id = None
            return

        selected_item_values = self.tree.item(selected_items[0], "values")
        
        try:
            self.selected_rehearsal_id = [tuple(r.values()) for r in self.all_rehearsals_cache].index(selected_item_values)
        except ValueError:
            self.selected_rehearsal_id = None
            self.clear_form()
            return

        key_map = list(self.columns_map.keys())
        for i, field_key in enumerate(self.fields):
            entry = self.entries[field_key]
            value = self.all_rehearsals_cache[self.selected_rehearsal_id][key_map[i]]
            
            if isinstance(entry, DateEntry):
                entry.set_date(datetime.strptime(value, "%d/%m/%Y"))
            elif isinstance(entry, ttk.Combobox):
                entry.set(value)
            else:
                entry.delete(0, "end")
                entry.insert(0, value)

    def clear_form(self):
        self.selected_rehearsal_id = None
        for name, entry in self.entries.items():
            if isinstance(entry, (ttk.Entry)):
                entry.delete(0, "end")
            elif isinstance(entry, ttk.Combobox):
                entry.set('')
            elif isinstance(entry, DateEntry):
                entry.delete(0, "end")

        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection()[0])

    def sort_column(self, col, reverse):
        try:
            if col == "date":
                self.all_rehearsals_cache.sort(key=lambda r: datetime.strptime(r[col], "%d/%m/%Y"), reverse=reverse)
            elif col == "price":
                self.all_rehearsals_cache.sort(key=lambda r: float(str(r[col]).replace(",",".")), reverse=reverse)
            else:
                self.all_rehearsals_cache.sort(key=lambda r: r.get(col, "").lower(), reverse=reverse)
            
            self.populate_treeview(self.all_rehearsals_cache)
            self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))
        except (ValueError, IndexError, KeyError):
             messagebox.showerror("Erro de Ordenação", "Não foi possível ordenar a coluna. Verifique os dados.")

    def search_rehearsals(self, event=None):
        query = self.search_entry.get().lower()
        if not query:
            self.populate_treeview(self.all_rehearsals_cache)
            return
            
        filtered_rehearsals = [
            rehearsal for rehearsal in self.all_rehearsals_cache 
            if query in str(rehearsal['band_name']).lower() or \
               query in str(rehearsal['contact']).lower() or \
               query in str(rehearsal['date']).lower()
        ]
        self.populate_treeview(filtered_rehearsals)


if __name__ == "__main__":
    root = tk.Tk()
    app = RehearsalSchedulerApp(root)
    root.mainloop()