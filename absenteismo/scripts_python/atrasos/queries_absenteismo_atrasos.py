


SCRIPTS_SQL = {

    "atrasos_por_mes": """

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
        
        -- Usado para remover o caractere "¶" chamado pilcrow que possui o Line feed e o Carriage Return basicamente ele faz um pulo de linha e volta pro inicio,
    	-- identificado no SQL Server com o código CHAR(10) e CHAR(13), porque estava quebrando o arquivo em csv na hora da formatação
    	REPLACE(REPLACE(psecao.DESCRICAO, CHAR(13), ''), CHAR(10), '') AS NOME_CENTRO_CUSTO,
        
        -- Dados de Função
        ISNULL(pfuncao.NOME, 'NÃO INFORMADO') AS FUNCAO,
        
        -- Dados Pessoais
        ISNULL(ppessoa.SEXO, 'N/D') AS SEXO,
        DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) - 
            CASE 
                WHEN DATEADD(YEAR, DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()), ppessoa.DTNASCIMENTO) > GETDATE() 
                THEN 1 ELSE 0 
            END AS IDADE,
		
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

        -- Dividindo o salário do funcionário pela jornada mensal em hora para obter o valor da hora de cada funcionário para futuramente
        -- multiplicar as horas de falta de cada funcionário e fazer uma estimativa de custo
        CAST((pfunc.JORNADAMENSAL / 60.0) AS FLOAT) AS JORNADAMENSAL,
        CAST(pfunc.SALARIO AS FLOAT) AS SALARIO,
        
        -- Pegando a jornada de horas mensais de cada funcionário(Valor em minutos) e dividindo por 60 para obter o valor em horas no mês
        CASE 
            WHEN ISNULL(pfunc.JORNADAMENSAL, 0) = 0 THEN 0
            ELSE CAST(pfunc.SALARIO AS FLOAT) / (pfunc.JORNADAMENSAL / 60.0)
        END AS VALOR_HORA
        
    FROM 
        PFUNC pfunc
    INNER JOIN PSECAO psecao 
        ON psecao.CODCOLIGADA = pfunc.CODCOLIGADA 
        AND psecao.CODIGO = pfunc.CODSECAO
    LEFT JOIN PFUNCAO pfuncao 
        ON pfuncao.CODCOLIGADA = pfunc.CODCOLIGADA 
        AND pfuncao.CODIGO = pfunc.CODFUNCAO
    LEFT JOIN PPESSOA ppessoa 
        ON ppessoa.CODIGO = pfunc.CODPESSOA
    WHERE 
        pfunc.CODCOLIGADA = 3
        AND pfunc.CHAPA NOT LIKE '%T%'
        AND pfunc.CODCATEGORIAESOCIAL NOT IN ('111', '701')
        -- Retira da contagem a filial da INVERNADA SP
        AND pfunc.CODFILIAL <> 10
),

-- =========================================================================
-- 3. MOVIMENTO DE ATRASOS NO PONTO (AAFHTFUN)
-- =========================================================================
MovimentoPonto AS (

    SELECT 
        ponto.CODCOLIGADA,
        ponto.CHAPA,
        FORMAT(ponto.DATA, 'yyyy-MM') AS MES_ANO,
        
        -- Quantidade de dias com atraso registrado
        COUNT(CASE WHEN ISNULL(ponto.ATRASO, 0) > 0 THEN 1 END) AS QTD_OCORRENCIAS_ATRASO,
        
        -- Soma das horas de atraso no mês (convertido de minutos para horas)
        SUM(CAST(ISNULL(ponto.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO
        
    FROM AAFHTFUN ponto 
    WHERE 
    	ponto.CODCOLIGADA = 3
        AND ponto.DATA BETWEEN @DataInicio AND @DataFim
        AND ISNULL(ponto.ATRASO, 0) > 0
    GROUP BY 
        ponto.CODCOLIGADA,
        ponto.CHAPA,
        FORMAT(ponto.DATA, 'yyyy-MM')
),

-- =========================================================================
-- 4. DESCONTOS DE ATRASOS NA FOLHA (PFFINANC - EVENTO 0163)
-- =========================================================================
MovimentoFichaFinanceira AS (

    SELECT 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        
        -- Concatenando o ano com o mês para manter o padrão 'yyyy-MM'
        FORMAT(CAST(CONCAT(pffin.ANOCOMP, '-', RIGHT('0' + CAST(pffin.MESCOMP AS VARCHAR(2)), 2), '-01') AS DATE), 'yyyy-MM') AS MES_ANO,
        
        -- Sumarizando a quantidade de referência do código de evento que se refere a quantidade de horas 
        SUM(CAST(ISNULL(pffin.REF, 0) AS FLOAT)) AS HORAS_DESCONTADAS_FOLHA,
        
        -- Sumarizando o valor de referência do código de evento que se refere ao valor em reais pago em relação a quantidade de horas do 'REF'
        SUM(CAST(ISNULL(pffin.VALOR, 0) AS FLOAT)) AS VALOR_DESCONTADO_FOLHA
    FROM 
        PFFINANC pffin
    WHERE 
        pffin.CODCOLIGADA = 3
        AND pffin.CODEVENTO = '0163'
        AND CAST(CONCAT(pffin.ANOCOMP, '-', RIGHT('0' + CAST(pffin.MESCOMP AS VARCHAR(2)), 2), '-01') AS DATE) 
            BETWEEN @DataInicio AND DATEADD(MONTH, 1, @DataFim) -- Cobre folha do período
    GROUP BY 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        pffin.ANOCOMP,
        pffin.MESCOMP
),

-- =========================================================================
-- 5. MOVIMENTO DO BANCO DE HORAS PARA ATRASOS (ASALDOBANCOHOR)
-- =========================================================================
MovimentoBancoHoras AS (
    SELECT 
        asal.CODCOLIGADA,
        asal.CHAPA,
        FORMAT(asal.INICIOPER, 'yyyy-MM') AS MES_ANO,
        SUM(CAST(ISNULL(asal.ATRASOANT, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO_ACUMULADO_ANTERIOR,
        SUM(CAST(ISNULL(asal.ATRASOATU, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO_BANCO_MES,
        
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
        AND asal.INICIOPER BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        asal.CODCOLIGADA,
        asal.CHAPA,
        FORMAT(asal.INICIOPER, 'yyyy-MM')
),


ConsolidadoFuncionario AS (
    SELECT 
   		mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        fv.CHAPA,
        fv.NOME,
        
        -- Ponto Eletrônico
        --ISNULL(mp.HORAS_FALTA, 0) AS HORAS_FALTA,
        --ISNULL(mp.HORAS_ABONO, 0) AS HORAS_ABONO,
        ISNULL(mp.HORAS_ATRASO, 0) AS HORAS_ATRASO,
        
        
        -- Banco de Horas
        ISNULL(bh.HORAS_ATRASO_ACUMULADO_ANTERIOR, 0) AS HORAS_FALTA_BANCO_MES_ANTERIOR,
        ISNULL(bh.HORAS_ATRASO_BANCO_MES, 0) AS HORAS_ATRASO_BANCO_ATUAL,
        
        -- Cálculo estimado das faltas e saldo do banco de horas
        -- Obs: Se calcular pelas horas base do ponto, vai refletir em valores inrreais naqueles meses em que o funcionário trabalho menos horas,
        -- consequentemente em um valor da hora maior
        ISNULL(mp.HORAS_ATRASO, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_ATRASOS_PONTO,
        ISNULL(bh.HORAS_ATRASO_BANCO_MES, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_ATRASOS_BANCO,
        
        -- Ficha Financeira (Eventos 0163)
        ISNULL(ff.HORAS_DESCONTADAS_FOLHA, 0) AS HORAS_DESCONTADAS_FOLHA,
        ISNULL(ff.VALOR_DESCONTADO_FOLHA, 0) AS VALOR_DESCONTADO_FOLHA
        
    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp ON mp.CODCOLIGADA = fv.CODCOLIGADA AND mp.CHAPA = fv.CHAPA
    LEFT JOIN MovimentoBancoHoras bh ON bh.CODCOLIGADA = fv.CODCOLIGADA AND bh.CHAPA = fv.CHAPA AND bh.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoFichaFinanceira ff ON ff.CODCOLIGADA = fv.CODCOLIGADA AND ff.CHAPA = fv.CHAPA AND ff.MES_ANO = mp.MES_ANO
)


-- ====================================================================================
-- BLOCO DE EXECUÇÃO: APARTIR DAQUI PRA BAIXO COMENTE AS CONSULTAS QUE NÃO FOREM USADAS
-- ====================================================================================

-- =========================================================================
-- BLOCO 1: RESUMO MENSAL (PONTO X FOLHA X BANCO DE HORAS)
-- =========================================================================
SELECT 
    cf.MES_ANO,
    ROUND(SUM(cf.HORAS_ATRASO), 2) AS TOTAL_HORAS_ATRASO_PONTO,
    ROUND(SUM(ISNULL(cf.HORAS_ATRASO_BANCO_ATUAL, 0)), 2) AS TOTAL_HORAS_ATRASO_BANCO,
    ROUND(SUM(cf.CUSTO_ESTIMADO_ATRASOS_PONTO), 2) AS TOTAL_CUSTO_ESTIMADO_ATRASOS_PONTO_R$,
    ROUND(SUM(cf.CUSTO_ESTIMADO_ATRASOS_BANCO), 2) AS TOTAL_CUSTO_ESTIMADO_ATRASOS_BANCO_R$,
    ROUND(SUM(ISNULL(cf.VALOR_DESCONTADO_FOLHA, 0)), 2) AS VALOR_DESCONTADO_FOLHA_R$
    
FROM 
    ConsolidadoFuncionario cf
WHERE
	cf.HORAS_ATRASO > 0
GROUP BY 
    cf.MES_ANO
ORDER BY 
    cf.MES_ANO ASC;

""",


"top_5_atrasos_por_centro_custo": """


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
        
        -- Usado para remover o caractere "¶" chamado pilcrow que possui o Line feed e o Carriage Return basicamente ele pula uma linha e volta pro inicio,
    	-- identificado no SQL Server com o código CHAR(10) e CHAR(13), porque estava quebrando o arquivo em csv na hora da formatação
    	REPLACE(REPLACE(psecao.DESCRICAO, CHAR(13), ''), CHAR(10), '') AS NOME_CENTRO_CUSTO,
        
        -- Dados de Função
        ISNULL(pfuncao.NOME, 'NÃO INFORMADO') AS FUNCAO,
        
        -- Dados Pessoais
        ISNULL(ppessoa.SEXO, 'N/D') AS SEXO,
        DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) - 
            CASE 
                WHEN DATEADD(YEAR, DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()), ppessoa.DTNASCIMENTO) > GETDATE() 
                THEN 1 ELSE 0 
            END AS IDADE,
		
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

        -- Dividindo o salário do funcionário pela jornada mensal em hora para obter o valor da hora de cada funcionário para futuramente
        -- multiplicar as horas de falta de cada funcionário e fazer uma estimativa de custo
        CAST((pfunc.JORNADAMENSAL / 60.0) AS FLOAT) AS JORNADAMENSAL,
        CAST(pfunc.SALARIO AS FLOAT) AS SALARIO,
        
        -- Pegando a jornada de horas mensais de cada funcionário(Valor em minutos) e dividindo por 60 para obter o valor em horas no mês
        CASE 
            WHEN ISNULL(pfunc.JORNADAMENSAL, 0) = 0 THEN 0
            ELSE CAST(pfunc.SALARIO AS FLOAT) / (pfunc.JORNADAMENSAL / 60.0)
        END AS VALOR_HORA
        
    FROM 
        PFUNC pfunc
    INNER JOIN PSECAO psecao 
        ON psecao.CODCOLIGADA = pfunc.CODCOLIGADA 
        AND psecao.CODIGO = pfunc.CODSECAO
    LEFT JOIN PFUNCAO pfuncao 
        ON pfuncao.CODCOLIGADA = pfunc.CODCOLIGADA 
        AND pfuncao.CODIGO = pfunc.CODFUNCAO
    LEFT JOIN PPESSOA ppessoa 
        ON ppessoa.CODIGO = pfunc.CODPESSOA
    WHERE 
        pfunc.CODCOLIGADA = 3
        AND pfunc.CHAPA NOT LIKE '%T%'
        AND pfunc.CODCATEGORIAESOCIAL NOT IN ('111', '701')
        -- Retira da contagem a filial da INVERNADA SP
        AND pfunc.CODFILIAL <> 10
),

-- =========================================================================
-- 3. MOVIMENTO DE ATRASOS NO PONTO (AAFHTFUN)
-- =========================================================================
MovimentoPonto AS (

    SELECT 
        ponto.CODCOLIGADA,
        ponto.CHAPA,
        FORMAT(ponto.DATA, 'yyyy-MM') AS MES_ANO,
        
        -- Quantidade de dias com atraso registrado
        COUNT(CASE WHEN ISNULL(ponto.ATRASO, 0) > 0 THEN 1 END) AS QTD_OCORRENCIAS_ATRASO,
        
        -- Soma das horas de atraso no mês (convertido de minutos para horas)
        SUM(CAST(ISNULL(ponto.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO
        
    FROM AAFHTFUN ponto 
    WHERE 
    	ponto.CODCOLIGADA = 3
        AND ponto.DATA BETWEEN @DataInicio AND @DataFim
        AND ISNULL(ponto.ATRASO, 0) > 0
    GROUP BY 
        ponto.CODCOLIGADA,
        ponto.CHAPA,
        FORMAT(ponto.DATA, 'yyyy-MM')
),

-- =========================================================================
-- 4. DESCONTOS DE ATRASOS NA FOLHA (PFFINANC - EVENTO 0163)
-- =========================================================================
MovimentoFichaFinanceira AS (

    SELECT 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        
        -- Concatenando o ano com o mês para manter o padrão 'yyyy-MM'
        FORMAT(CAST(CONCAT(pffin.ANOCOMP, '-', RIGHT('0' + CAST(pffin.MESCOMP AS VARCHAR(2)), 2), '-01') AS DATE), 'yyyy-MM') AS MES_ANO,
        
        -- Sumarizando a quantidade de referência do código de evento que se refere a quantidade de horas 
        SUM(CAST(ISNULL(pffin.REF, 0) AS FLOAT)) AS HORAS_DESCONTADAS_FOLHA,
        
        -- Sumarizando o valor de referência do código de evento que se refere ao valor em reais pago em relação a quantidade de horas do 'REF'
        SUM(CAST(ISNULL(pffin.VALOR, 0) AS FLOAT)) AS VALOR_DESCONTADO_FOLHA
    FROM 
        PFFINANC pffin
    WHERE 
        pffin.CODCOLIGADA = 3
        AND pffin.CODEVENTO = '0163'
        AND CAST(CONCAT(pffin.ANOCOMP, '-', RIGHT('0' + CAST(pffin.MESCOMP AS VARCHAR(2)), 2), '-01') AS DATE) 
            BETWEEN @DataInicio AND DATEADD(MONTH, 1, @DataFim) -- Cobre folha do período
    GROUP BY 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        pffin.ANOCOMP,
        pffin.MESCOMP
),

-- =========================================================================
-- 5. MOVIMENTO DO BANCO DE HORAS PARA ATRASOS (ASALDOBANCOHOR)
-- =========================================================================
MovimentoBancoHoras AS (
    SELECT 
        asal.CODCOLIGADA,
        asal.CHAPA,
        FORMAT(asal.INICIOPER, 'yyyy-MM') AS MES_ANO,
        SUM(CAST(ISNULL(asal.ATRASOANT, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO_ACUMULADO_ANTERIOR,
        SUM(CAST(ISNULL(asal.ATRASOATU, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO_BANCO_MES,
        
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
        AND asal.INICIOPER BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        asal.CODCOLIGADA,
        asal.CHAPA,
        FORMAT(asal.INICIOPER, 'yyyy-MM')
),


ConsolidadoFuncionario AS (
    SELECT 
   		mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        fv.CHAPA,
        fv.NOME,
        
        -- Ponto Eletrônico
        --ISNULL(mp.HORAS_FALTA, 0) AS HORAS_FALTA,
        --ISNULL(mp.HORAS_ABONO, 0) AS HORAS_ABONO,
        ISNULL(mp.HORAS_ATRASO, 0) AS HORAS_ATRASO,
        
        
        -- Banco de Horas
        ISNULL(bh.HORAS_ATRASO_ACUMULADO_ANTERIOR, 0) AS HORAS_FALTA_BANCO_MES_ANTERIOR,
        ISNULL(bh.HORAS_ATRASO_BANCO_MES, 0) AS HORAS_ATRASO_BANCO_ATUAL,
        
        -- Cálculo estimado das faltas e saldo do banco de horas
        -- Obs: Se calcular pelas horas base do ponto, vai refletir em valores inrreais naqueles meses em que o funcionário trabalho menos horas,
        -- consequentemente em um valor da hora maior
        ISNULL(mp.HORAS_ATRASO, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_ATRASOS_PONTO,
        ISNULL(bh.HORAS_ATRASO_BANCO_MES, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_ATRASOS_BANCO,
        
        -- Ficha Financeira (Eventos 0163)
        ISNULL(ff.HORAS_DESCONTADAS_FOLHA, 0) AS HORAS_DESCONTADAS_FOLHA,
        ISNULL(ff.VALOR_DESCONTADO_FOLHA, 0) AS VALOR_DESCONTADO_FOLHA
        
    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp ON mp.CODCOLIGADA = fv.CODCOLIGADA AND mp.CHAPA = fv.CHAPA
    LEFT JOIN MovimentoBancoHoras bh ON bh.CODCOLIGADA = fv.CODCOLIGADA AND bh.CHAPA = fv.CHAPA AND bh.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoFichaFinanceira ff ON ff.CODCOLIGADA = fv.CODCOLIGADA AND ff.CHAPA = fv.CHAPA AND ff.MES_ANO = mp.MES_ANO
)

-- =========================================================================
-- BLOCO DE EXECUÇÃO: DAQUI PRA BAIXO É SO COMENTAR AS CTE QUE NÃO VÃO SER USADAS E EXECUTAR AS DE INTERESSE
-- =========================================================================

-- =========================================================================
-- BLOCO 4: TOP 5 CENTROS DE CUSTO COM MAIS ATRASOS (POR MÊS E REGIONAL)
-- =========================================================================
,RankingCentrosCusto AS (
    SELECT 
        cf.MES_ANO,
        cf.CENTRO_CUSTO,
        ROUND(SUM(cf.HORAS_ATRASO), 2) AS TOTAL_HORAS_ATRASO_PONTO,
        ROUND(SUM(ISNULL(cf.HORAS_ATRASO_BANCO_ATUAL, 0)), 2) AS TOTAL_HORAS_ATRASO_BANCO,
        ROUND(SUM(cf.CUSTO_ESTIMADO_ATRASOS_PONTO), 2) AS TOTAL_CUSTO_ESTIMADO_ATRASOS_PONTO_R$,
        ROUND(SUM(cf.CUSTO_ESTIMADO_ATRASOS_BANCO), 2) AS TOTAL_CUSTO_ESTIMADO_ATRASOS_BANCO_R$,
    	ROUND(SUM(ISNULL(cf.VALOR_DESCONTADO_FOLHA, 0)), 2) AS VALOR_DESCONTADO_FOLHA_R$,
        ROW_NUMBER() OVER (
            PARTITION BY  cf.MES_ANO
            ORDER BY SUM(cf.HORAS_ATRASO) DESC
        ) AS RANKING
        
    FROM 
        ConsolidadoFuncionario cf
    WHERE
    	cf.REGIONAL <> 'NÃO CLASSIFICADO'
    GROUP BY 
        cf.MES_ANO,
        cf.CENTRO_CUSTO
        
)
SELECT 
    MES_ANO,
    RANKING,
    CENTRO_CUSTO,
    TOTAL_HORAS_ATRASO_PONTO,
    TOTAL_HORAS_ATRASO_BANCO,
    TOTAL_CUSTO_ESTIMADO_ATRASOS_PONTO_R$,
    TOTAL_CUSTO_ESTIMADO_ATRASOS_BANCO_R$,
    VALOR_DESCONTADO_FOLHA_R$
 
FROM 
    RankingCentrosCusto
WHERE 
    RANKING <= 5
ORDER BY 
    MES_ANO ASC, 
    RANKING ASC;

"""

}