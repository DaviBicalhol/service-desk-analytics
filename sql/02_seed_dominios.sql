-- =====================================================================
-- Service Desk Analytics | Etapa 1: dados fixos (tabelas de apoio)
-- =====================================================================

INSERT INTO status_chamado (nome) VALUES
    ('Aberto'),
    ('Em atendimento'),
    ('Aguardando usuário'),
    ('Resolvido'),
    ('Fechado');

INSERT INTO prioridades (nome, sla_horas) VALUES
    ('Crítica', 4),
    ('Alta',    8),
    ('Média',   24),
    ('Baixa',   72);

INSERT INTO categorias (nome) VALUES
    ('Senha e acesso'),
    ('Hardware'),
    ('Impressora'),
    ('Rede e internet'),
    ('Software e sistemas'),
    ('E-mail'),
    ('Solicitação de equipamento'),
    ('Outros');

INSERT INTO departamentos (nome) VALUES
    ('Administrativo'),
    ('Financeiro'),
    ('Recursos Humanos'),
    ('Comercial'),
    ('Operações'),
    ('Atendimento'),
    ('Diretoria');
