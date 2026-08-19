


SCRIPTS_SQL = {


"top_5_faltas_por_centro_custo": """


-- =========================================================================
-- 1. PARAMETRIZAÇÃO DO PERÍODO DE ANÁLISE
-- =========================================================================
DECLARE @DataInicio DATE = ?;
DECLARE @DataFim    DATE = ?;

-- =========================================================================
-- 2. CADASTRO BASE DE FUNCIONÁRIOS
-- =========================================================================
WITH FuncionariosValidos AS (
    SELECT
        pfunc.CODCOLIGADA,
        pfunc.CHAPA,
        pfunc.NOME,
        pfunc.CODSECAO,
        psecao.NROCENCUSTOCONT AS CENTRO_CUSTO,
        
        -- Usado para remover o caractere "¶" chamado pilcrow que possui o Line feed e o Carriage Return basicamente ele pula a linha e volta pro inicio,
    	-- identificado no SQL Server com o código CHAR(10) e CHAR(13), porque estava quebrando o arquivo em csv na hora da formatação
    	REPLACE(REPLACE(psecao.DESCRICAO, CHAR(13), ''), CHAR(10), '') AS NOME_CENTRO_CUSTO,

        -- Regra de negócio aplicada definindo a regional e o seu conjunto de centro de custos em cada uma
        CASE 
            WHEN psecao.NROCENCUSTOCONT IN ('8101','8104', '8105', '8110', '8113', '8115', '8116', '8117', '8118', '8119','8120','8121', '8122', '8124', '8126')
                THEN 'ADMINISTRAÇÃO'
            WHEN psecao.NROCENCUSTOCONT IN ('8369', '8111')
                THEN 'TELECOM'    
            WHEN psecao.NROCENCUSTOCONT IN ('8295', '8296', '8422', '8272', '8274', '8293', '8294', '8401', '8403', '8411', '8413', '8427', '8431', '8432', '8433', '8290' ,'8419', '8425', '8426')
                THEN 'REGIONAL_SESU'    
            WHEN psecao.NROCENCUSTOCONT IN ('8279', '8410', '8429', '8408', '8423', '8270', '8284', '8298', '8409', '8421', '8430', '8519')
                THEN 'REGIONAL_CONE'
            ELSE 'NÃO CLASSIFICADO'
        END AS REGIONAL,
        
		-- Pegando a jornada de horas mensais de cada funcionário(Valor em minutos) e dividindo por 60 para obter o valor em horas no mês
        CAST((pfunc.JORNADAMENSAL / 60.0) AS FLOAT) AS JORNADAMENSAL,
        CAST(pfunc.SALARIO AS FLOAT) AS SALARIO,
        
        -- Dividindo o salário do funcionário pela jornada mensal em hora para obter o valor da hora de cada funcionário para futuramente
        -- multiplicar as horas de falta de cada funcionário e fazer uma estimativa de custo
        CASE 
            WHEN ISNULL(pfunc.JORNADAMENSAL, 0) = 0 THEN 0
            ELSE CAST(pfunc.SALARIO AS FLOAT) / (pfunc.JORNADAMENSAL / 60.0)
        END AS VALOR_HORA,
        
		-- Pegando a data de admissão e demissão para saber os funcionários ativos em cada mês
        CAST(pfunc.DATAADMISSAO AS DATE) AS DATAADMISSAO,
        CAST(pfunc.DATADEMISSAO AS DATE) AS DATADEMISSAO
    FROM 
        PFUNC pfunc
        
    -- Fazendo uma junção com PSECAO para pegar o código do centro de custo
    INNER JOIN PSECAO psecao ON psecao.CODCOLIGADA = pfunc.CODCOLIGADA AND psecao.CODIGO = pfunc.CODSECAO
    WHERE
    	-- Código da empresa Matriz
        pfunc.CODCOLIGADA = 3
        -- Funcionários com a letra "T" na Chapa significa que foram Transferidos ou Tomadores, ou seja, possui dois registros na tabela
    	-- sendo assim, ignorando o registro que possui o "T" na Chapa para não gerar duplicidade 
        AND pfunc.CHAPA NOT LIKE '%T%'
        -- os funcionários que são da categoria autônomos e intermitentes
        AND pfunc.CODCATEGORIAESOCIAL NOT IN ('111', '701')
        -- Retira da contagem a filial da INVERNADA SP
        AND pfunc.CODFILIAL <> 10
),

-- =========================================================================
-- 3. MOVIMENTAÇÃO DE PONTO E MESES EXISTENTES
-- =========================================================================
MovimentoPonto AS (
    SELECT 
        ponto.CODCOLIGADA,
        ponto.CHAPA,
        FORMAT(ponto.DATA, 'yyyy-MM') AS MES_ANO,
        EOMONTH(ponto.DATA) AS ULTIMO_DIA_MES,
        DATEFROMPARTS(YEAR(ponto.DATA), MONTH(ponto.DATA), 1) AS PRIMEIRO_DIA_MES,
        SUM(CAST(ISNULL(ponto.FALTA, 0) AS FLOAT) / 60.0) AS HORAS_FALTA,
        SUM(CAST(ISNULL(ponto.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO
        
    FROM 
        AAFHTFUN ponto
    WHERE
        ponto.CODCOLIGADA = 3
        AND ponto.DATA BETWEEN @DataInicio AND @DataFim
        
    -- Fazendo o agrupamento por essas campos para pegar o movimento do ponto de cada fucnionário por mês
    GROUP BY 
        ponto.CODCOLIGADA,
        ponto.CHAPA,
        FORMAT(ponto.DATA, 'yyyy-MM'),
        EOMONTH(ponto.DATA), -- Traz a data final do mês
        DATEFROMPARTS(YEAR(ponto.DATA), MONTH(ponto.DATA), 1) -- Traz a primeira data do mês
),

-- Tabela para trazer todos os mês do ano registrados no ponto para consultar os funcionários ativos mês a mês
MesesExistentes AS (
    SELECT DISTINCT 
        MES_ANO, 
        PRIMEIRO_DIA_MES, 
        ULTIMO_DIA_MES 
    FROM MovimentoPonto
),

-- =========================================================================
-- 4. ABONOS ESPECÍFICOS DE FALTAS (AABONOFUNCIONARIO)
-- =========================================================================
AbonosFiltrados AS (
    SELECT 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM') AS MES_ANO,
        SUM(
            CASE 
                -- Se tiver Intervalo de Inicio e Fim preenchidos
                WHEN abono.DATAHORAINICIO IS NOT NULL AND abono.DATAHORAFIM IS NOT NULL THEN
                    CAST(DATEDIFF(MINUTE, abono.DATAHORAINICIO, abono.DATAHORAFIM) AS FLOAT) / 60.0
                
                -- Se não tiver datas, utiliza a coluna NUMHORAS (convertendo minutos para horas)
                ELSE
                    CAST(ISNULL(abono.NUMHORAS, 0) AS FLOAT) / 60.0
            END
        ) AS HORAS_ABONADAS
    FROM 
        AABONOFUNCIONARIO abono
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = abono.CODCOLIGADA
        AND fv.CHAPA = abono.CHAPA
    WHERE 
        abono.CODCOLIGADA = 3
        -- Registro Ativo
        AND abono.SITUACAO = '1'
        -- Código de abono referente aos eventos de faltas
        AND abono.CODABONO IN ('008', '017', '020', '022', '028', '030', '031', '033', '035', '22', '407', '415', '432', '436')
        AND abono.DATAREFERENCIA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM')
),

-- =========================================================================
-- 7. BANCO DE HORAS (ASALDOBANCOHOR) - CÁLCULO DE SALDO MENSAL
-- =========================================================================
MovimentoBancoHoras AS (
-- Não precisa usar o SUM nos campos por que, o banco de horas trás os valores por mês e não por dia como o Movimento do ponto (AAFHTFUN)

    SELECT 
        asal.CODCOLIGADA,
        asal.CHAPA,
        FORMAT(asal.INICIOPER, 'yyyy-MM') AS MES_ANO,
        SUM(CAST(ISNULL(asal.FALTAANT, 0) AS FLOAT) / 60.0) AS HORAS_FALTA_ACUMULADO_ANTERIOR,
        SUM(CAST(ISNULL(asal.FALTAATU, 0) AS FLOAT) / 60.0) AS HORAS_FALTA_BANCO_MES,
        
        
        -- Sumarizando e calculando o saldo do banco de horas por funcionário no mês, fazendo a diferença
        -- entre as horas extras acumuladas + horas extras atuais e atrasos acumulados + atrasos atuais + faltas acumuladas + faltas atuais 
        SUM(
            CAST(
                (ISNULL(asal.EXTRAANT, 0) + ISNULL(asal.EXTRAATU, 0)) - 
                (ISNULL(asal.ATRASOANT, 0) + ISNULL(asal.FALTAANT, 0) + ISNULL(asal.ATRASOATU, 0) + ISNULL(asal.FALTAATU, 0))
            AS FLOAT) / 60.0
        ) AS SALDO_HORAS_BANCO
        
    FROM 
        ASALDOBANCOHOR asal
    WHERE 
        asal.CODCOLIGADA = 3
        
        -- Pegando o movimento do banco de horas de acordo com a data de inicio e data final dos parâmetros
        AND asal.INICIOPER >= @DataInicio 
        AND asal.FIMPER <= @DataFim
    GROUP BY 
        asal.CODCOLIGADA,
        asal.CHAPA,
        FORMAT(asal.INICIOPER, 'yyyy-MM')
),

-- =========================================================================
-- 8. FICHA FINANCEIRA - DESCONTOS DE FALTAS EM FOLHA (EVENTO 0182 e 8180)
-- =========================================================================
MovimentoFichaFinanceira AS (
    SELECT 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        
        -- Concatenando o ano com o mês para manter o padrão 'yyyy-MM'
        CONCAT(pffin.ANOCOMP, '-', RIGHT(CONCAT('0', pffin.MESCOMP), 2)) AS MES_ANO,
        
        -- Sumarizando a quantidade de referência do código de evento que se refere a quantidade de horas 
        SUM(CAST(ISNULL(pffin.REF, 0) AS FLOAT)) AS HORAS_DESCONTADAS_FOLHA,
        
        -- Sumarizando o valor de referência do código de evento que se refere ao valor em reais pago em relação a quantidade de horas do 'REF'
        SUM(CAST(ISNULL(pffin.VALOR, 0) AS FLOAT)) AS VALOR_DESCONTADO_FOLHA
        
    FROM 
        PFFINANC pffin
    WHERE 
        pffin.CODCOLIGADA = 3
        
        -- Código na folha de falta (0182), falta reduzida(Quando trabalha noturno)(8180)
        AND pffin.CODEVENTO IN ('0182', '8180')
        
        -- Formatando a data para trazer o primeiro dia do ano e mês da ficha financeira para manter o padrão no filtro
        AND DATEFROMPARTS(pffin.ANOCOMP, pffin.MESCOMP, 1) BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        pffin.ANOCOMP,
        pffin.MESCOMP
),

-- =========================================================================
-- 9. DETALHAMENTO CONSOLIDADO POR FUNCIONÁRIO E MÊS
-- =========================================================================
ConsolidadoFuncionario AS (
    SELECT 
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        fv.CHAPA,
        fv.NOME,
        mp.MES_ANO,
        
        -- Ponto Eletrônico
        ISNULL(mp.HORAS_FALTA, 0) AS HORAS_FALTA,
        --ISNULL(mp.HORAS_ABONO, 0) AS HORAS_ABONO,
        ISNULL(mp.HORAS_ATRASO, 0) AS HORAS_ATRASO,
        
        -- Abonos Específicos (AABONOFUNCIONARIO)
        ISNULL(ab.HORAS_ABONADAS, 0) AS HORAS_ABONADAS,
        
        -- Banco de Horas
        ISNULL(bh.HORAS_FALTA_BANCO_MES, 0) AS HORAS_FALTA_BANCO,
        ISNULL(bh.SALDO_HORAS_BANCO, 0) AS SALDO_HORAS_BANCO,
        
        -- Cálculo estimado das faltas e saldo do banco de horas
        ISNULL(mp.HORAS_FALTA, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_FALTAS,
        ISNULL(bh.SALDO_HORAS_BANCO, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_HORAS_BANCO,
        
        -- Ficha Financeira (Eventos 0182, 8180)
        ISNULL(ff.HORAS_DESCONTADAS_FOLHA, 0) AS HORAS_DESCONTADAS_FOLHA,
        ISNULL(ff.VALOR_DESCONTADO_FOLHA, 0) AS VALOR_DESCONTADO_FOLHA
    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp ON mp.CODCOLIGADA = fv.CODCOLIGADA AND mp.CHAPA = fv.CHAPA
    LEFT JOIN AbonosFiltrados ab ON ab.CODCOLIGADA = fv.CODCOLIGADA AND ab.CHAPA = fv.CHAPA AND ab.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoBancoHoras bh ON bh.CODCOLIGADA = fv.CODCOLIGADA AND bh.CHAPA = fv.CHAPA AND bh.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoFichaFinanceira ff ON ff.CODCOLIGADA = fv.CODCOLIGADA AND ff.CHAPA = fv.CHAPA AND ff.MES_ANO = mp.MES_ANO
)

-- =========================================================================
-- BLOCO DE EXECUÇÃO: DAQUI PRA BAIXO É SO COMENTAR AS CTE QUE NÃO VÃO SER USADAS E EXECUTAR AS DE INTERESSE
-- =========================================================================

-- =========================================================================
-- BLOCO 5: TOP 10 CENTROS DE CUSTO (CENTRO_CUSTO)
-- =========================================================================
, RankedCentrosCusto AS (
    SELECT
    	MES_ANO,
        CENTRO_CUSTO,
        ROUND(SUM(HORAS_FALTA), 2) AS TOTAL_HORAS_FALTA_PONTO,
        ROUND(SUM(VALOR_DESCONTADO_FOLHA), 2) AS VALOR_DESCONTADO_FOLHA_R$,
        ROUND(SUM(CUSTO_ESTIMADO_FALTAS), 2) AS TOTAL_CUSTO_ESTIMADO_FALTAS_R$,
        
        -- Criando ranking
        ROW_NUMBER() OVER (
            PARTITION BY MES_ANO
            ORDER BY SUM(HORAS_FALTA) DESC
        ) AS RANKING
        
    FROM 
        ConsolidadoFuncionario
    GROUP BY 
    	MES_ANO, 
        CENTRO_CUSTO
)
SELECT
	MES_ANO,
    RANKING,
    CENTRO_CUSTO,
    TOTAL_HORAS_FALTA_PONTO,
    TOTAL_CUSTO_ESTIMADO_FALTAS_R$,
    VALOR_DESCONTADO_FOLHA_R$
    
FROM 
    RankedCentrosCusto
WHERE 
    RANKING <= 5
ORDER BY
	MES_ANO ASC,
    RANKING ASC;

""", 


"faltas_por_regional": """

-- =========================================================================
-- 1. PARAMETRIZAÇÃO DO PERÍODO DE ANÁLISE
-- =========================================================================
DECLARE @DataInicio DATE = ?;
DECLARE @DataFim    DATE = ?;

-- =========================================================================
-- 2. CADASTRO BASE DE FUNCIONÁRIOS
-- =========================================================================
WITH FuncionariosValidos AS (
    SELECT
        pfunc.CODCOLIGADA,
        pfunc.CHAPA,
        pfunc.NOME,
        pfunc.CODSECAO,
        psecao.NROCENCUSTOCONT AS CENTRO_CUSTO,
        
        -- Usado para remover o caractere "¶" chamado pilcrow que possui o Line feed e o Carriage Return basicamente ele pula a linha e volta pro inicio,
    	-- identificado no SQL Server com o código CHAR(10) e CHAR(13), porque estava quebrando o arquivo em csv na hora da formatação
    	REPLACE(REPLACE(psecao.DESCRICAO, CHAR(13), ''), CHAR(10), '') AS NOME_CENTRO_CUSTO,

        -- Regra de negócio aplicada definindo a regional e o seu conjunto de centro de custos em cada uma
        CASE 
            WHEN psecao.NROCENCUSTOCONT IN ('8101','8104', '8105', '8110', '8113', '8115', '8116', '8117', '8118', '8119','8120','8121', '8122', '8124', '8126')
                THEN 'ADMINISTRAÇÃO'
            WHEN psecao.NROCENCUSTOCONT IN ('8369', '8111')
                THEN 'TELECOM'    
            WHEN psecao.NROCENCUSTOCONT IN ('8295', '8296', '8422', '8272', '8274', '8293', '8294', '8401', '8403', '8411', '8413', '8427', '8431', '8432', '8433', '8290' ,'8419', '8425', '8426')
                THEN 'REGIONAL_SESU'    
            WHEN psecao.NROCENCUSTOCONT IN ('8279', '8410', '8429', '8408', '8423', '8270', '8284', '8298', '8409', '8421', '8430', '8519')
                THEN 'REGIONAL_CONE'
            ELSE 'NÃO CLASSIFICADO'
        END AS REGIONAL,
        
		-- Pegando a jornada de horas mensais de cada funcionário(Valor em minutos) e dividindo por 60 para obter o valor em horas no mês
        CAST((pfunc.JORNADAMENSAL / 60.0) AS FLOAT) AS JORNADAMENSAL,
        CAST(pfunc.SALARIO AS FLOAT) AS SALARIO,
        
        -- Dividindo o salário do funcionário pela jornada mensal em hora para obter o valor da hora de cada funcionário para futuramente
        -- multiplicar as horas de falta de cada funcionário e fazer uma estimativa de custo
        CASE 
            WHEN ISNULL(pfunc.JORNADAMENSAL, 0) = 0 THEN 0
            ELSE CAST(pfunc.SALARIO AS FLOAT) / (pfunc.JORNADAMENSAL / 60.0)
        END AS VALOR_HORA,
        
		-- Pegando a data de admissão e demissão para saber os funcionários ativos em cada mês
        CAST(pfunc.DATAADMISSAO AS DATE) AS DATAADMISSAO,
        CAST(pfunc.DATADEMISSAO AS DATE) AS DATADEMISSAO
    FROM 
        PFUNC pfunc
        
    -- Fazendo uma junção com PSECAO para pegar o código do centro de custo
    INNER JOIN PSECAO psecao ON psecao.CODCOLIGADA = pfunc.CODCOLIGADA AND psecao.CODIGO = pfunc.CODSECAO
    WHERE
    	-- Código da empresa Matriz
        pfunc.CODCOLIGADA = 3
        -- Funcionários com a letra "T" na Chapa significa que foram Transferidos ou Tomadores, ou seja, possui dois registros na tabela
    	-- sendo assim, ignorando o registro que possui o "T" na Chapa para não gerar duplicidade 
        AND pfunc.CHAPA NOT LIKE '%T%'
        -- os funcionários que são da categoria autônomos e intermitentes
        AND pfunc.CODCATEGORIAESOCIAL NOT IN ('111', '701')
        -- Retira da contagem a filial da INVERNADA SP
        AND pfunc.CODFILIAL <> 10
),

-- =========================================================================
-- 3. MOVIMENTAÇÃO DE PONTO E MESES EXISTENTES
-- =========================================================================
MovimentoPonto AS (
    SELECT 
        ponto.CODCOLIGADA,
        ponto.CHAPA,
        FORMAT(ponto.DATA, 'yyyy-MM') AS MES_ANO,
        EOMONTH(ponto.DATA) AS ULTIMO_DIA_MES,
        DATEFROMPARTS(YEAR(ponto.DATA), MONTH(ponto.DATA), 1) AS PRIMEIRO_DIA_MES,
        SUM(CAST(ISNULL(ponto.FALTA, 0) AS FLOAT) / 60.0) AS HORAS_FALTA,
        SUM(CAST(ISNULL(ponto.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO
        
    FROM 
        AAFHTFUN ponto
    WHERE
        ponto.CODCOLIGADA = 3
        AND ponto.DATA BETWEEN @DataInicio AND @DataFim
        
    -- Fazendo o agrupamento por essas campos para pegar o movimento do ponto de cada fucnionário por mês
    GROUP BY 
        ponto.CODCOLIGADA,
        ponto.CHAPA,
        FORMAT(ponto.DATA, 'yyyy-MM'),
        EOMONTH(ponto.DATA), -- Traz a data final do mês
        DATEFROMPARTS(YEAR(ponto.DATA), MONTH(ponto.DATA), 1) -- Traz a primeira data do mês
),

-- Tabela para trazer todos os mês do ano registrados no ponto para consultar os funcionários ativos mês a mês
MesesExistentes AS (
    SELECT DISTINCT 
        MES_ANO, 
        PRIMEIRO_DIA_MES, 
        ULTIMO_DIA_MES 
    FROM MovimentoPonto
),

-- =========================================================================
-- 4. ABONOS ESPECÍFICOS DE FALTAS (AABONOFUNCIONARIO)
-- =========================================================================
AbonosFiltrados AS (
    SELECT 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM') AS MES_ANO,
        SUM(
            CASE 
                -- Se tiver Intervalo de Inicio e Fim preenchidos
                WHEN abono.DATAHORAINICIO IS NOT NULL AND abono.DATAHORAFIM IS NOT NULL THEN
                    CAST(DATEDIFF(MINUTE, abono.DATAHORAINICIO, abono.DATAHORAFIM) AS FLOAT) / 60.0
                
                -- Se não tiver datas, utiliza a coluna NUMHORAS (convertendo minutos para horas)
                ELSE
                    CAST(ISNULL(abono.NUMHORAS, 0) AS FLOAT) / 60.0
            END
        ) AS HORAS_ABONADAS
    FROM 
        AABONOFUNCIONARIO abono
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = abono.CODCOLIGADA
        AND fv.CHAPA = abono.CHAPA
    WHERE 
        abono.CODCOLIGADA = 3
        -- Registro Ativo
        AND abono.SITUACAO = '1'
        -- Código de abono referente aos eventos de faltas
        AND abono.CODABONO IN ('008', '017', '020', '022', '028', '030', '031', '033', '035', '22', '407', '415', '432', '436')
        AND abono.DATAREFERENCIA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM')
),

-- =========================================================================
-- 7. BANCO DE HORAS (ASALDOBANCOHOR) - CÁLCULO DE SALDO MENSAL
-- =========================================================================
MovimentoBancoHoras AS (
-- Não precisa usar o SUM nos campos por que, o banco de horas trás os valores por mês e não por dia como o Movimento do ponto (AAFHTFUN)

    SELECT 
        asal.CODCOLIGADA,
        asal.CHAPA,
        FORMAT(asal.INICIOPER, 'yyyy-MM') AS MES_ANO,
        SUM(CAST(ISNULL(asal.FALTAANT, 0) AS FLOAT) / 60.0) AS HORAS_FALTA_ACUMULADO_ANTERIOR,
        SUM(CAST(ISNULL(asal.FALTAATU, 0) AS FLOAT) / 60.0) AS HORAS_FALTA_BANCO_MES,
        
        
        -- Sumarizando e calculando o saldo do banco de horas por funcionário no mês, fazendo a diferença
        -- entre as horas extras acumuladas + horas extras atuais e atrasos acumulados + atrasos atuais + faltas acumuladas + faltas atuais 
        SUM(
            CAST(
                (ISNULL(asal.EXTRAANT, 0) + ISNULL(asal.EXTRAATU, 0)) - 
                (ISNULL(asal.ATRASOANT, 0) + ISNULL(asal.FALTAANT, 0) + ISNULL(asal.ATRASOATU, 0) + ISNULL(asal.FALTAATU, 0))
            AS FLOAT) / 60.0
        ) AS SALDO_HORAS_BANCO
        
    FROM 
        ASALDOBANCOHOR asal
    WHERE 
        asal.CODCOLIGADA = 3
        
        -- Pegando o movimento do banco de horas de acordo com a data de inicio e data final dos parâmetros
        AND asal.INICIOPER >= @DataInicio 
        AND asal.FIMPER <= @DataFim
    GROUP BY 
        asal.CODCOLIGADA,
        asal.CHAPA,
        FORMAT(asal.INICIOPER, 'yyyy-MM')
),

-- =========================================================================
-- 8. FICHA FINANCEIRA - DESCONTOS DE FALTAS EM FOLHA (EVENTO 0182 e 8180)
-- =========================================================================
MovimentoFichaFinanceira AS (
    SELECT 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        
        -- Concatenando o ano com o mês para manter o padrão 'yyyy-MM'
        CONCAT(pffin.ANOCOMP, '-', RIGHT(CONCAT('0', pffin.MESCOMP), 2)) AS MES_ANO,
        
        -- Sumarizando a quantidade de referência do código de evento que se refere a quantidade de horas 
        SUM(CAST(ISNULL(pffin.REF, 0) AS FLOAT)) AS HORAS_DESCONTADAS_FOLHA,
        
        -- Sumarizando o valor de referência do código de evento que se refere ao valor em reais pago em relação a quantidade de horas do 'REF'
        SUM(CAST(ISNULL(pffin.VALOR, 0) AS FLOAT)) AS VALOR_DESCONTADO_FOLHA
        
    FROM 
        PFFINANC pffin
    WHERE 
        pffin.CODCOLIGADA = 3
        
        -- Código na folha de falta (0182), falta reduzida(Quando trabalha noturno)(8180)
        AND pffin.CODEVENTO IN ('0182', '8180')
        
        -- Formatando a data para trazer o primeiro dia do ano e mês da ficha financeira para manter o padrão no filtro
        AND DATEFROMPARTS(pffin.ANOCOMP, pffin.MESCOMP, 1) BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        pffin.ANOCOMP,
        pffin.MESCOMP
),

-- =========================================================================
-- 9. DETALHAMENTO CONSOLIDADO POR FUNCIONÁRIO E MÊS
-- =========================================================================
ConsolidadoFuncionario AS (
    SELECT 
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        fv.CHAPA,
        fv.NOME,
        mp.MES_ANO,
        
        -- Ponto Eletrônico
        ISNULL(mp.HORAS_FALTA, 0) AS HORAS_FALTA,
        --ISNULL(mp.HORAS_ABONO, 0) AS HORAS_ABONO,
        ISNULL(mp.HORAS_ATRASO, 0) AS HORAS_ATRASO,
        
        -- Abonos Específicos (AABONOFUNCIONARIO)
        ISNULL(ab.HORAS_ABONADAS, 0) AS HORAS_ABONADAS,
        
        -- Banco de Horas
        ISNULL(bh.HORAS_FALTA_BANCO_MES, 0) AS HORAS_FALTA_BANCO,
        ISNULL(bh.SALDO_HORAS_BANCO, 0) AS SALDO_HORAS_BANCO,
        
        -- Cálculo estimado das faltas e saldo do banco de horas
        ISNULL(mp.HORAS_FALTA, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_FALTAS,
        ISNULL(bh.SALDO_HORAS_BANCO, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_HORAS_BANCO,
        
        -- Ficha Financeira (Eventos 0182, 8180)
        ISNULL(ff.HORAS_DESCONTADAS_FOLHA, 0) AS HORAS_DESCONTADAS_FOLHA,
        ISNULL(ff.VALOR_DESCONTADO_FOLHA, 0) AS VALOR_DESCONTADO_FOLHA
    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp ON mp.CODCOLIGADA = fv.CODCOLIGADA AND mp.CHAPA = fv.CHAPA
    LEFT JOIN AbonosFiltrados ab ON ab.CODCOLIGADA = fv.CODCOLIGADA AND ab.CHAPA = fv.CHAPA AND ab.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoBancoHoras bh ON bh.CODCOLIGADA = fv.CODCOLIGADA AND bh.CHAPA = fv.CHAPA AND bh.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoFichaFinanceira ff ON ff.CODCOLIGADA = fv.CODCOLIGADA AND ff.CHAPA = fv.CHAPA AND ff.MES_ANO = mp.MES_ANO
)

-- =========================================================================
-- BLOCO DE EXECUÇÃO: DAQUI PRA BAIXO É SO COMENTAR AS CTE QUE NÃO VÃO SER USADAS E EXECUTAR AS DE INTERESSE
-- =========================================================================

-- =========================================================================
-- BLOCO 5: FALTAS ENTRE AS REGIONAIS (REGIONAIS)
-- =========================================================================

    SELECT
    	MES_ANO,
        REGIONAL,
        ROUND(SUM(HORAS_FALTA), 2) AS TOTAL_HORAS_FALTA_PONTO,
        ROUND(SUM(HORAS_FALTA_BANCO), 2) AS TOTAL_HORAS_FALTA_BANCO,
        ROUND(SUM(VALOR_DESCONTADO_FOLHA), 2) AS VALOR_DESCONTADO_FOLHA_R$,
        ROUND(SUM(CUSTO_ESTIMADO_FALTAS), 2) AS TOTAL_CUSTO_ESTIMADO_FALTAS_R$
        
    FROM 
        ConsolidadoFuncionario
    GROUP BY 
    	MES_ANO, 
        REGIONAL
    ORDER BY
    	MES_ANO ASC,
        TOTAL_HORAS_FALTA_PONTO DESC;


""",


"faltas_por_mes": """

-- =========================================================================
-- 1. PARAMETRIZAÇÃO DO PERÍODO DE ANÁLISE
-- =========================================================================
DECLARE @DataInicio DATE = ?;
DECLARE @DataFim    DATE = ?;

-- =========================================================================
-- 2. CADASTRO BASE DE FUNCIONÁRIOS
-- =========================================================================
WITH FuncionariosValidos AS (
    SELECT
        pfunc.CODCOLIGADA,
        pfunc.CHAPA,
        pfunc.NOME,
        psecao.NROCENCUSTOCONT AS CENTRO_CUSTO,
        
        -- Usado para remover o caractere "¶" chamado pilcrow que possui o Line feed e o Carriage Return basicamente ele pula a linha e volta pro inicio,
    	-- identificado no SQL Server com o código CHAR(10) e CHAR(13), porque estava quebrando o arquivo em csv na hora da formatação
    	REPLACE(REPLACE(psecao.DESCRICAO, CHAR(13), ''), CHAR(10), '') AS NOME_CENTRO_CUSTO,

        -- Regra de negócio aplicada definindo a regional e o seu conjunto de centro de custos em cada uma
        CASE 
            WHEN psecao.NROCENCUSTOCONT IN ('8101','8104', '8105', '8110', '8113', '8115', '8116', '8117', '8118', '8119','8120','8121', '8122', '8124', '8126')
                THEN 'ADMINISTRAÇÃO'
            WHEN psecao.NROCENCUSTOCONT IN ('8369', '8111')
                THEN 'TELECOM'    
            WHEN psecao.NROCENCUSTOCONT IN ('8295', '8296', '8422', '8272', '8274', '8293', '8294', '8401', '8403', '8411', '8413', '8427', '8431', '8432', '8433', '8290' ,'8419', '8425', '8426')
                THEN 'REGIONAL_SESU'    
            WHEN psecao.NROCENCUSTOCONT IN ('8279', '8410', '8429', '8408', '8423', '8270', '8284', '8298', '8409', '8421', '8430', '8519')
                THEN 'REGIONAL_CONE'
            ELSE 'NÃO CLASSIFICADO'
        END AS REGIONAL,
        
		-- Pegando a jornada de horas mensais de cada funcionário(Valor em minutos) e dividindo por 60 para obter o valor em horas no mês
        CAST((pfunc.JORNADAMENSAL / 60.0) AS FLOAT) AS JORNADAMENSAL,
        CAST(pfunc.SALARIO AS FLOAT) AS SALARIO,
        
        -- Dividindo o salário do funcionário pela jornada mensal em hora para obter o valor da hora de cada funcionário para futuramente
        -- multiplicar as horas de falta de cada funcionário e fazer uma estimativa de custo
        CASE 
            WHEN ISNULL(pfunc.JORNADAMENSAL, 0) = 0 THEN 0
            ELSE CAST(pfunc.SALARIO AS FLOAT) / (pfunc.JORNADAMENSAL / 60.0)
        END AS VALOR_HORA,
        
		-- Pegando a data de admissão e demissão para saber os funcionários ativos em cada mês
        CAST(pfunc.DATAADMISSAO AS DATE) AS DATAADMISSAO,
        CAST(pfunc.DATADEMISSAO AS DATE) AS DATADEMISSAO
    FROM 
        PFUNC pfunc
        
    -- Fazendo uma junção com PSECAO para pegar o código do centro de custo
    INNER JOIN PSECAO psecao ON psecao.CODCOLIGADA = pfunc.CODCOLIGADA AND psecao.CODIGO = pfunc.CODSECAO
    WHERE
    	-- Código da empresa Matriz
        pfunc.CODCOLIGADA = 3
        -- Funcionários com a letra "T" na Chapa significa que foram Transferidos ou Tomadores, ou seja, possui dois registros na tabela
    	-- sendo assim, ignorando o registro que possui o "T" na Chapa para não gerar duplicidade 
        AND pfunc.CHAPA NOT LIKE '%T%'
        -- os funcionários que são da categoria autônomos e intermitentes
        AND pfunc.CODCATEGORIAESOCIAL NOT IN ('111', '701')
        -- Retira da contagem a filial da INVERNADA SP
        AND pfunc.CODFILIAL <> 10
),

-- =========================================================================
-- 3. MOVIMENTAÇÃO DE PONTO E MESES EXISTENTES
-- =========================================================================
MovimentoPonto AS (
    SELECT 
        ponto.CODCOLIGADA,
        ponto.CHAPA,
        FORMAT(ponto.DATA, 'yyyy-MM') AS MES_ANO,
        EOMONTH(ponto.DATA) AS ULTIMO_DIA_MES,
        DATEFROMPARTS(YEAR(ponto.DATA), MONTH(ponto.DATA), 1) AS PRIMEIRO_DIA_MES,
        SUM(CAST(ISNULL(ponto.FALTA, 0) AS FLOAT) / 60.0) AS HORAS_FALTA,
        SUM(CAST(ISNULL(ponto.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO
        
    FROM 
        AAFHTFUN ponto
    WHERE
        ponto.CODCOLIGADA = 3
        AND ponto.DATA BETWEEN @DataInicio AND @DataFim
        
    -- Fazendo o agrupamento por essas campos para pegar o movimento do ponto de cada fucnionário por mês
    GROUP BY 
        ponto.CODCOLIGADA,
        ponto.CHAPA,
        FORMAT(ponto.DATA, 'yyyy-MM'),
        EOMONTH(ponto.DATA), -- Traz a data final do mês
        DATEFROMPARTS(YEAR(ponto.DATA), MONTH(ponto.DATA), 1) -- Traz a primeira data do mês
),

-- Tabela para trazer todos os mês do ano registrados no ponto para consultar os funcionários ativos mês a mês
MesesExistentes AS (
    SELECT DISTINCT 
        MES_ANO, 
        PRIMEIRO_DIA_MES, 
        ULTIMO_DIA_MES 
    FROM MovimentoPonto
),

-- =========================================================================
-- 4. ABONOS ESPECÍFICOS DE FALTAS (AABONOFUNCIONARIO)
-- =========================================================================
AbonosFiltrados AS (
    SELECT 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM') AS MES_ANO,
        SUM(
            CASE 
                -- Se tiver Intervalo de Inicio e Fim preenchidos
                WHEN abono.DATAHORAINICIO IS NOT NULL AND abono.DATAHORAFIM IS NOT NULL THEN
                    CAST(DATEDIFF(MINUTE, abono.DATAHORAINICIO, abono.DATAHORAFIM) AS FLOAT) / 60.0
                
                -- Se não tiver datas, utiliza a coluna NUMHORAS (convertendo minutos para horas)
                ELSE
                    CAST(ISNULL(abono.NUMHORAS, 0) AS FLOAT) / 60.0
            END
        ) AS HORAS_ABONADAS
    FROM 
        AABONOFUNCIONARIO abono
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = abono.CODCOLIGADA
        AND fv.CHAPA = abono.CHAPA
    WHERE 
        abono.CODCOLIGADA = 3
        -- Registro Ativo
        AND abono.SITUACAO = '1'
        -- Código de abono referente aos eventos de faltas
        AND abono.CODABONO IN ('008', '017', '020', '022', '028', '030', '031', '033', '035', '22', '407', '415', '432', '436')
        AND abono.DATAREFERENCIA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM')
),

-- =========================================================================
-- 7. BANCO DE HORAS (ASALDOBANCOHOR) - CÁLCULO DE SALDO MENSAL
-- =========================================================================
MovimentoBancoHoras AS (
-- Não precisa usar o SUM nos campos por que, o banco de horas trás os valores por mês e não por dia como o Movimento do ponto (AAFHTFUN)

    SELECT 
        asal.CODCOLIGADA,
        asal.CHAPA,
        FORMAT(asal.INICIOPER, 'yyyy-MM') AS MES_ANO,
        SUM(CAST(ISNULL(asal.FALTAANT, 0) AS FLOAT) / 60.0) AS HORAS_FALTA_ACUMULADO_ANTERIOR,
        SUM(CAST(ISNULL(asal.FALTAATU, 0) AS FLOAT) / 60.0) AS HORAS_FALTA_BANCO_MES,
        
        
        -- Sumarizando e calculando o saldo do banco de horas por funcionário no mês, fazendo a diferença
        -- entre as horas extras acumuladas + horas extras atuais e atrasos acumulados + atrasos atuais + faltas acumuladas + faltas atuais 
        SUM(
            CAST(
                (ISNULL(asal.EXTRAANT, 0) + ISNULL(asal.EXTRAATU, 0)) - 
                (ISNULL(asal.ATRASOANT, 0) + ISNULL(asal.FALTAANT, 0) + ISNULL(asal.ATRASOATU, 0) + ISNULL(asal.FALTAATU, 0))
            AS FLOAT) / 60.0
        ) AS SALDO_HORAS_BANCO
        
    FROM 
        ASALDOBANCOHOR asal
    WHERE 
        asal.CODCOLIGADA = 3
        
        -- Pegando o movimento do banco de horas de acordo com a data de inicio e data final dos parâmetros
        AND asal.INICIOPER >= @DataInicio 
        AND asal.FIMPER <= @DataFim
    GROUP BY 
        asal.CODCOLIGADA,
        asal.CHAPA,
        FORMAT(asal.INICIOPER, 'yyyy-MM')
),

-- =========================================================================
-- 8. FICHA FINANCEIRA - DESCONTOS DE FALTAS EM FOLHA (EVENTO 0182 e 8180)
-- =========================================================================
MovimentoFichaFinanceira AS (
    SELECT 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        
        -- Concatenando o ano com o mês para manter o padrão 'yyyy-MM'
        CONCAT(pffin.ANOCOMP, '-', RIGHT(CONCAT('0', pffin.MESCOMP), 2)) AS MES_ANO,
        
        -- Sumarizando a quantidade de referência do código de evento que se refere a quantidade de horas 
        SUM(CAST(ISNULL(pffin.REF, 0) AS FLOAT)) AS HORAS_DESCONTADAS_FOLHA,
        
        -- Sumarizando o valor de referência do código de evento que se refere ao valor em reais pago em relação a quantidade de horas do 'REF'
        SUM(CAST(ISNULL(pffin.VALOR, 0) AS FLOAT)) AS VALOR_DESCONTADO_FOLHA
        
    FROM 
        PFFINANC pffin
    WHERE 
        pffin.CODCOLIGADA = 3
        
        -- Código na folha de falta (0182), falta reduzida(Quando trabalha noturno)(8180)
        AND pffin.CODEVENTO IN ('0182', '8180')
        
        -- Formatando a data para trazer o primeiro dia do ano e mês da ficha financeira para manter o padrão no filtro
        AND DATEFROMPARTS(pffin.ANOCOMP, pffin.MESCOMP, 1) BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        pffin.ANOCOMP,
        pffin.MESCOMP
),

-- =========================================================================
-- 9. DETALHAMENTO CONSOLIDADO POR FUNCIONÁRIO E MÊS
-- =========================================================================
ConsolidadoFuncionario AS (
    SELECT 
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        fv.CHAPA,
        fv.NOME,
        mp.MES_ANO,
        
        -- Ponto Eletrônico
        ISNULL(mp.HORAS_FALTA, 0) AS HORAS_FALTA,
        --ISNULL(mp.HORAS_ABONO, 0) AS HORAS_ABONO,
        ISNULL(mp.HORAS_ATRASO, 0) AS HORAS_ATRASO,
        
        -- Abonos Específicos (AABONOFUNCIONARIO)
        ISNULL(ab.HORAS_ABONADAS, 0) AS HORAS_ABONADAS,
        
        -- Banco de Horas
        ISNULL(bh.HORAS_FALTA_BANCO_MES, 0) AS HORAS_FALTA_BANCO,
        ISNULL(bh.SALDO_HORAS_BANCO, 0) AS SALDO_HORAS_BANCO,
        
        -- Cálculo estimado das faltas e saldo do banco de horas
        ISNULL(mp.HORAS_FALTA, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_FALTAS,
        ISNULL(bh.SALDO_HORAS_BANCO, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_HORAS_BANCO,
        
        -- Ficha Financeira (Eventos 0182, 8180)
        ISNULL(ff.HORAS_DESCONTADAS_FOLHA, 0) AS HORAS_DESCONTADAS_FOLHA,
        ISNULL(ff.VALOR_DESCONTADO_FOLHA, 0) AS VALOR_DESCONTADO_FOLHA
    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp ON mp.CODCOLIGADA = fv.CODCOLIGADA AND mp.CHAPA = fv.CHAPA
    LEFT JOIN AbonosFiltrados ab ON ab.CODCOLIGADA = fv.CODCOLIGADA AND ab.CHAPA = fv.CHAPA AND ab.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoBancoHoras bh ON bh.CODCOLIGADA = fv.CODCOLIGADA AND bh.CHAPA = fv.CHAPA AND bh.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoFichaFinanceira ff ON ff.CODCOLIGADA = fv.CODCOLIGADA AND ff.CHAPA = fv.CHAPA AND ff.MES_ANO = mp.MES_ANO
)

-- =========================================================================
-- BLOCO DE EXECUÇÃO: DAQUI PRA BAIXO É SO COMENTAR AS CTE QUE NÃO VÃO SER USADAS E EXECUTAR AS DE INTERESSE
-- =========================================================================

-- =========================================================================
-- BLOCO 1: RESUMO MENSAL (FALTAS, ABONOS FILTRADOS E FOLHA)
-- =========================================================================


SELECT 
    cf.MES_ANO,
    ROUND(SUM(cf.HORAS_FALTA), 2) AS TOTAL_HORAS_FALTA_PONTO,
    ROUND(SUM(cf.CUSTO_ESTIMADO_FALTAS), 2) AS CUSTO_ESTIMADO_FALTAS_R$,
    
    -- Valores da Ficha Financeira (Evento 0182, 8180)
    ROUND(SUM(cf.HORAS_DESCONTADAS_FOLHA), 2) AS TOTAL_HORAS_DESCONTADAS_FOLHA,
    ROUND(SUM(cf.VALOR_DESCONTADO_FOLHA), 2) AS VALOR_DESCONTADO_FOLHA_R$
    
FROM 
	ConsolidadoFuncionario cf
GROUP BY 
    cf.MES_ANO
ORDER BY 
    cf.MES_ANO ASC;

"""

}