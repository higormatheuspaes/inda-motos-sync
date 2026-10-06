import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
import status_manager
import sync_engine

COR_FUNDO = "#f4f6f8"
COR_CARD = "#ffffff"
COR_TEXTO = "#1f2937"
COR_TEXTO_SECUNDARIO = "#6b7280"
COR_SUCESSO = "#16a34a"
COR_ERRO = "#dc2626"
COR_PRIMARIA = "#2563eb"
COR_PRIMARIA_HOVER = "#1d4ed8"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sincronização Inda Motos")
        self.geometry("880x620")
        self.resizable(False, False)
        self.configure(bg=COR_FUNDO)

        # precisa vir antes de _montar_layout, que já usa self.logo_img
        self.logo_img = tk.PhotoImage(file="assets/logo_indamotos.png").zoom(2, 2).subsample(3, 3)

        self._configurar_estilos()
        self._montar_layout()
        self.carregar_tela()

    # ------------------------------------------------------------------
    def _configurar_estilos(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background=COR_CARD,
            fieldbackground=COR_CARD,
            foreground=COR_TEXTO,
            rowheight=28,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#e5e7eb",
            foreground=COR_TEXTO,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", COR_TEXTO)],
        )

        style.configure(
            "Primaria.TButton",
            background=COR_PRIMARIA,
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            padding=(16, 10),
            borderwidth=0,
            focuscolor=COR_PRIMARIA,
        )
        style.map(
            "Primaria.TButton",
            background=[("active", COR_PRIMARIA_HOVER), ("disabled", "#9ca3af")],
        )

        style.configure(
            "Verde.Horizontal.TProgressbar",
            background=COR_SUCESSO,
            troughcolor="#e5e7eb",
            borderwidth=0,
        )

        style.configure("TNotebook", background=COR_FUNDO, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            font=("Segoe UI", 10, "bold"),
            padding=(16, 8),
            background="#e5e7eb",
            foreground=COR_TEXTO_SECUNDARIO,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", COR_CARD)],
            foreground=[("selected", COR_TEXTO)],
        )

    # ------------------------------------------------------------------
    def _montar_layout(self):
        # Cabeçalho
        header = tk.Frame(self, bg=COR_FUNDO)
        header.pack(fill="x", padx=24, pady=(20, 10))

        logo_label = tk.Label(header, image=self.logo_img, bg=COR_FUNDO)
        logo_label.pack(anchor="center", pady=(0, 8))

        tk.Label(
            header, text="Sincronização Inda Motos",
            font=("Segoe UI", 16, "bold"), bg=COR_FUNDO, fg=COR_TEXTO,
        ).pack(anchor="w")

        tk.Label(
            header, text="Estoque e preço — Firebird → Magazord",
            font=("Segoe UI", 10), bg=COR_FUNDO, fg=COR_TEXTO_SECUNDARIO,
        ).pack(anchor="w")

        # Card de status
        status_card = tk.Frame(self, bg=COR_CARD, highlightbackground="#e5e7eb", highlightthickness=1)
        status_card.pack(fill="x", padx=24, pady=10)

        status_inner = tk.Frame(status_card, bg=COR_CARD)
        status_inner.pack(fill="x", padx=18, pady=14)

        self.label_status_titulo = tk.Label(
            status_inner, text="Carregando...",
            font=("Segoe UI", 11, "bold"), bg=COR_CARD, fg=COR_TEXTO,
        )
        self.label_status_titulo.pack(anchor="w")

        self.label_status_detalhe = tk.Label(
            status_inner, text="",
            font=("Segoe UI", 9), bg=COR_CARD, fg=COR_TEXTO_SECUNDARIO,
        )
        self.label_status_detalhe.pack(anchor="w", pady=(2, 0))

        self.botao_rerun = ttk.Button(
            status_inner, text="Sincronizar agora",
            style="Primaria.TButton", command=self.rodar_sincronizacao,
        )
        self.botao_rerun.pack(anchor="e")

        self.progresso = ttk.Progressbar(
            status_inner, orient="horizontal", mode="indeterminate",
            style="Verde.Horizontal.TProgressbar",
        )

        # Abas: Produtos sincronizados / Erros
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        aba_produtos = tk.Frame(self.notebook, bg=COR_CARD)
        aba_erros = tk.Frame(self.notebook, bg=COR_CARD)
        aba_alertas = tk.Frame(self.notebook, bg=COR_CARD)

        self.notebook.add(aba_produtos, text="Produtos sincronizados")
        self.notebook.add(aba_erros, text="Erros")
        self.notebook.add(aba_alertas, text="Alertas")

        tk.Label(
            aba_produtos,
            text="As alterações podem levar até 1 hora para aparecer no site.",
            font=("Segoe UI", 9), bg=COR_CARD, fg=COR_TEXTO_SECUNDARIO,
        ).pack(anchor="w", padx=16, pady=(12, 0))

        # --- Filtro de produtos ---
        filtro_frame = tk.Frame(aba_produtos, bg=COR_CARD)
        filtro_frame.pack(fill="x", padx=16, pady=(8, 0))

        tk.Label(
            filtro_frame, text="Buscar (SKU ou produto):",
            font=("Segoe UI", 9), bg=COR_CARD, fg=COR_TEXTO_SECUNDARIO,
        ).pack(side="left", padx=(0, 8))

        self.var_filtro = tk.StringVar()
        self.var_filtro.trace_add("write", lambda *_: self._filtrar_produtos())
        entrada_filtro = ttk.Entry(filtro_frame, textvariable=self.var_filtro, font=("Segoe UI", 10))
        entrada_filtro.pack(side="left", fill="x", expand=True)

        # --- Tabela de produtos ---
        colunas = ("sku", "nome", "estoque", "preco")
        self.tabela = ttk.Treeview(aba_produtos, columns=colunas, show="headings")
        self.tabela.heading("sku", text="SKU")
        self.tabela.heading("nome", text="Produto")
        self.tabela.heading("estoque", text="Estoque (antes → depois)")
        self.tabela.heading("preco", text="Preço (antes → depois)")

        self.tabela.column("sku", width=70, anchor="center")
        self.tabela.column("nome", width=280)
        self.tabela.column("estoque", width=200, anchor="center")
        self.tabela.column("preco", width=200, anchor="center")

        scroll_produtos = ttk.Scrollbar(aba_produtos, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll_produtos.set)

        self.tabela.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        scroll_produtos.pack(side="right", fill="y", padx=(0, 16), pady=16)

        # --- Tabela de erros ---
        colunas_erro = ("sku", "nome", "estoque", "preco", "mensagem")
        self.tabela_erros = ttk.Treeview(aba_erros, columns=colunas_erro, show="headings")
        self.tabela_erros.heading("sku", text="SKU")
        self.tabela_erros.heading("nome", text="Produto")
        self.tabela_erros.heading("estoque", text="Estoque (antes → depois)")
        self.tabela_erros.heading("preco", text="Preço (antes → depois)")
        self.tabela_erros.heading("mensagem", text="Mensagem de erro")
        self.tabela_erros.column("sku", width=70, anchor="center")
        self.tabela_erros.column("nome", width=200)
        self.tabela_erros.column("estoque", width=150, anchor="center")
        self.tabela_erros.column("preco", width=150, anchor="center")
        self.tabela_erros.column("mensagem", width=280)

        scroll_erros = ttk.Scrollbar(aba_erros, orient="vertical", command=self.tabela_erros.yview)
        self.tabela_erros.configure(yscrollcommand=scroll_erros.set)

        self.tabela_erros.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        scroll_erros.pack(side="right", fill="y", padx=(0, 16), pady=16)

        tk.Label(
            aba_alertas,
            text="Itens com variação grande. Não foram enviados à Magazord: confira e sincronize um a um.",
            font=("Segoe UI", 9), bg=COR_CARD, fg=COR_TEXTO_SECUNDARIO,
        ).pack(anchor="w", padx=16, pady=(12, 0))

        colunas_alerta = ("sku", "nome_banco", "nome_magazord", "estoque", "preco", "motivo")
        self.tabela_alertas = ttk.Treeview(aba_alertas, columns=colunas_alerta, show="headings", selectmode="browse")
        self.tabela_alertas.heading("sku", text="SKU")
        self.tabela_alertas.heading("nome_banco", text="Produto (banco)")
        self.tabela_alertas.heading("nome_magazord", text="Produto (Magazord)")
        self.tabela_alertas.heading("estoque", text="Estoque (Magazord → banco)")
        self.tabela_alertas.heading("preco", text="Preço (Magazord → banco)")
        self.tabela_alertas.heading("motivo", text="Motivo")
        self.tabela_alertas.column("sku", width=60, anchor="center")
        self.tabela_alertas.column("nome_banco", width=220)
        self.tabela_alertas.column("nome_magazord", width=220)
        self.tabela_alertas.column("estoque", width=150, anchor="center")
        self.tabela_alertas.column("preco", width=150, anchor="center")
        self.tabela_alertas.column("motivo", width=200)

        scroll_alertas = ttk.Scrollbar(aba_alertas, orient="vertical", command=self.tabela_alertas.yview)
        self.tabela_alertas.configure(yscrollcommand=scroll_alertas.set)

        self.tabela_alertas.pack(side="top", fill="both", expand=True, padx=(16, 0), pady=(8, 0))
        scroll_alertas.pack(side="right", fill="y", padx=(0, 16), pady=(8, 0))

        self.botao_aprovar = ttk.Button(
            aba_alertas, text="Sincronizar selecionado",
            style="Primaria.TButton", command=self.aprovar_alerta_selecionado,
        )
        self.botao_aprovar.pack(anchor="e", padx=16, pady=12)
        self.tabela_alertas.bind("<<TreeviewSelect>>", lambda _: self._atualizar_botao_aprovar())
        self._alertas_por_sku = {}
        self._atualizar_botao_aprovar()

    # ------------------------------------------------------------------
    def _atualizar_titulo_aba_erros(self, total_erros):
        texto = f"Erros ({total_erros})" if total_erros else "Erros"
        self.notebook.tab(1, text=texto)

    def _atualizar_titulo_aba_alertas(self, total_alertas):
        texto = f"Alertas ({total_alertas})" if total_alertas else "Alertas"
        self.notebook.tab(2, text=texto)

    def carregar_tela(self):
        status = status_manager.carregar_status()

        if status["ultima_execucao"]:
            data_formatada = status["ultima_execucao"][:16].replace("T", " às ")
            if status["sucesso"]:
                self.label_status_titulo.config(text="✓ Última sincronização concluída", fg=COR_SUCESSO)
            else:
                self.label_status_titulo.config(
                    text=f"⚠ Última sincronização com {status['total_erros']} erro(s)", fg=COR_ERRO
                )
            self.label_status_detalhe.config(
                text=f"{data_formatada}  •  {status['total_produtos']} produto(s) atualizado(s)"
            )
        else:
            self.label_status_titulo.config(text="Nenhuma sincronização realizada ainda", fg=COR_TEXTO)
            self.label_status_detalhe.config(text="Clique em \"Sincronizar agora\" para começar")

        self._produtos_cache = status["produtos"]
        self._filtrar_produtos()

        for item in self.tabela_erros.get_children():
            self.tabela_erros.delete(item)
        for e in status["erros"]:
            estoque_txt = f"{e.get('estoque_antigo', '-')}  →  {e.get('estoque_novo', '-')}"
            preco_txt = f"{e.get('preco_antigo', '-')}  →  {e.get('preco_novo', '-')}"
            self.tabela_erros.insert(
                "", "end",
                values=(e["sku"], e.get("nome", ""), estoque_txt, preco_txt, e["mensagem"]),
            )

        self._atualizar_titulo_aba_erros(status["total_erros"])

        for item in self.tabela_alertas.get_children():
            self.tabela_alertas.delete(item)
        self._alertas_por_sku = {}
        for a in status.get("alertas", []):
            self._alertas_por_sku[a["sku"]] = a
            self.tabela_alertas.insert(
                "", "end", iid=a["sku"],
                values=(
                    a["sku"],
                    a["nome_banco"],
                    a["nome_magazord"],
                    f"{a.get('estoque_antigo', '-')}  →  {a.get('estoque_novo', '-')}",
                    f"{a.get('preco_antigo', '-')}  →  {a.get('preco_novo', '-')}",
                    ", ".join(a["motivos"]),
                ),
            )

        self._atualizar_titulo_aba_alertas(len(status.get("alertas", [])))
        self._atualizar_botao_aprovar()

    def _atualizar_botao_aprovar(self):
        selecionado = self.tabela_alertas.selection()
        estado = "normal" if selecionado and str(self.botao_rerun["state"]) != "disabled" else "disabled"
        self.botao_aprovar.config(state=estado)

    def aprovar_alerta_selecionado(self):
        selecionado = self.tabela_alertas.selection()
        if not selecionado:
            return
        item = self._alertas_por_sku[selecionado[0]]
        confirmado = messagebox.askyesno(
            "Confirmar sincronização",
            f"SKU {item['sku']} — {item['nome_banco']}\n\n"
            f"Estoque: {item.get('estoque_antigo', '-')} → {item['estoque_novo']}\n"
            f"Preço: {item.get('preco_antigo', '-')} → {item['preco_novo']}\n\n"
            f"Motivo: {', '.join(item['motivos'])}\n\n"
            "Enviar esta alteração para a Magazord?",
            parent=self,
        )
        if not confirmado:
            return
        self.botao_aprovar.config(state="disabled")
        threading.Thread(target=self._aprovar_em_thread, args=(item,), daemon=True).start()

    def _aprovar_em_thread(self, item):
        try:
            ok, mensagem = sync_engine.sincronizar_alerta(item)
        except Exception as e:
            logging.exception("Falha ao sincronizar item aprovado")
            ok, mensagem = False, str(e)
        self.after(0, lambda: self._finalizou_aprovacao(item["sku"], ok, mensagem))

    def _finalizou_aprovacao(self, sku, ok, mensagem):
        if not ok:
            messagebox.showerror("Falha ao sincronizar", f"SKU {sku}: {mensagem}", parent=self)
        self.carregar_tela()

    # ------------------------------------------------------------------
    def _filtrar_produtos(self):
        termo = self.var_filtro.get().strip().lower()

        for item in self.tabela.get_children():
            self.tabela.delete(item)

        for p in self._produtos_cache:
            if termo and termo not in str(p["sku"]).lower() and termo not in p["nome"].lower():
                continue
            estoque_txt = f"{p.get('estoque_antigo', '-')}  →  {p.get('estoque_novo', '-')}"
            preco_txt = f"{p.get('preco_antigo', '-')}  →  {p.get('preco_novo', '-')}"
            self.tabela.insert("", "end", values=(p["sku"], p["nome"], estoque_txt, preco_txt))

    # ------------------------------------------------------------------
    def rodar_sincronizacao(self):
        self.botao_rerun.config(state="disabled", text="Sincronizando...")
        self._atualizar_botao_aprovar()
        self.progresso.pack(anchor="e", fill="x", pady=(8, 0))
        self.progresso.configure(mode="indeterminate")
        self.progresso.start(10)
        thread = threading.Thread(target=self._rodar_em_thread)
        thread.start()

    def _rodar_em_thread(self):
        try:
            sync_engine.executar_sincronizacao(on_progress=self._progresso_thread_segura)
        except Exception as e:
            logging.exception("Falha na sincronização")
            mensagem = str(e)
            self.after(0, lambda: self._falhou(mensagem))
            return
        self.after(0, self._finalizou)

    def _falhou(self, mensagem):
        self.botao_rerun.config(state="normal", text="Sincronizar agora")
        self.progresso.stop()
        self.progresso.pack_forget()
        resumo = " ".join(mensagem.split())[:160]
        self.label_status_titulo.config(text="⚠ Falha ao sincronizar", fg=COR_ERRO)
        self.label_status_detalhe.config(text=f"{resumo}  (detalhes em logs/sync.log)")
        self._atualizar_botao_aprovar()

    def _progresso_thread_segura(self, atual, total):
        self.after(0, lambda: self._atualizar_progresso(atual, total))

    def _atualizar_progresso(self, atual, total):
        if str(self.progresso["mode"]) == "indeterminate":
            self.progresso.stop()
            self.progresso.configure(mode="determinate", maximum=max(total, 1))
        self.progresso["value"] = atual

    def _finalizou(self):
        self.botao_rerun.config(state="normal", text="Sincronizar agora")
        self.progresso.stop()
        self.progresso.pack_forget()
        self.carregar_tela()