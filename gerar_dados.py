"""
Service Desk Analytics | Etapa 2: geração de dados sintéticos

Gera usuários, técnicos, chamados e histórico de status e grava no PostgreSQL.
Os dados são FICTÍCIOS (biblioteca Faker) e seguem regras que imitam um
service desk real: prioridades, SLAs, horário comercial e descumprimento
ocasional de prazo.

Pode ser executado várias vezes: a cada execução, as tabelas de pessoas e
chamados são limpas e recriadas.
"""

import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from faker import Faker

# ---------------------------------------------------------------------
# 1) Configurações (altere aqui para mudar o tamanho da base)
# ---------------------------------------------------------------------
QTD_USUARIOS = 120
QTD_CHAMADOS = 5000
DIAS_DE_HISTORICO = 365
SEMENTE = 42  # mesma semente = mesmos dados; facilita reproduzir o projeto

FUSO = ZoneInfo("America/Sao_Paulo")
AGORA = datetime.now(FUSO)

random.seed(SEMENTE)
Faker.seed(SEMENTE)
fake = Faker("pt_BR")

# Nomes de técnicos (fictícios) e seus níveis
TECNICOS = [
    ("Carlos Mendes", "N1"),
    ("Juliana Rocha", "N1"),
    ("Rafael Duarte", "N1"),
    ("Patrícia Lima", "N1"),
    ("Bruno Teixeira", "N1"),
    ("Fernanda Alves", "N2"),
    ("Marcelo Pires", "N2"),
    ("Aline Moraes", "N2"),
]

# Modelos de título por categoria (cada chamado sorteia um deles)
TITULOS = {
    "Senha e acesso": [
        "Esqueci minha senha de rede",
        "Conta bloqueada após tentativas de login",
        "Solicitação de acesso a pasta compartilhada",
        "Redefinição de senha do sistema interno",
    ],
    "Hardware": [
        "Computador não liga",
        "Monitor sem imagem",
        "Teclado com teclas falhando",
        "Computador muito lento e travando",
    ],
    "Impressora": [
        "Impressora não imprime",
        "Papel atolado na impressora",
        "Toner acabando, impressão com falhas",
        "Impressora fora da rede",
    ],
    "Rede e internet": [
        "Sem acesso à internet",
        "Wi-Fi instável na sala",
        "Não consigo acessar a rede da empresa",
        "Lentidão na conexão",
    ],
    "Software e sistemas": [
        "Erro ao abrir o sistema de gestão",
        "Instalação de software solicitada",
        "Programa fecha sozinho",
        "Atualização do sistema com erro",
    ],
    "E-mail": [
        "Caixa de e-mail cheia",
        "Não recebo e-mails externos",
        "Erro ao enviar e-mail com anexo",
        "Configurar e-mail no celular",
    ],
    "Solicitação de equipamento": [
        "Solicitação de novo mouse e teclado",
        "Pedido de notebook para novo colaborador",
        "Solicitação de segundo monitor",
        "Pedido de headset",
    ],
    "Outros": [
        "Dúvida sobre uso de ferramenta",
        "Solicitação de suporte em reunião",
        "Problema não identificado",
    ],
}

# Frequência relativa de cada categoria (
PESO_CATEGORIAS = {
    "Senha e acesso": 28,
    "Hardware": 14,
    "Impressora": 15,
    "Rede e internet": 13,
    "Software e sistemas": 14,
    "E-mail": 8,
    "Solicitação de equipamento": 5,
    "Outros": 3,
}

# Frequência relativa de cada prioridade 
PESO_PRIORIDADES = {"Crítica": 4, "Alta": 16, "Média": 55, "Baixa": 25}

# Categorias mais demoradas ou mais rápidas de resolver
FATOR_TEMPO = {
    "Senha e acesso": 0.4,
    "Hardware": 1.4,
    "Impressora": 0.9,
    "Rede e internet": 1.1,
    "Software e sistemas": 1.2,
    "E-mail": 0.8,
    "Solicitação de equipamento": 1.6,
    "Outros": 1.0,
}


# ---------------------------------------------------------------------
# 2) Funções auxiliares
# ---------------------------------------------------------------------
def conectar():
    """Abre a conexão com o PostgreSQL usando as variáveis do arquivo .env."""
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def carregar_dominios(cursor):
    """Lê as tabelas de apoio e devolve dicionários {nome: id}."""
    cursor.execute("SELECT nome, id FROM categorias;")
    categorias = dict(cursor.fetchall())

    cursor.execute("SELECT nome, id, sla_horas FROM prioridades;")
    prioridades = {nome: (id_, sla) for nome, id_, sla in cursor.fetchall()}

    cursor.execute("SELECT nome, id FROM status_chamado;")
    status = dict(cursor.fetchall())

    cursor.execute("SELECT id FROM departamentos;")
    departamentos = [linha[0] for linha in cursor.fetchall()]

    return categorias, prioridades, status, departamentos


