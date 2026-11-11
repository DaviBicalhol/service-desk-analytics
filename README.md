🎧 Service Desk Analytics

Projeto de análise de dados de um service desk (suporte técnico N1/N2), do banco de dados ao dashboard: modelagem em PostgreSQL, geração de dados sintéticos com Python, análises em SQL e um dashboard interativo no Power BI com indicadores de volume, tempo de resolução e cumprimento de SLA.

📌 Sobre o projeto

Trabalho com suporte técnico (N1 e N2) e convivo com chamados, prazos e filas de atendimento no dia a dia. Este projeto transforma essa experiência em um case de dados, respondendo perguntas que um gestor de TI faria:

Quais tipos de problema geram mais chamados?
Em que horários o suporte é mais demandado?
Estamos cumprindo os prazos (SLA) de cada prioridade?
Como está o desempenho de cada técnico e de cada nível de atendimento?
Quantos chamados continuam em aberto?

⚠️ Os dados são 100% fictícios, gerados por código. Nenhuma informação de empresa ou pessoa real foi usada.

🛠️ Tecnologias
Camada	Ferramentas
Banco de dados	PostgreSQL
Geração de dados	Python (Faker, psycopg2, python-dotenv)
Análise	SQL (JOIN, CTE, funções de janela, função própria)
Visualização	Power BI (DAX, tema personalizado)
Versionamento	Git e GitHub
🗄️ Modelo de dados

O banco tem 8 tabelas normalizadas, separando os dados que se repetem (categorias, prioridades, status, departamentos) dos dados principais (chamados e histórico).

Diagrama do banco

Tabela	Função
chamados	Tabela principal: título, usuário, técnico, categoria, prioridade, status e datas
historico_chamados	Cada mudança de status de um chamado (Aberto → Em atendimento → Resolvido → Fechado)
usuarios e departamentos	Quem abre os chamados e de qual setor
tecnicos	Quem atende, com o nível (N1, N2 ou N3)
categorias, prioridades, status_chamado	Tabelas de apoio; a prioridade guarda o prazo de SLA em horas

Decisões de modelagem:

Chaves estrangeiras garantem a integridade dos dados (não existe chamado de um usuário inexistente).
CHECK impede, por exemplo, um chamado resolvido antes de ser aberto.
Índices nas colunas mais usadas em filtros e junções.
O prazo de SLA fica na tabela de prioridades, em um único lugar.
⏱️ SLA em horas úteis

O SLA é medido em horas úteis (segunda a sexta, das 8h às 18h), como em um service desk real. Para isso, criei a função SQL horas_uteis(inicio, fim), que conta apenas o tempo dentro do expediente.

Prioridade	SLA (horas úteis)
Crítica	4
Alta	8
Média	24
Baixa	72

Exemplo: um chamado aberto na sexta às 16h e resolvido na segunda às 10h levou 4 horas úteis.

A função não considera feriados.

📊 Dashboard

O dashboard em Power BI foi construído sobre a view vw_chamados_analise, que junta as tabelas e já traz o tempo de resolução e o indicador de SLA calculados.

Indicadores principais:

Indicador	Valor
Total de chamados	5.000
Tempo médio de resolução	19,15 horas úteis
SLA cumprido	85,2% (meta de 90%)
Chamados resolvidos	4.962
Chamados em aberto	38

Visuais: chamados por prioridade, por categoria, por departamento, por mês, por hora de abertura e desempenho por técnico, com filtros por prioridade e departamento.

Medidas DAX:

Total de Chamados = COUNTROWS(vw_chamados_analise)
Chamados em Aberto = SUM(vw_chamados_analise[em_aberto])
Chamados Resolvidos = CALCULATE(COUNTROWS(vw_chamados_analise), vw_chamados_analise[em_aberto] = 0)
Tempo Médio de Resolução (h úteis) = AVERAGE(vw_chamados_analise[horas_uteis_resolucao])
% SLA Cumprido = AVERAGE(vw_chamados_analise[dentro_do_sla])
Meta SLA = 0.9
🔎 Principais insights

Os dados são simulados, mas a análise segue o raciocínio de um caso real:

Senha e acesso lidera os chamados, com cerca de 27% do total, seguida de impressora, hardware e rede. São categorias ligadas a atendimento simples, que poderiam ser reduzidas com autoatendimento (por exemplo, redefinição de senha).
O volume se concentra em dois picos: entre 9h e 10h (726 e 703 chamados abertos) e no começo da tarde, às 14h e 15h. Há queda no horário de almoço, às 12h (334). É a informação que embasaria a escala da equipe.
O SLA global (85,2%) fica abaixo da meta de 90%. Sem olhar o detalhe por prioridade e por técnico, esse número esconde onde está o problema.
O SLA varia entre os técnicos, de cerca de 78% a 90%. Os técnicos N2 aparecem com percentuais mais baixos, o que faz sentido na simulação: eles recebem mais chamados críticos e de alta prioridade, que têm prazos mais curtos.
O volume mensal é estável, em torno de 400 chamados por mês, sem sazonalidade forte.
Apenas 38 chamados (0,8%) estão em aberto, o que indica uma fila sob controle.

Esses padrões refletem as regras usadas para simular os dados. Em dados reais, o objetivo seria investigar as causas por trás de cada um deles.
