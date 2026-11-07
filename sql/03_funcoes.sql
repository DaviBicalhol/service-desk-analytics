-- =====================================================================
-- Service Desk Analytics | Função de horas úteis
-- Execute no banco "service_desk" (uma vez). Pode rodar de novo sem erro.
--
-- horas_uteis(inicio, fim): quantas horas entre duas datas caem dentro do
-- expediente (segunda a sexta, 8h às 18h, horário de Brasília).
-- Ex.: sexta 16h até segunda 10h = 2h (sexta) + 2h (segunda) = 4 horas úteis.
-- =====================================================================

CREATE OR REPLACE FUNCTION horas_uteis(
    p_inicio    TIMESTAMPTZ,
    p_fim       TIMESTAMPTZ,
    p_hora_ini  INTEGER DEFAULT 8,
    p_hora_fim  INTEGER DEFAULT 18
) RETURNS NUMERIC
LANGUAGE sql
STABLE
AS $$
    WITH limites AS (
        -- converte para o horário local (sem fuso) para trabalhar com "dias"
        SELECT p_inicio AT TIME ZONE 'America/Sao_Paulo' AS ini,
               p_fim    AT TIME ZONE 'America/Sao_Paulo' AS fim
    ),
    dias AS (
        -- uma linha por dia do intervalo, só dias úteis (ISODOW: 1=seg ... 7=dom)
        SELECT d::timestamp AS dia, l.ini, l.fim
        FROM limites l,
             generate_series(date_trunc('day', l.ini),
                             date_trunc('day', l.fim),
                             INTERVAL '1 day') AS d
        WHERE EXTRACT(ISODOW FROM d) < 6
    )
    SELECT CASE
        WHEN p_inicio IS NULL OR p_fim IS NULL THEN NULL
        ELSE ROUND(COALESCE(SUM(GREATEST(0,
                 EXTRACT(EPOCH FROM (
                     LEAST(fim, dia + make_interval(hours => p_hora_fim))
                   - GREATEST(ini, dia + make_interval(hours => p_hora_ini))
                 )) / 3600
             )), 0)::numeric, 2)
    END
    FROM dias;
$$;

-- Testes rápidos (resultados esperados nos comentários):
-- SELECT horas_uteis('2026-11-06 16:00-03', '2026-11-09 10:00-03');  -- 4.00 (sexta 16h até segunda 10h)
-- SELECT horas_uteis('2026-11-06 09:00-03', '2026-11-06 12:30-03');  -- 3.50 (mesmo dia)
-- SELECT horas_uteis('2026-11-07 10:00-03', '2026-11-08 15:00-03');  -- 0.00 (fim de semana)