def limpar_tabelas(cursor):
    """Apaga os dados gerados antes e reinicia os ids (para poder rodar de novo)."""
    cursor.execute(
        "TRUNCATE historico_chamados, chamados, usuarios, tecnicos "
        "RESTART IDENTITY CASCADE;"
    )


def sortear_abertura():
    """Sorteia uma data de abertura, com mais chance em dias úteis e horário comercial."""
    while True:
        dia = AGORA - timedelta(days=random.uniform(0, DIAS_DE_HISTORICO))
        eh_fim_de_semana = dia.weekday() >= 5
        if eh_fim_de_semana and random.random() > 0.08:
            continue
        hora = random.choices(
            population=list(range(8, 18)),
            weights=[8, 14, 14, 11, 7, 8, 12, 12, 9, 5],  # picos de manhã e pós-almoço
        )[0]
        abertura = dia.replace(
            hour=hora,
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
            microsecond=0,
        )
        if abertura < AGORA:
            return abertura


def sortear_horas_de_resolucao(sla_horas, categoria):
    """
    Define quantas horas o chamado levou para ser resolvido.
    O tempo gira em torno de metade do SLA, ajustado pela categoria.
    A distribuição lognormal gera um "rabo" de casos demorados, e cerca de
    15% a 25% dos chamados acabam estourando o prazo, como na vida real.
    """
    base = sla_horas * random.lognormvariate(-0.6, 0.6)
    return max(0.1, base * FATOR_TEMPO[categoria])


# ---------------------------------------------------------------------
# 3) Geração das pessoas
# ---------------------------------------------------------------------
def gerar_usuarios(cursor, departamentos):
    linhas = []
    for i in range(1, QTD_USUARIOS + 1):
        nome = fake.name()
        # O número no e-mail garante que nunca haja dois e-mails iguais
        email = f"usuario{i:03d}@empresa-ficticia.com.br"
        criado_em = AGORA - timedelta(days=random.randint(DIAS_DE_HISTORICO, DIAS_DE_HISTORICO + 400))
        linhas.append((nome, email, random.choice(departamentos), criado_em))

    execute_values(
        cursor,
        "INSERT INTO usuarios (nome, email, departamento_id, criado_em) VALUES %s "
        "RETURNING id;",
        linhas,
        fetch=True,
    )
    cursor.execute("SELECT id FROM usuarios ORDER BY id;")
    return [linha[0] for linha in cursor.fetchall()]


def gerar_tecnicos(cursor):
    linhas = [
        (nome, f"tecnico{i}@empresa-ficticia.com.br", nivel)
        for i, (nome, nivel) in enumerate(TECNICOS, start=1)
    ]
    execute_values(
        cursor,
        "INSERT INTO tecnicos (nome, email, nivel) VALUES %s;",
        linhas,
    )
    cursor.execute("SELECT id, nivel FROM tecnicos ORDER BY id;")
    return cursor.fetchall()  # lista de (id, nivel)


