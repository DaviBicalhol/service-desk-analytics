-- =====================================================================
-- Service Desk Analytics | Etapa 1: criação das tabelas
-- Banco: PostgreSQL
-- Execute conectado ao banco "service_desk"
-- =====================================================================

-- 1) Tabelas de apoio (domínios): valores que se repetem em vários chamados
-- ---------------------------------------------------------------------

CREATE TABLE departamentos (
    id    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome  VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE categorias (
    id    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome  VARCHAR(80) NOT NULL UNIQUE
);

-- Cada prioridade define o prazo (SLA) em horas para resolver o chamado
CREATE TABLE prioridades (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome       VARCHAR(30) NOT NULL UNIQUE,
    sla_horas  INTEGER NOT NULL CHECK (sla_horas > 0)
);

CREATE TABLE status_chamado (
    id    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome  VARCHAR(30) NOT NULL UNIQUE
);

-- ---------------------------------------------------------------------
-- 2) Pessoas
-- ---------------------------------------------------------------------

-- Quem abre os chamados
CREATE TABLE usuarios (
    id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome             VARCHAR(120) NOT NULL,
    email            VARCHAR(150) NOT NULL UNIQUE,
    departamento_id  INTEGER NOT NULL REFERENCES departamentos(id),
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Quem atende os chamados
CREATE TABLE tecnicos (
    id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome   VARCHAR(120) NOT NULL,
    email  VARCHAR(150) NOT NULL UNIQUE,
    nivel  VARCHAR(2) NOT NULL CHECK (nivel IN ('N1', 'N2', 'N3')),
    ativo  BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------
-- 3) Tabela principal: chamados (a "tabela fato" das análises)
-- ---------------------------------------------------------------------

CREATE TABLE chamados (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    titulo         VARCHAR(150) NOT NULL,
    descricao      TEXT,
    usuario_id     INTEGER NOT NULL REFERENCES usuarios(id),
    tecnico_id     INTEGER REFERENCES tecnicos(id),   -- pode ser nulo: ainda sem técnico
    categoria_id   INTEGER NOT NULL REFERENCES categorias(id),
    prioridade_id  INTEGER NOT NULL REFERENCES prioridades(id),
    status_id      INTEGER NOT NULL REFERENCES status_chamado(id),
    aberto_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolvido_em   TIMESTAMPTZ,                       -- nulo enquanto não resolvido
    CONSTRAINT ck_resolucao_apos_abertura
        CHECK (resolvido_em IS NULL OR resolvido_em >= aberto_em)
);

-- ---------------------------------------------------------------------
-- 4) Histórico: cada mudança de status vira uma linha
-- ---------------------------------------------------------------------

CREATE TABLE historico_chamados (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chamado_id         INTEGER NOT NULL REFERENCES chamados(id) ON DELETE CASCADE,
    status_anterior_id INTEGER REFERENCES status_chamado(id),
    status_novo_id     INTEGER NOT NULL REFERENCES status_chamado(id),
    tecnico_id         INTEGER REFERENCES tecnicos(id),
    comentario         TEXT,
    alterado_em        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 5) Índices: aceleram os filtros e junções mais usados nas análises
-- ---------------------------------------------------------------------

CREATE INDEX idx_chamados_usuario     ON chamados(usuario_id);
CREATE INDEX idx_chamados_tecnico     ON chamados(tecnico_id);
CREATE INDEX idx_chamados_categoria   ON chamados(categoria_id);
CREATE INDEX idx_chamados_status      ON chamados(status_id);
CREATE INDEX idx_chamados_aberto_em   ON chamados(aberto_em);
CREATE INDEX idx_historico_chamado    ON historico_chamados(chamado_id);
