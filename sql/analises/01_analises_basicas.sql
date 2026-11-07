-- =====================================================================
-- Service Desk Analytics | Etapa 3: análises em SQL
-- Execute UMA consulta por vez (selecione o trecho e aperte F5)
--
-- ATENÇÃO: o SLA e os tempos de resolução são medidos em HORAS ÚTEIS
-- (seg a sex, 8h às 18h) com a função horas_uteis(), criada em
-- sql/03_funcoes.sql. Rode esse arquivo antes destas consultas.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1) Volume de chamados por categoria (e % do total)
--    Conceitos: JOIN, GROUP BY, COUNT, função de janela SUM() OVER ()
-- ---------------------------------------------------------------------
SELECT
    ca.nome                                              AS categoria,
    COUNT(*)                                             AS total_chamados,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)   AS percentual
FROM chamados c
JOIN categorias ca ON ca.id = c.categoria_id
GROUP BY ca.nome
ORDER BY total_chamados DESC;


-- ---------------------------------------------------------------------
-- 2) Tempo médio de resolução por categoria (em horas úteis)
--    Conceitos: AVG, função própria horas_uteis(), WHERE para filtrar só resolvidos
-- ---------------------------------------------------------------------
SELECT
    ca.nome AS categoria,
    COUNT(*) AS chamados_resolvidos,
    ROUND(AVG(horas_uteis(c.aberto_em, c.resolvido_em)), 1)
        AS horas_medias_resolucao
FROM chamados c
JOIN categorias ca ON ca.id = c.categoria_id
WHERE c.resolvido_em IS NOT NULL
GROUP BY ca.nome
ORDER BY horas_medias_resolucao DESC;


-- ---------------------------------------------------------------------
-- 3) Cumprimento de SLA por prioridade (SLA em horas úteis)
--    Conceitos: CASE WHEN, comparação entre tabelas, percentual
-- ---------------------------------------------------------------------
SELECT
    p.nome       AS prioridade,
    p.sla_horas  AS sla_horas,
    COUNT(*)     AS chamados_resolvidos,
    SUM(CASE WHEN horas_uteis(c.aberto_em, c.resolvido_em) <= p.sla_horas
             THEN 1 ELSE 0 END) AS dentro_do_sla,
    ROUND(100.0 * SUM(CASE WHEN horas_uteis(c.aberto_em, c.resolvido_em) <= p.sla_horas
                           THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_sla_cumprido
FROM chamados c
JOIN prioridades p ON p.id = c.prioridade_id
WHERE c.resolvido_em IS NOT NULL
GROUP BY p.nome, p.sla_horas
ORDER BY p.sla_horas;


-- ---------------------------------------------------------------------
-- 4) Desempenho por técnico
--    Conceitos: LEFT JOIN, vários agregados na mesma consulta
-- ---------------------------------------------------------------------
SELECT
    t.nome  AS tecnico,
    t.nivel,
    COUNT(c.id) AS chamados_atendidos,
    ROUND(AVG(horas_uteis(c.aberto_em, c.resolvido_em)), 1)
        AS horas_medias_resolucao,
    ROUND(100.0 * SUM(CASE WHEN horas_uteis(c.aberto_em, c.resolvido_em) <= p.sla_horas
                           THEN 1 ELSE 0 END)
          / NULLIF(COUNT(c.resolvido_em), 0), 1) AS pct_sla_cumprido
FROM tecnicos t
LEFT JOIN chamados c    ON c.tecnico_id = t.id
LEFT JOIN prioridades p ON p.id = c.prioridade_id
GROUP BY t.nome, t.nivel
ORDER BY chamados_atendidos DESC;


-- ---------------------------------------------------------------------
-- 5) Chamados por hora do dia (horários de pico)
--    Conceitos: EXTRACT(HOUR ...), AT TIME ZONE
-- ---------------------------------------------------------------------
SELECT
    EXTRACT(HOUR FROM c.aberto_em AT TIME ZONE 'America/Sao_Paulo')::int AS hora,
    COUNT(*) AS total_chamados
FROM chamados c
GROUP BY hora
ORDER BY hora;


-- ---------------------------------------------------------------------
-- 6) Evolução mensal e variação em relação ao mês anterior
--    Conceitos: DATE_TRUNC, CTE (WITH), função de janela LAG
-- ---------------------------------------------------------------------
WITH por_mes AS (
    SELECT
        DATE_TRUNC('month', c.aberto_em AT TIME ZONE 'America/Sao_Paulo')::date AS mes,
        COUNT(*) AS total_chamados
    FROM chamados c
    GROUP BY 1
)
SELECT
    mes,
    total_chamados,
    LAG(total_chamados) OVER (ORDER BY mes) AS mes_anterior,
    ROUND(100.0 * (total_chamados - LAG(total_chamados) OVER (ORDER BY mes))
          / LAG(total_chamados) OVER (ORDER BY mes), 1) AS variacao_pct
FROM por_mes
ORDER BY mes;


-- ---------------------------------------------------------------------
-- 7) Departamentos que mais abrem chamados
--    Conceitos: JOIN em cadeia (chamados -> usuarios -> departamentos)
-- ---------------------------------------------------------------------
SELECT
    d.nome AS departamento,
    COUNT(*) AS total_chamados,
    COUNT(DISTINCT u.id) AS usuarios_distintos,
    ROUND(1.0 * COUNT(*) / COUNT(DISTINCT u.id), 1) AS chamados_por_usuario
FROM chamados c
JOIN usuarios u      ON u.id = c.usuario_id
JOIN departamentos d ON d.id = u.departamento_id
GROUP BY d.nome
ORDER BY total_chamados DESC;


-- ---------------------------------------------------------------------
-- 8) Chamados em aberto: já estouraram o SLA? (horas úteis desde a abertura)
--    Conceitos: filtro por status, now(), função horas_uteis()
-- ---------------------------------------------------------------------
SELECT
    c.id,
    c.titulo,
    p.nome  AS prioridade,
    s.nome  AS status,
    ROUND(horas_uteis(c.aberto_em, now()), 1) AS horas_em_aberto,
    p.sla_horas,
    CASE WHEN horas_uteis(c.aberto_em, now()) > p.sla_horas
         THEN 'SLA estourado' ELSE 'No prazo' END AS situacao_sla
FROM chamados c
JOIN prioridades p     ON p.id = c.prioridade_id
JOIN status_chamado s  ON s.id = c.status_id
WHERE s.nome NOT IN ('Resolvido', 'Fechado')
ORDER BY horas_em_aberto DESC;


-- ---------------------------------------------------------------------
-- 9) Tempo parado em "Aguardando usuário" (avançada)
--    Conceitos: tabela de histórico, função de janela LEAD
--    Mede quanto tempo cada chamado ficou esperando retorno do usuário.
-- ---------------------------------------------------------------------
WITH eventos AS (
    SELECT
        h.chamado_id,
        s.nome AS status,
        h.alterado_em,
        LEAD(h.alterado_em) OVER (PARTITION BY h.chamado_id ORDER BY h.alterado_em) AS saida_do_status
    FROM historico_chamados h
    JOIN status_chamado s ON s.id = h.status_novo_id
)
SELECT
    COUNT(*) AS vezes_aguardando,
    ROUND(AVG(horas_uteis(alterado_em, saida_do_status)), 1)
        AS horas_medias_espera
FROM eventos
WHERE status = 'Aguardando usuário'
  AND saida_do_status IS NOT NULL;