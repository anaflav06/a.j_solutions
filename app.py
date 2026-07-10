
import io
import os
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from supabase import Client, create_client


# ============================================================
# CONFIGURAÇÕES GERAIS
# ============================================================

EMPRESA = "A.J Solutions"
TITULO_APP = "Gestão de Ordens de Serviço"
TABELA_OS = "ordens_servico"

st.set_page_config(
    page_title=f"{EMPRESA} | {TITULO_APP}",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# ESTILO VISUAL
# ============================================================

st.markdown(
    """
    <style>
        .stApp {
            background-color: #f6f8fb;
        }

        .main .block-container {
            max-width: 1250px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }

        .aj-header {
            background: linear-gradient(135deg, #111827, #263449);
            color: white;
            border-radius: 18px;
            padding: 24px 28px;
            margin-bottom: 20px;
            box-shadow: 0 8px 24px rgba(17, 24, 39, 0.14);
        }

        .aj-header h1 {
            margin: 0;
            font-size: 2rem;
        }

        .aj-header p {
            margin: 8px 0 0 0;
            opacity: 0.86;
        }

        .aj-card {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 18px;
            box-shadow: 0 4px 14px rgba(17, 24, 39, 0.05);
            margin-bottom: 14px;
        }

        .status-pill {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            background: #e8eef8;
            color: #1f3b64;
        }

        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #e5e7eb;
            padding: 16px;
            border-radius: 14px;
        }

        div[data-testid="stForm"] {
            background: white;
            padding: 22px;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
        }

        .stButton > button,
        .stDownloadButton > button,
        .stFormSubmitButton > button {
            border-radius: 10px;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CONEXÃO COM SUPABASE
# ============================================================

@st.cache_resource
def get_supabase() -> Optional[Client]:
    """
    Obtém as credenciais pelo st.secrets no Streamlit Cloud.

    Cadastre em:
    Settings > Secrets

    SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
    SUPABASE_KEY = "SUA-CHAVE"
    """
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None


supabase = get_supabase()


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def moeda_para_decimal(valor: Any) -> float:
    if valor is None:
        return 0.0

    if isinstance(valor, (int, float, Decimal)):
        return float(valor)

    texto = str(valor).strip().replace("R$", "").replace(" ", "")

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(Decimal(texto))
    except (InvalidOperation, ValueError):
        return 0.0


def formatar_moeda(valor: Any) -> str:
    numero = moeda_para_decimal(valor)
    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_numero_os() -> str:
    agora = datetime.now()
    sufixo = uuid.uuid4().hex[:4].upper()
    return f"AJ-{agora:%Y%m%d}-{sufixo}"


def limpar_texto(valor: Any) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def salvar_os(dados: Dict[str, Any]) -> Dict[str, Any]:
    if supabase is None:
        raise RuntimeError(
            "Supabase não configurado. Adicione SUPABASE_URL e SUPABASE_KEY "
            "nos Secrets do Streamlit."
        )

    resposta = supabase.table(TABELA_OS).insert(dados).execute()

    if not resposta.data:
        raise RuntimeError("O Supabase não retornou confirmação do cadastro.")

    return resposta.data[0]


def listar_os() -> List[Dict[str, Any]]:
    if supabase is None:
        return []

    resposta = (
        supabase.table(TABELA_OS)
        .select("*")
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )
    return resposta.data or []


def atualizar_status_os(os_id: int, novo_status: str) -> None:
    if supabase is None:
        raise RuntimeError("Supabase não configurado.")

    supabase.table(TABELA_OS).update(
        {
            "status": novo_status,
            "updated_at": datetime.now().isoformat(),
        }
    ).eq("id", os_id).execute()


def excluir_os(os_id: int) -> None:
    if supabase is None:
        raise RuntimeError("Supabase não configurado.")

    supabase.table(TABELA_OS).delete().eq("id", os_id).execute()


def texto_pdf(texto: Any) -> str:
    conteudo = limpar_texto(texto)
    if not conteudo:
        return "Não informado"
    return (
        conteudo.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def gerar_pdf_os(dados: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Ordem de Serviço {dados.get('numero_os', '')}",
        author=EMPRESA,
    )

    estilos = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "TituloAJ",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111827"),
        spaceAfter=4,
    )

    estilo_subtitulo = ParagraphStyle(
        "SubtituloAJ",
        parent=estilos["Normal"],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=12,
    )

    estilo_secao = ParagraphStyle(
        "SecaoAJ",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.white,
        backColor=colors.HexColor("#263449"),
        leftIndent=5,
        spaceBefore=8,
        spaceAfter=6,
    )

    estilo_normal = ParagraphStyle(
        "NormalAJ",
        parent=estilos["Normal"],
        fontSize=8.5,
        leading=11,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#111827"),
    )

    estilo_pequeno = ParagraphStyle(
        "PequenoAJ",
        parent=estilo_normal,
        fontSize=7.5,
        leading=9.5,
    )

    elementos = [
        Paragraph(EMPRESA, estilo_titulo),
        Paragraph("FICHA DE SERVIÇO REALIZADO / ORDEM DE SERVIÇO", estilo_subtitulo),
    ]

    cabecalho = [
        [
            Paragraph("<b>Número da OS</b><br/>" + texto_pdf(dados.get("numero_os")), estilo_normal),
            Paragraph("<b>Data de abertura</b><br/>" + texto_pdf(dados.get("data_abertura")), estilo_normal),
            Paragraph("<b>Status</b><br/>" + texto_pdf(dados.get("status")), estilo_normal),
        ]
    ]

    tabela_cabecalho = Table(cabecalho, colWidths=[60 * mm, 55 * mm, 55 * mm])
    tabela_cabecalho.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    elementos.extend([tabela_cabecalho, Spacer(1, 8)])

    def adicionar_secao(titulo: str, linhas: List[List[Any]], larguras: Optional[List[float]] = None):
        elementos.append(Paragraph(titulo, estilo_secao))
        linhas_formatadas = []
        for linha in linhas:
            linha_pdf = []
            for celula in linha:
                linha_pdf.append(Paragraph(texto_pdf(celula), estilo_normal))
            linhas_formatadas.append(linha_pdf)

        tabela = Table(linhas_formatadas, colWidths=larguras, repeatRows=0)
        tabela.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D1D5DB")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ]
            )
        )
        elementos.append(tabela)

    adicionar_secao(
        "DADOS DO CLIENTE",
        [
            [
                f"Cliente / Empresa:\n{dados.get('cliente_nome', '')}",
                f"CPF/CNPJ:\n{dados.get('cliente_documento', '')}",
            ],
            [
                f"Responsável:\n{dados.get('cliente_responsavel', '')}",
                f"Telefone / WhatsApp:\n{dados.get('cliente_telefone', '')}",
            ],
            [
                f"E-mail:\n{dados.get('cliente_email', '')}",
                f"Unidade / Setor:\n{dados.get('cliente_setor', '')}",
            ],
        ],
        [95 * mm, 75 * mm],
    )

    adicionar_secao(
        "DADOS DO EQUIPAMENTO",
        [
            [
                f"Categoria:\n{dados.get('equipamento_categoria', '')}",
                f"Marca:\n{dados.get('equipamento_marca', '')}",
                f"Modelo:\n{dados.get('equipamento_modelo', '')}",
            ],
            [
                f"Número de série:\n{dados.get('equipamento_serie', '')}",
                f"Patrimônio:\n{dados.get('equipamento_patrimonio', '')}",
                f"IMEI / Identificação:\n{dados.get('equipamento_imei', '')}",
            ],
            [
                f"Acessórios recebidos:\n{dados.get('acessorios', '')}",
                f"Estado de entrada:\n{dados.get('estado_entrada', '')}",
                f"Senha informada:\n{dados.get('senha_equipamento', '')}",
            ],
        ],
        [57 * mm, 57 * mm, 56 * mm],
    )

    adicionar_secao(
        "ATENDIMENTO TÉCNICO",
        [
            [f"Problema relatado:\n{dados.get('problema_relatado', '')}"],
            [f"Diagnóstico técnico:\n{dados.get('diagnostico', '')}"],
            [f"Serviço realizado:\n{dados.get('servico_realizado', '')}"],
            [f"Testes finais:\n{dados.get('testes_finais', '')}"],
            [f"Pendências / Recomendações:\n{dados.get('pendencias', '')}"],
        ],
        [170 * mm],
    )

    adicionar_secao(
        "VALORES E GARANTIA",
        [
            [
                f"Peças / Materiais:\n{formatar_moeda(dados.get('valor_pecas', 0))}",
                f"Mão de obra:\n{formatar_moeda(dados.get('valor_mao_obra', 0))}",
                f"Desconto:\n{formatar_moeda(dados.get('desconto', 0))}",
                f"Total:\n{formatar_moeda(dados.get('valor_total', 0))}",
            ],
            [
                f"Garantia:\n{dados.get('garantia_dias', 0)} dia(s)",
                f"Forma de pagamento:\n{dados.get('forma_pagamento', '')}",
                f"Técnico responsável:\n{dados.get('tecnico_responsavel', '')}",
                f"Prioridade:\n{dados.get('prioridade', '')}",
            ],
        ],
        [42.5 * mm, 42.5 * mm, 42.5 * mm, 42.5 * mm],
    )

    elementos.append(Spacer(1, 16))

    assinaturas = Table(
        [
            [
                Paragraph("____________________________________", estilo_normal),
                Paragraph("____________________________________", estilo_normal),
            ],
            [
                Paragraph("Assinatura do técnico", estilo_pequeno),
                Paragraph("Assinatura do cliente / responsável", estilo_pequeno),
            ],
        ],
        colWidths=[85 * mm, 85 * mm],
    )
    assinaturas.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos.append(assinaturas)
    elementos.append(Spacer(1, 12))
    elementos.append(
        Paragraph(
            f"Documento gerado pelo sistema de gestão de serviços da {EMPRESA}.",
            estilo_subtitulo,
        )
    )

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()


def validar_campos_obrigatorios(dados: Dict[str, Any]) -> List[str]:
    obrigatorios = {
        "cliente_nome": "Cliente / Empresa",
        "cliente_telefone": "Telefone / WhatsApp",
        "equipamento_categoria": "Categoria do equipamento",
        "equipamento_marca": "Marca",
        "equipamento_modelo": "Modelo",
        "problema_relatado": "Problema relatado",
        "tecnico_responsavel": "Técnico responsável",
    }

    faltantes = []
    for campo, rotulo in obrigatorios.items():
        if not limpar_texto(dados.get(campo)):
            faltantes.append(rotulo)

    return faltantes


# ============================================================
# COMPONENTES VISUAIS
# ============================================================

def mostrar_cabecalho():
    st.markdown(
        f"""
        <div class="aj-header">
            <h1>🛠️ {EMPRESA}</h1>
            <p>{TITULO_APP} — celulares, notebooks, coletores, impressoras Zebra e outros equipamentos.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def aviso_conexao():
    if supabase is None:
        st.warning(
            "O app está sem conexão com o Supabase. Cadastre `SUPABASE_URL` e "
            "`SUPABASE_KEY` nos Secrets do Streamlit Cloud."
        )


# ============================================================
# PÁGINA: DASHBOARD
# ============================================================

def pagina_dashboard():
    mostrar_cabecalho()
    aviso_conexao()

    registros = listar_os()

    st.subheader("Visão geral")

    if not registros:
        st.info("Ainda não existem ordens de serviço cadastradas.")
        return

    df = pd.DataFrame(registros)

    total = len(df)
    concluidas = int(df["status"].isin(["Serviço concluído", "Entregue ao cliente"]).sum())
    em_andamento = int(
        df["status"].isin(
            [
                "Recebido",
                "Em análise",
                "Aguardando orçamento",
                "Aguardando aprovação",
                "Aprovado",
                "Em manutenção",
                "Aguardando peça",
                "Pronto para retirada",
            ]
        ).sum()
    )
    valor_total = pd.to_numeric(df.get("valor_total", 0), errors="coerce").fillna(0).sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de OS", total)
    c2.metric("Em andamento", em_andamento)
    c3.metric("Concluídas/entregues", concluidas)
    c4.metric("Valor total registrado", formatar_moeda(valor_total))

    st.markdown("### Ordens recentes")

    colunas = [
        "numero_os",
        "data_abertura",
        "cliente_nome",
        "equipamento_categoria",
        "equipamento_marca",
        "equipamento_modelo",
        "status",
        "valor_total",
    ]

    df_view = df[[c for c in colunas if c in df.columns]].copy()

    if "valor_total" in df_view.columns:
        df_view["valor_total"] = df_view["valor_total"].apply(formatar_moeda)

    df_view = df_view.rename(
        columns={
            "numero_os": "OS",
            "data_abertura": "Abertura",
            "cliente_nome": "Cliente",
            "equipamento_categoria": "Categoria",
            "equipamento_marca": "Marca",
            "equipamento_modelo": "Modelo",
            "status": "Status",
            "valor_total": "Valor",
        }
    )

    st.dataframe(df_view.head(20), use_container_width=True, hide_index=True)


# ============================================================
# PÁGINA: NOVA ORDEM DE SERVIÇO
# ============================================================

def pagina_nova_os():
    mostrar_cabecalho()
    aviso_conexao()

    st.subheader("Nova ficha de serviço")

    if "numero_os_atual" not in st.session_state:
        st.session_state.numero_os_atual = gerar_numero_os()

    numero_os = st.session_state.numero_os_atual

    with st.form("form_nova_os", clear_on_submit=False):
        st.markdown("### Identificação da OS")

        c1, c2, c3, c4 = st.columns(4)
        numero_os_input = c1.text_input("Número da OS", value=numero_os, disabled=True)
        data_abertura = c2.date_input("Data de abertura", value=date.today())
        prioridade = c3.selectbox("Prioridade", ["Normal", "Urgente", "Crítica"])
        status = c4.selectbox(
            "Status",
            [
                "Recebido",
                "Em análise",
                "Aguardando orçamento",
                "Aguardando aprovação",
                "Aprovado",
                "Em manutenção",
                "Aguardando peça",
                "Serviço concluído",
                "Sem reparo",
                "Cancelado",
                "Pronto para retirada",
                "Entregue ao cliente",
            ],
        )

        st.markdown("### Dados do cliente")

        c1, c2 = st.columns(2)
        cliente_nome = c1.text_input("Cliente / Empresa *")
        cliente_documento = c2.text_input("CPF ou CNPJ")

        c1, c2, c3 = st.columns(3)
        cliente_responsavel = c1.text_input("Pessoa responsável")
        cliente_telefone = c2.text_input("Telefone / WhatsApp *")
        cliente_email = c3.text_input("E-mail")

        cliente_setor = st.text_input("Unidade, filial ou setor")

        st.markdown("### Dados do equipamento")

        c1, c2, c3 = st.columns(3)
        equipamento_categoria = c1.selectbox(
            "Categoria *",
            [
                "",
                "Celular",
                "Notebook",
                "Computador / Desktop",
                "Tablet",
                "Coletor Zebra",
                "Impressora Zebra",
                "Leitor de código de barras",
                "Outro",
            ],
        )
        equipamento_marca = c2.text_input("Marca *")
        equipamento_modelo = c3.text_input("Modelo *")

        c1, c2, c3 = st.columns(3)
        equipamento_serie = c1.text_input("Número de série")
        equipamento_patrimonio = c2.text_input("Número de patrimônio")
        equipamento_imei = c3.text_input("IMEI ou identificação")

        c1, c2 = st.columns(2)
        acessorios_lista = c1.multiselect(
            "Acessórios recebidos",
            [
                "Carregador",
                "Fonte",
                "Cabo USB",
                "Bateria",
                "Dock",
                "Capa",
                "Bolsa",
                "Cartão de memória",
                "Etiqueta / Ribbon",
                "Outro",
            ],
        )
        senha_equipamento = c2.text_input(
            "Senha do equipamento, quando autorizada",
            type="password",
            help="Evite registrar senhas quando não forem realmente necessárias.",
        )

        estado_entrada_lista = st.multiselect(
            "Estado do equipamento na entrada",
            [
                "Liga normalmente",
                "Não liga",
                "Tela quebrada",
                "Carcaça danificada",
                "Marcas de queda",
                "Sinais de oxidação",
                "Parafusos faltando",
                "Lacre violado",
                "Bateria danificada",
                "Peças faltando",
                "Equipamento bloqueado",
                "Sem senha de acesso",
                "Sem danos visíveis",
                "Outro",
            ],
        )

        observacao_estado = st.text_area(
            "Observações sobre o estado de entrada",
            height=90,
        )

        st.markdown("### Atendimento técnico")

        problema_relatado = st.text_area(
            "Problema relatado pelo cliente *",
            height=110,
        )

        diagnostico = st.text_area(
            "Diagnóstico técnico",
            height=120,
            placeholder="Descreva os testes realizados, o defeito identificado e a causa provável.",
        )

        servicos_lista = st.multiselect(
            "Serviços executados",
            [
                "Diagnóstico",
                "Limpeza interna",
                "Limpeza externa",
                "Formatação",
                "Instalação de sistema",
                "Atualização de sistema",
                "Instalação de drivers",
                "Configuração de rede",
                "Remoção de vírus",
                "Backup",
                "Recuperação de arquivos",
                "Troca de tela",
                "Troca de bateria",
                "Troca de teclado",
                "Troca de HD / SSD",
                "Troca de memória RAM",
                "Troca de conector",
                "Reparo de placa",
                "Calibração de impressora",
                "Troca de rolete",
                "Troca da cabeça de impressão",
                "Atualização de firmware",
                "Configuração de coletor",
                "Instalação de aplicativo",
                "Testes funcionais",
                "Outro",
            ],
        )

        detalhes_servico = st.text_area(
            "Descrição detalhada do serviço realizado",
            height=140,
        )

        testes_lista = st.multiselect(
            "Testes finais realizados",
            [
                "Liga e desliga",
                "Tela",
                "Touch",
                "Teclado",
                "Touchpad",
                "USB",
                "HDMI",
                "Câmera",
                "Áudio",
                "Microfone",
                "Wi-Fi",
                "Bluetooth",
                "Carregamento",
                "Bateria",
                "Leitor de código de barras",
                "Gatilho",
                "Aplicativos",
                "Dock",
                "Impressão",
                "Calibração",
                "Sensor de etiqueta",
                "Cabeça de impressão",
                "Avanço de mídia",
                "Comunicação USB",
                "Comunicação de rede",
                "Qualidade de impressão",
                "Teste geral aprovado",
                "Outro",
            ],
        )

        resultado_testes = st.text_area(
            "Resultado dos testes finais",
            height=90,
        )

        pendencias = st.text_area(
            "Pendências, recomendações ou ressalvas",
            height=100,
        )

        st.markdown("### Valores, pagamento e garantia")

        c1, c2, c3, c4 = st.columns(4)
        valor_pecas = c1.number_input(
            "Peças e materiais (R$)",
            min_value=0.0,
            step=10.0,
            format="%.2f",
        )
        valor_mao_obra = c2.number_input(
            "Mão de obra (R$)",
            min_value=0.0,
            step=10.0,
            format="%.2f",
        )
        desconto = c3.number_input(
            "Desconto (R$)",
            min_value=0.0,
            step=5.0,
            format="%.2f",
        )
        valor_total = max(valor_pecas + valor_mao_obra - desconto, 0)
        c4.metric("Valor total", formatar_moeda(valor_total))

        c1, c2, c3 = st.columns(3)
        forma_pagamento = c1.selectbox(
            "Forma de pagamento",
            [
                "Não informado",
                "PIX",
                "Dinheiro",
                "Cartão de débito",
                "Cartão de crédito",
                "Boleto",
                "Transferência",
                "Faturado",
            ],
        )
        garantia_dias = c2.number_input(
            "Garantia do serviço (dias)",
            min_value=0,
            max_value=365,
            value=90,
            step=1,
        )
        tecnico_responsavel = c3.text_input("Técnico responsável *")

        st.markdown("### Evidências")

        fotos = st.file_uploader(
            "Fotos do equipamento ou serviço",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="Nesta primeira versão, as fotos são selecionadas, mas não são enviadas ao Supabase Storage.",
        )

        confirmar = st.checkbox(
            "Confirmo que as informações registradas estão corretas."
        )

        salvar = st.form_submit_button(
            "💾 Salvar ordem de serviço",
            use_container_width=True,
            type="primary",
        )

    if salvar:
        servico_realizado = ", ".join(servicos_lista)
        if detalhes_servico:
            servico_realizado = (
                f"{servico_realizado}\n\n{detalhes_servico}"
                if servico_realizado
                else detalhes_servico
            )

        testes_finais = ", ".join(testes_lista)
        if resultado_testes:
            testes_finais = (
                f"{testes_finais}\n\nResultado: {resultado_testes}"
                if testes_finais
                else resultado_testes
            )

        estado_entrada = ", ".join(estado_entrada_lista)
        if observacao_estado:
            estado_entrada = (
                f"{estado_entrada}\n\nObservações: {observacao_estado}"
                if estado_entrada
                else observacao_estado
            )

        dados = {
            "numero_os": numero_os_input,
            "data_abertura": data_abertura.isoformat(),
            "prioridade": prioridade,
            "status": status,
            "cliente_nome": limpar_texto(cliente_nome),
            "cliente_documento": limpar_texto(cliente_documento),
            "cliente_responsavel": limpar_texto(cliente_responsavel),
            "cliente_telefone": limpar_texto(cliente_telefone),
            "cliente_email": limpar_texto(cliente_email),
            "cliente_setor": limpar_texto(cliente_setor),
            "equipamento_categoria": limpar_texto(equipamento_categoria),
            "equipamento_marca": limpar_texto(equipamento_marca),
            "equipamento_modelo": limpar_texto(equipamento_modelo),
            "equipamento_serie": limpar_texto(equipamento_serie),
            "equipamento_patrimonio": limpar_texto(equipamento_patrimonio),
            "equipamento_imei": limpar_texto(equipamento_imei),
            "acessorios": ", ".join(acessorios_lista),
            "senha_equipamento": limpar_texto(senha_equipamento),
            "estado_entrada": limpar_texto(estado_entrada),
            "problema_relatado": limpar_texto(problema_relatado),
            "diagnostico": limpar_texto(diagnostico),
            "servico_realizado": limpar_texto(servico_realizado),
            "testes_finais": limpar_texto(testes_finais),
            "pendencias": limpar_texto(pendencias),
            "valor_pecas": float(valor_pecas),
            "valor_mao_obra": float(valor_mao_obra),
            "desconto": float(desconto),
            "valor_total": float(valor_total),
            "forma_pagamento": forma_pagamento,
            "garantia_dias": int(garantia_dias),
            "tecnico_responsavel": limpar_texto(tecnico_responsavel),
            "quantidade_fotos": len(fotos or []),
            "updated_at": datetime.now().isoformat(),
        }

        faltantes = validar_campos_obrigatorios(dados)

        if faltantes:
            st.error(
                "Preencha os campos obrigatórios: " + ", ".join(faltantes) + "."
            )
        elif not confirmar:
            st.error("Marque a confirmação das informações antes de salvar.")
        else:
            try:
                salvo = salvar_os(dados)
                st.session_state["ultima_os_salva"] = salvo
                st.session_state.numero_os_atual = gerar_numero_os()
                st.success(
                    f"Ordem de serviço {salvo.get('numero_os')} salva com sucesso."
                )
                st.rerun()
            except Exception as erro:
                st.error(f"Não foi possível salvar a ordem de serviço: {erro}")

    ultima_os = st.session_state.get("ultima_os_salva")
    if ultima_os:
        st.markdown("---")
        st.success(
            f"Última OS cadastrada: **{ultima_os.get('numero_os', '')}**"
        )
        pdf = gerar_pdf_os(ultima_os)
        st.download_button(
            "📄 Baixar ficha em PDF",
            data=pdf,
            file_name=f"{ultima_os.get('numero_os', 'ordem_servico')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


# ============================================================
# PÁGINA: CONSULTAR ORDENS
# ============================================================

def pagina_consultar_os():
    mostrar_cabecalho()
    aviso_conexao()

    st.subheader("Consultar ordens de serviço")

    registros = listar_os()

    if not registros:
        st.info("Nenhuma ordem de serviço encontrada.")
        return

    df = pd.DataFrame(registros)

    c1, c2, c3 = st.columns([2, 1, 1])
    busca = c1.text_input(
        "Buscar",
        placeholder="Número da OS, cliente, série, patrimônio, marca ou modelo",
    )
    status_filtro = c2.selectbox(
        "Filtrar por status",
        ["Todos"] + sorted(df["status"].dropna().astype(str).unique().tolist()),
    )
    categoria_filtro = c3.selectbox(
        "Filtrar por categoria",
        ["Todas"]
        + sorted(
            df["equipamento_categoria"].dropna().astype(str).unique().tolist()
        ),
    )

    filtrado = df.copy()

    if busca:
        termo = busca.lower().strip()
        campos_busca = [
            "numero_os",
            "cliente_nome",
            "cliente_documento",
            "equipamento_categoria",
            "equipamento_marca",
            "equipamento_modelo",
            "equipamento_serie",
            "equipamento_patrimonio",
            "equipamento_imei",
            "tecnico_responsavel",
        ]

        mascara = pd.Series(False, index=filtrado.index)
        for campo in campos_busca:
            if campo in filtrado.columns:
                mascara = mascara | (
                    filtrado[campo]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(termo, regex=False)
                )
        filtrado = filtrado[mascara]

    if status_filtro != "Todos":
        filtrado = filtrado[filtrado["status"] == status_filtro]

    if categoria_filtro != "Todas":
        filtrado = filtrado[
            filtrado["equipamento_categoria"] == categoria_filtro
        ]

    st.caption(f"{len(filtrado)} registro(s) encontrado(s).")

    if filtrado.empty:
        st.warning("Nenhuma ordem corresponde aos filtros selecionados.")
        return

    opcoes = {
        f"{row['numero_os']} | {row['cliente_nome']} | "
        f"{row['equipamento_categoria']} {row['equipamento_marca']} "
        f"{row['equipamento_modelo']}": int(row["id"])
        for _, row in filtrado.iterrows()
    }

    selecionada_label = st.selectbox(
        "Selecione uma ordem de serviço",
        list(opcoes.keys()),
    )

    os_id = opcoes[selecionada_label]
    dados = filtrado[filtrado["id"] == os_id].iloc[0].to_dict()

    st.markdown(
        f"""
        <div class="aj-card">
            <h3 style="margin-top:0;">{dados.get('numero_os', '')}</h3>
            <span class="status-pill">{dados.get('status', '')}</span>
            <p><b>Cliente:</b> {dados.get('cliente_nome', '')}</p>
            <p><b>Equipamento:</b> {dados.get('equipamento_categoria', '')} —
               {dados.get('equipamento_marca', '')} {dados.get('equipamento_modelo', '')}</p>
            <p><b>Número de série:</b> {dados.get('equipamento_serie', '') or 'Não informado'}</p>
            <p><b>Problema relatado:</b><br>{dados.get('problema_relatado', '')}</p>
            <p><b>Serviço realizado:</b><br>{dados.get('servico_realizado', '') or 'Ainda não informado'}</p>
            <p><b>Valor total:</b> {formatar_moeda(dados.get('valor_total', 0))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    novo_status = c1.selectbox(
        "Alterar status",
        [
            "Recebido",
            "Em análise",
            "Aguardando orçamento",
            "Aguardando aprovação",
            "Aprovado",
            "Em manutenção",
            "Aguardando peça",
            "Serviço concluído",
            "Sem reparo",
            "Cancelado",
            "Pronto para retirada",
            "Entregue ao cliente",
        ],
        index=[
            "Recebido",
            "Em análise",
            "Aguardando orçamento",
            "Aguardando aprovação",
            "Aprovado",
            "Em manutenção",
            "Aguardando peça",
            "Serviço concluído",
            "Sem reparo",
            "Cancelado",
            "Pronto para retirada",
            "Entregue ao cliente",
        ].index(dados.get("status", "Recebido"))
        if dados.get("status", "Recebido")
        in [
            "Recebido",
            "Em análise",
            "Aguardando orçamento",
            "Aguardando aprovação",
            "Aprovado",
            "Em manutenção",
            "Aguardando peça",
            "Serviço concluído",
            "Sem reparo",
            "Cancelado",
            "Pronto para retirada",
            "Entregue ao cliente",
        ]
        else 0,
    )

    if c1.button("Atualizar status", use_container_width=True):
        try:
            atualizar_status_os(os_id, novo_status)
            st.success("Status atualizado.")
            st.rerun()
        except Exception as erro:
            st.error(f"Erro ao atualizar: {erro}")

    pdf = gerar_pdf_os(dados)
    c2.download_button(
        "📄 Baixar PDF da OS",
        data=pdf,
        file_name=f"{dados.get('numero_os', 'ordem_servico')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    with st.expander("Exibir todos os dados"):
        for campo, valor in dados.items():
            if campo not in {"id"}:
                st.write(f"**{campo.replace('_', ' ').title()}:** {valor}")

    with st.expander("Excluir esta ordem de serviço"):
        st.warning(
            "A exclusão é definitiva. Use somente quando o cadastro estiver incorreto."
        )
        confirmar_exclusao = st.text_input(
            "Digite o número da OS para confirmar",
            key=f"confirmar_exclusao_{os_id}",
        )
        if st.button(
            "Excluir definitivamente",
            type="secondary",
            use_container_width=True,
        ):
            if confirmar_exclusao != dados.get("numero_os"):
                st.error("O número informado não corresponde à OS selecionada.")
            else:
                try:
                    excluir_os(os_id)
                    st.success("Ordem de serviço excluída.")
                    st.rerun()
                except Exception as erro:
                    st.error(f"Erro ao excluir: {erro}")


# ============================================================
# PÁGINA: CONFIGURAÇÃO
# ============================================================

def pagina_configuracao():
    mostrar_cabecalho()

    st.subheader("Configuração do Supabase")

    st.markdown(
        """
        Para o app manter os dados no Streamlit Cloud:

        1. Crie um projeto no Supabase.
        2. Abra o **SQL Editor**.
        3. Execute o comando SQL fornecido abaixo.
        4. No Streamlit Cloud, abra **Settings > Secrets**.
        5. Cadastre a URL e a chave do projeto.
        """
    )

    st.code(
        """
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_KEY = "SUA-CHAVE-DO-SUPABASE"
        """.strip(),
        language="toml",
    )

    sql = """
create table if not exists public.ordens_servico (
    id bigint generated by default as identity primary key,
    created_at timestamptz not null default now(),
    updated_at timestamptz,
    numero_os text not null unique,
    data_abertura date not null,
    prioridade text,
    status text not null default 'Recebido',

    cliente_nome text not null,
    cliente_documento text,
    cliente_responsavel text,
    cliente_telefone text not null,
    cliente_email text,
    cliente_setor text,

    equipamento_categoria text not null,
    equipamento_marca text not null,
    equipamento_modelo text not null,
    equipamento_serie text,
    equipamento_patrimonio text,
    equipamento_imei text,
    acessorios text,
    senha_equipamento text,
    estado_entrada text,

    problema_relatado text not null,
    diagnostico text,
    servico_realizado text,
    testes_finais text,
    pendencias text,

    valor_pecas numeric(12,2) not null default 0,
    valor_mao_obra numeric(12,2) not null default 0,
    desconto numeric(12,2) not null default 0,
    valor_total numeric(12,2) not null default 0,
    forma_pagamento text,
    garantia_dias integer not null default 0,
    tecnico_responsavel text not null,
    quantidade_fotos integer not null default 0
);

alter table public.ordens_servico enable row level security;

create policy "permitir leitura ordens"
on public.ordens_servico
for select
to anon
using (true);

create policy "permitir cadastro ordens"
on public.ordens_servico
for insert
to anon
with check (true);

create policy "permitir atualização ordens"
on public.ordens_servico
for update
to anon
using (true)
with check (true);

create policy "permitir exclusão ordens"
on public.ordens_servico
for delete
to anon
using (true);
    """.strip()

    st.code(sql, language="sql")

    if supabase is not None:
        st.success("Supabase conectado.")
    else:
        st.error("Supabase ainda não está conectado.")


# ============================================================
# NAVEGAÇÃO
# ============================================================

with st.sidebar:
    st.markdown(f"## 🛠️ {EMPRESA}")
    st.caption("Sistema de assistência técnica")

    pagina = st.radio(
        "Menu",
        [
            "Dashboard",
            "Nova ordem de serviço",
            "Consultar ordens",
            "Configuração",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.caption("A.J Solutions • Gestão de serviços")


if pagina == "Dashboard":
    pagina_dashboard()
elif pagina == "Nova ordem de serviço":
    pagina_nova_os()
elif pagina == "Consultar ordens":
    pagina_consultar_os()
else:
    pagina_configuracao()