# ---------------------------------------------------------------------
# 4) Geração dos chamados e do histórico
# ---------------------------------------------------------------------
def montar_chamados(usuarios_ids, tecnicos, categorias, prioridades, status):
    """
    Monta em memória os chamados e o histórico de cada um.
    Devolve duas listas: chamados e historicos (ligados pela posição do chamado).
    """
    tecnicos_n1 = [t_id for t_id, nivel in tecnicos if nivel == "N1"]
    tecnicos_n2 = [t_id for t_id, nivel in tecnicos if nivel == "N2"]

    nomes_cat = list(PESO_CATEGORIAS)
    pesos_cat = list(PESO_CATEGORIAS.values())
    nomes_pri = list(PESO_PRIORIDADES)
    pesos_pri = list(PESO_PRIORIDADES.values())

    chamados = []
    historicos = []  # cada item: (posição_do_chamado, status_ant, status_novo, tecnico, comentario, data)

    for posicao in range(QTD_CHAMADOS):
        categoria = random.choices(nomes_cat, weights=pesos_cat)[0]
        prioridade = random.choices(nomes_pri, weights=pesos_pri)[0]
        prioridade_id, sla_horas = prioridades[prioridade]

        # Chamados críticos e de hardware/rede vão mais ao N2
        vai_para_n2 = prioridade in ("Crítica", "Alta") or categoria in ("Rede e internet", "Hardware")
        if vai_para_n2 and random.random() < 0.7:
            tecnico_id = random.choice(tecnicos_n2)
        else:
            tecnico_id = random.choice(tecnicos_n1)

        aberto_em = sortear_abertura()
        resolvido_potencial = aberto_em + timedelta(
            hours=sortear_horas_de_resolucao(sla_horas, categoria)
        )

        titulo = random.choice(TITULOS[categoria])
        descricao = f"{titulo}. {fake.sentence(nb_words=12)}"

        historico = []  # (status_ant, status_novo, tecnico, comentario, data)
        inicio_atendimento = aberto_em + timedelta(minutes=random.randint(2, 90))

        if resolvido_potencial <= AGORA:
            # Chamado já resolvido
            resolvido_em = resolvido_potencial
            inicio_atendimento = min(inicio_atendimento, resolvido_em - timedelta(minutes=1))
            if inicio_atendimento < aberto_em:
                inicio_atendimento = aberto_em

            historico.append((None, "Aberto", None, "Chamado aberto", aberto_em))
            historico.append(("Aberto", "Em atendimento", tecnico_id, "Atendimento iniciado", inicio_atendimento))

            # 25% dos chamados ficam um tempo aguardando retorno do usuário
            if (resolvido_em - inicio_atendimento) > timedelta(hours=1) and random.random() < 0.25:
                espera_ini = inicio_atendimento + (resolvido_em - inicio_atendimento) * 0.3
                espera_fim = inicio_atendimento + (resolvido_em - inicio_atendimento) * 0.6
                historico.append(("Em atendimento", "Aguardando usuário", tecnico_id, "Aguardando retorno do usuário", espera_ini))
                historico.append(("Aguardando usuário", "Em atendimento", tecnico_id, "Usuário respondeu", espera_fim))

            ultimo = "Em atendimento"
            historico.append((ultimo, "Resolvido", tecnico_id, "Problema resolvido", resolvido_em))
            status_final = "Resolvido"

            # 80% dos resolvidos já foram fechados (se o fechamento já aconteceu)
            fechamento = resolvido_em + timedelta(hours=random.randint(2, 48))
            if random.random() < 0.8 and fechamento <= AGORA:
                historico.append(("Resolvido", "Fechado", tecnico_id, "Chamado encerrado", fechamento))
                status_final = "Fechado"
        else:
            # Chamado ainda em andamento
            resolvido_em = None
            historico.append((None, "Aberto", None, "Chamado aberto", aberto_em))
            sorteio = random.random()
            if aberto_em + timedelta(minutes=30) > AGORA or sorteio < 0.15:
                status_final = "Aberto"
                tecnico_id = None
            else:
                historico.append(("Aberto", "Em atendimento", tecnico_id, "Atendimento iniciado", min(inicio_atendimento, AGORA)))
                if sorteio < 0.40:
                    historico.append(("Em atendimento", "Aguardando usuário", tecnico_id, "Aguardando retorno do usuário", min(inicio_atendimento + timedelta(hours=2), AGORA)))
                    status_final = "Aguardando usuário"
                else:
                    status_final = "Em atendimento"

        chamados.append((
            titulo,
            descricao,
            random.choice(usuarios_ids),
            tecnico_id,
            categorias[categoria],
            prioridade_id,
            status[status_final],
            aberto_em,
            resolvido_em,
        ))

        for ant, novo, tec, comentario, data in historico:
            historicos.append((posicao, ant, novo, tec, comentario, data))

    return chamados, historicos


def inserir_chamados(cursor, chamados, historicos, status):
    """Insere os chamados, recupera os ids gerados e insere o histórico."""
    ids = execute_values(
        cursor,
        "INSERT INTO chamados (titulo, descricao, usuario_id, tecnico_id, categoria_id, "
        "prioridade_id, status_id, aberto_em, resolvido_em) VALUES %s RETURNING id;",
        chamados,
        page_size=1000,
        fetch=True,
    )
    ids_chamados = [linha[0] for linha in ids]

    linhas_historico = [
        (
            ids_chamados[posicao],
            status[ant] if ant else None,
            status[novo],
            tec,
            comentario,
            data,
        )
        for posicao, ant, novo, tec, comentario, data in historicos
    ]
    execute_values(
        cursor,
        "INSERT INTO historico_chamados (chamado_id, status_anterior_id, status_novo_id, "
        "tecnico_id, comentario, alterado_em) VALUES %s;",
        linhas_historico,
        page_size=1000,
    )
    return len(ids_chamados), len(linhas_historico)


# ---------------------------------------------------------------------
# 5) Execução principal
# ---------------------------------------------------------------------
def main():
    conexao = conectar()
    try:
        with conexao.cursor() as cursor:
            categorias, prioridades, status, departamentos = carregar_dominios(cursor)

            if not (categorias and prioridades and status and departamentos):
                raise RuntimeError(
                    "As tabelas de apoio estão vazias. Rode o 02_seed_dominios.sql primeiro."
                )

            limpar_tabelas(cursor)
            usuarios_ids = gerar_usuarios(cursor, departamentos)
            tecnicos = gerar_tecnicos(cursor)

            chamados, historicos = montar_chamados(
                usuarios_ids, tecnicos, categorias, prioridades, status
            )
            qtd_chamados, qtd_historico = inserir_chamados(
                cursor, chamados, historicos, status
            )

        conexao.commit()  # só grava de verdade se tudo deu certo
        print("Dados gerados com sucesso!")
        print(f"  Usuários:  {len(usuarios_ids)}")
        print(f"  Técnicos:  {len(tecnicos)}")
        print(f"  Chamados:  {qtd_chamados}")
        print(f"  Histórico: {qtd_historico} registros")
    except Exception:
        conexao.rollback()  # desfaz tudo se algo falhar no meio
        raise
    finally:
        conexao.close()


if __name__ == "__main__":
    main()