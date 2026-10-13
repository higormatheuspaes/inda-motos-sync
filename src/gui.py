import tkinter as tk
from tkinter import ttk, messagebox
import sys
import threading
import logging
import atualizador
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
        versao = atualizador.versao_local()
        titulo = "Sincronização Inda Motos"
        if versao and versao != "local":
            titulo += f" — build {versao[:7]}"
        self.title(titulo)
        self.geometry("1100x700")
        self.minsize(900, 560)
        self.resizable(True, True)
        self.configure(bg=COR_FUNDO)

        try:
            self.iconbitmap("assets/icone.ico")
        except Exception:
            logging.exception("Falha ao carregar o ícone da janela")

        # precisa vir antes de _montar_layout, que já usa self.logo_img
        self.logo_img = tk.PhotoImage(file="assets/logo_indamotos.png").zoom(2, 2).subsample(3, 3)

        self._configurar_estilos()
        self._montar_layout()
        self.carregar_tela()
        self.after(1000, self._checar_atualizacao_em_segundo_plano)

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
    def _criar_tabela(self, parent, colunas, cabecalhos, larguras):
        """Monta um Treeview com rolagem vertical e horizontal dentro de parent."""
        frame = tk.Frame(parent, bg=COR_CARD)
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        tabela = ttk.Treeview(frame, columns=colunas, show="headings")
        for coluna, titulo in zip(colunas, cabecalhos):
            tabela.heading(coluna, text=titulo)
            tabela.column(coluna, width=larguras.get(coluna, 150), anchor=larguras.get(f"{coluna}_anchor", "w"))

        scroll_v = ttk.Scrollbar(frame, orient="vertical", command=tabela.yview)
        scroll_h = ttk.Scrollbar(frame, orient="horizontal", command=tabela.xview)
        tabela.configure(yscrollcommand=scroll_v.set, xscrollcommand=scroll_h.set)

        tabela.grid(row=0, column=0, sticky="nsew")
        scroll_v.grid(row=0, column=1, sticky="ns")
        scroll_h.grid(row=1, column=0, sticky="ew")
        return tabela

    def _criar_lista(self, parent, colunas):
        """Lista de linhas com cabeçalho fixo, rolagem vertical e espaço pro botão de
        cada linha. colunas: lista de (titulo, largura_em_caracteres)."""
        container = tk.Frame(parent, bg=COR_CARD)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        cabecalho = tk.Frame(container, bg="#e5e7eb")
        cabecalho.pack(fill="x")
        for titulo, largura in colunas:
            tk.Label(
                cabecalho, text=titulo, font=("Segoe UI", 9, "bold"), bg="#e5e7eb", fg=COR_TEXTO,
                width=largura, anchor="w", padx=6, pady=6,
            ).pack(side="left")
        tk.Frame(cabecalho, bg="#e5e7eb", width=120).pack(side="left")

        area = tk.Frame(container, bg=COR_CARD)
        area.pack(fill="both", expand=True)
        canvas = tk.Canvas(area, bg=COR_CARD, highlightthickness=0)
        scroll_v = ttk.Scrollbar(area, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll_v.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll_v.pack(side="right", fill="y")

        corpo = tk.Frame(canvas, bg=COR_CARD)
        janela = canvas.create_window((0, 0), window=corpo, anchor="nw")
        corpo.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(janela, width=e.width))

        rolar = lambda e: canvas.yview_scroll(int(-e.delta / 40), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", rolar))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        return corpo

    def _linha_lista(self, corpo, valores_larguras, texto_botao, comando):
        linha = tk.Frame(corpo, bg=COR_CARD)
        linha.pack(fill="x")
        for valor, largura in valores_larguras:
            tk.Label(
                linha, text=valor, width=largura, anchor="w", justify="left",
                wraplength=largura * 7, bg=COR_CARD, fg=COR_TEXTO,
                font=("Segoe UI", 9), padx=6, pady=6,
            ).pack(side="left", fill="y")
        botao = ttk.Button(linha, text=texto_botao, command=comando)
        botao.pack(side="left", padx=8, pady=4)
        tk.Frame(corpo, bg="#e5e7eb", height=1).pack(fill="x")
        return botao

    def _ver_detalhe(self, titulo, linhas):
        top = tk.Toplevel(self)
        top.title(titulo)
        top.configure(bg=COR_CARD)
        top.geometry("520x320")
        texto = tk.Text(
            top, wrap="word", font=("Segoe UI", 10), bg=COR_CARD, fg=COR_TEXTO,
            relief="flat", padx=12, pady=12,
        )
        texto.insert("1.0", "\n".join(linhas))
        texto.config(state="disabled")
        texto.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        ttk.Button(top, text="Fechar", command=top.destroy).pack(pady=(0, 12))
        top.transient(self)
        top.grab_set()

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

        versao = atualizador.versao_local()
        subtitulo = "Estoque e preço — Firebird → Magazord"
        if versao:
            subtitulo += f"  •  versão {versao[:7]}"
        tk.Label(
            header, text=subtitulo,
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
        self.tabela = self._criar_tabela(
            aba_produtos,
            ("sku", "nome", "estoque", "preco"),
            ("SKU", "Produto", "Estoque (antes → depois)", "Preço (antes → depois)"),
            {"sku": 70, "sku_anchor": "center", "nome": 320, "estoque": 180, "estoque_anchor": "center",
             "preco": 180, "preco_anchor": "center"},
        )
        self.tabela.bind("<Double-1>", self._ver_detalhe_produto)

        # --- Lista de erros ---
        self._corpo_erros = self._criar_lista(
            aba_erros,
            [("SKU", 6), ("Produto", 26), ("Estoque (antes → depois)", 16),
             ("Preço (antes → depois)", 14), ("Mensagem de erro", 42)],
        )
        self._erros_por_sku = {}
        self._botoes_erro = {}

        tk.Label(
            aba_alertas,
            text="Itens com variação grande de preço/estoque. Já foram enviados à Magazord — confira, e se "
                 "algum não devia ter mudado assim, clique em Reverter.",
            font=("Segoe UI", 9), bg=COR_CARD, fg=COR_TEXTO_SECUNDARIO,
        ).pack(anchor="w", padx=16, pady=(12, 0))

        # --- Lista de alertas ---
        self._corpo_alertas = self._criar_lista(
            aba_alertas,
            [("SKU", 5), ("Produto (banco)", 24), ("Produto (Magazord)", 24),
             ("Estoque (Magazord → banco)", 16), ("Preço (Magazord → banco)", 14), ("Motivo", 18)],
        )
        self._alertas_por_sku = {}
        self._botoes_alerta = {}

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

        for widget in self._corpo_erros.winfo_children():
            widget.destroy()
        self._erros_por_sku = {}
        self._botoes_erro = {}
        for e in status["erros"]:
            sku = e["sku"]
            self._erros_por_sku[sku] = e
            estoque_txt = f"{e.get('estoque_antigo', '-')}  →  {e.get('estoque_novo', '-')}"
            preco_txt = f"{e.get('preco_antigo', '-')}  →  {e.get('preco_novo', '-')}"
            self._botoes_erro[sku] = self._linha_lista(
                self._corpo_erros,
                [(sku, 6), (e.get("nome", ""), 26), (estoque_txt, 16), (preco_txt, 14), (e["mensagem"], 42)],
                "↻ Tentar de novo",
                lambda sku=sku: self._iniciar_tentar_de_novo(sku),
            )

        self._atualizar_titulo_aba_erros(status["total_erros"])

        for widget in self._corpo_alertas.winfo_children():
            widget.destroy()
        self._alertas_por_sku = {}
        self._botoes_alerta = {}
        for a in status.get("alertas", []):
            sku = a["sku"]
            self._alertas_por_sku[sku] = a
            self._botoes_alerta[sku] = self._linha_lista(
                self._corpo_alertas,
                [
                    (sku, 5), (a["nome_banco"], 24), (a["nome_magazord"], 24),
                    (f"{a.get('estoque_antigo', '-')}  →  {a.get('estoque_novo', '-')}", 16),
                    (f"{a.get('preco_antigo', '-')}  →  {a.get('preco_novo', '-')}", 14),
                    (", ".join(a["motivos"]), 18),
                ],
                "↺ Reverter",
                lambda sku=sku: self._iniciar_reverter_alerta(sku),
            )

        self._atualizar_titulo_aba_alertas(len(status.get("alertas", [])))

    # ------------------------------------------------------------------
    def _ocupado(self):
        return str(self.botao_rerun["state"]) == "disabled"

    def _iniciar_reverter_alerta(self, sku):
        if self._ocupado():
            return
        item = self._alertas_por_sku.get(sku)
        if not item:
            return
        confirmado = messagebox.askyesno(
            "Confirmar reversão",
            f"SKU {sku} — {item['nome_banco']}\n\n"
            f"Isso vai voltar na Magazord para os valores de antes desta sincronização:\n"
            f"Estoque: {item['estoque_novo']} → {item.get('estoque_antigo', '-')}\n"
            f"Preço: {item['preco_novo']} → {item.get('preco_antigo', '-')}\n\n"
            f"Motivo do alerta: {', '.join(item['motivos'])}\n\n"
            "Reverter esse item?",
            parent=self,
        )
        if not confirmado:
            return
        botao = self._botoes_alerta.get(sku)
        if botao:
            botao.config(state="disabled", text="Revertendo...")
        threading.Thread(target=self._reverter_em_thread, args=(item,), daemon=True).start()

    def _reverter_em_thread(self, item):
        try:
            ok, mensagem = sync_engine.reverter_alerta(item)
        except Exception as e:
            logging.exception("Falha ao reverter alerta")
            ok, mensagem = False, str(e)
        self.after(0, lambda: self._finalizou_reversao(item["sku"], ok, mensagem))

    def _finalizou_reversao(self, sku, ok, mensagem):
        if not ok:
            messagebox.showerror("Falha ao reverter", f"SKU {sku}: {mensagem}", parent=self)
        self.carregar_tela()

    def _iniciar_tentar_de_novo(self, sku):
        if self._ocupado():
            return
        item = self._erros_por_sku.get(sku)
        if not item:
            return
        botao = self._botoes_erro.get(sku)
        if botao:
            botao.config(state="disabled", text="Tentando...")
        threading.Thread(target=self._tentar_de_novo_em_thread, args=(item,), daemon=True).start()

    def _tentar_de_novo_em_thread(self, item):
        try:
            resultado, mensagem = sync_engine.tentar_novamente(item)
        except Exception as e:
            logging.exception("Falha ao tentar de novo")
            resultado, mensagem = "erro", str(e)
        self.after(0, lambda: self._finalizou_tentativa(item["sku"], resultado, mensagem))

    def _finalizou_tentativa(self, sku, resultado, mensagem):
        if resultado == "sincronizado":
            messagebox.showinfo("Sincronizado", f"SKU {sku}: {mensagem}", parent=self)
        elif resultado == "alerta":
            messagebox.showinfo("Movido para Alertas", f"SKU {sku}: {mensagem}", parent=self)
        else:
            messagebox.showerror("Ainda bloqueado", f"SKU {sku}: {mensagem}", parent=self)
        self.carregar_tela()

    def _ver_detalhe_produto(self, _event):
        sel = self.tabela.selection()
        if not sel:
            return
        sku, nome, estoque, preco = self.tabela.item(sel[0], "values")
        self._ver_detalhe(f"Produto — SKU {sku}", [f"Produto: {nome}", f"Estoque: {estoque}", f"Preço: {preco}"])

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
        for botao in list(self._botoes_erro.values()) + list(self._botoes_alerta.values()):
            botao.config(state="disabled")
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

    # ------------------------------------------------------------------
    def _checar_atualizacao_em_segundo_plano(self):
        threading.Thread(target=self._checar_atualizacao_thread, daemon=True).start()

    def _checar_atualizacao_thread(self):
        try:
            info = atualizador.verificar_atualizacao()
        except Exception:
            logging.exception("Falha ao checar atualização")
            return
        if info:
            self.after(0, lambda: self._perguntar_atualizacao(*info))

    def _perguntar_atualizacao(self, versao, url):
        confirmado = messagebox.askyesno(
            "Atualização disponível",
            "Tem uma versão nova do sistema disponível.\n\n"
            "Atualizar agora? O programa vai fechar e abrir de novo sozinho.",
            parent=self,
        )
        if not confirmado:
            return
        aviso = tk.Toplevel(self)
        aviso.title("Atualizando")
        aviso.configure(bg=COR_CARD)
        aviso.resizable(False, False)
        tk.Label(
            aviso, text="Baixando atualização, aguarde...",
            font=("Segoe UI", 10), bg=COR_CARD, fg=COR_TEXTO, padx=32, pady=32,
        ).pack()
        aviso.transient(self)
        aviso.grab_set()
        threading.Thread(target=self._aplicar_atualizacao_thread, args=(versao, url, aviso), daemon=True).start()

    def _aplicar_atualizacao_thread(self, versao, url, aviso):
        try:
            atualizador.aplicar_atualizacao(versao, url)
        except Exception as e:
            logging.exception("Falha ao aplicar atualização")
            self.after(0, lambda: self._falhou_atualizacao(aviso, str(e)))
            return
        self.after(0, lambda: self._atualizacao_concluida(aviso))

    def _falhou_atualizacao(self, aviso, mensagem):
        aviso.destroy()
        messagebox.showerror("Falha ao atualizar", mensagem, parent=self)

    def _atualizacao_concluida(self, aviso):
        aviso.destroy()
        self.destroy()
        sys.exit(0)