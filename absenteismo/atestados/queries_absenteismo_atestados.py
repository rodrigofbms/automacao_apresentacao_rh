


SCRIPTS_SQL = {

    "atestados_por_mes": """


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
        
        -- Usado para remover o caractere "¶" chamado pilcrow que possui o Line feed e o Carriage Return basicamente ele volta pro início e pula uma linha,
    	-- identificado no SQL Server com o código CHAR(10) e CHAR(13), porque estava quebrando o arquivo em csv na hora da formatação
    	REPLACE(REPLACE(psecao.DESCRICAO, CHAR(13), ''), CHAR(10), '') AS NOME_CENTRO_CUSTO,
        ISNULL(ppessoa.SEXO, 'N/I') AS SEXO,
        ISNULL(pfunc.CODFUNCAO, 'N/I') AS CODFUNCAO,
        ISNULL(pfuncao.NOME, 'NÃO INFORMADO') AS NOME_FUNCAO,
        
        -- Cálculo de idade
        DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) - 
        CASE 
            WHEN DATEADD(YEAR, DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()), ppessoa.DTNASCIMENTO) > GETDATE() THEN 1 
            ELSE 0 
        END AS IDADE,

        -- Classificação por Faixa Etária
        CASE 
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) < 25 THEN 'Até 24 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 25 AND 34 THEN '25 a 34 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 35 AND 44 THEN '35 a 44 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 45 AND 54 THEN '45 a 54 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) >= 55 THEN '55+ anos'
            ELSE 'NÃO INFORMADO'
        END AS FAIXA_ETARIA,

        -- Regionalização
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
        
        CAST((pfunc.JORNADAMENSAL / 60.0) AS FLOAT) AS JORNADAMENSAL,
        CAST(pfunc.SALARIO AS FLOAT) AS SALARIO,
        
        CASE 
            WHEN ISNULL(pfunc.JORNADAMENSAL, 0) = 0 THEN 0
            ELSE CAST(pfunc.SALARIO AS FLOAT) / (pfunc.JORNADAMENSAL / 60.0)
        END AS VALOR_HORA,
        
        CAST(pfunc.DATAADMISSAO AS DATE) AS DATAADMISSAO,
        CAST(pfunc.DATADEMISSAO AS DATE) AS DATADEMISSAO
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
-- 3. MOVIMENTAÇÃO DE PONTO E MESES EXISTENTES
-- =========================================================================
MovimentoPonto AS (
    SELECT 
        aafhtfun.CODCOLIGADA,
        aafhtfun.CHAPA,
        FORMAT(aafhtfun.DATA, 'yyyy-MM') AS MES_ANO,
        CAST(DATEADD(MONTH, DATEDIFF(MONTH, 0, aafhtfun.DATA), 0) AS DATE) AS PRIMEIRO_DIA_MES,
        CAST(EOMONTH(aafhtfun.DATA) AS DATE) AS ULTIMO_DIA_MES,
        SUM(CAST(ISNULL(aafhtfun.FALTA, 0) AS FLOAT) / 60.0) AS HORAS_FALTA,
        SUM(CAST(ISNULL(aafhtfun.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO
    FROM 
        AAFHTFUN aafhtfun
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = aafhtfun.CODCOLIGADA
        AND fv.CHAPA = aafhtfun.CHAPA
    WHERE
        aafhtfun.CODCOLIGADA = 3
        AND aafhtfun.DATA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        aafhtfun.CODCOLIGADA,
        aafhtfun.CHAPA,
        FORMAT(aafhtfun.DATA, 'yyyy-MM'),
        CAST(DATEADD(MONTH, DATEDIFF(MONTH, 0, aafhtfun.DATA), 0) AS DATE),
        CAST(EOMONTH(aafhtfun.DATA) AS DATE)
),

MesesExistentes AS (
    SELECT DISTINCT 
        MES_ANO, 
        PRIMEIRO_DIA_MES, 
        ULTIMO_DIA_MES 
    FROM 
        MovimentoPonto
),

-- =========================================================================
-- 4. ABONOS DE ATESTADO (AABONOFUNCIONARIO) (EVENTO 001 DE ATESTADOS MÉDICOS)
-- =========================================================================
AbonosAtestado AS (
    SELECT 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM') AS MES_ANO,
        COUNT(abono.ID) AS QTD_ATESTADOS,
        SUM(
            CASE 
                WHEN abono.DATAHORAINICIO IS NOT NULL AND abono.DATAHORAFIM IS NOT NULL THEN
                    CAST(DATEDIFF(MINUTE, abono.DATAHORAINICIO, abono.DATAHORAFIM) AS FLOAT) / 60.0
                ELSE
                    CAST(ISNULL(abono.NUMHORAS, 0) AS FLOAT) / 60.0
            END
        ) AS HORAS_ATESTADO
    FROM 
        AABONOFUNCIONARIO abono
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = abono.CODCOLIGADA
        AND fv.CHAPA = abono.CHAPA
    WHERE 
        abono.CODCOLIGADA = 3
        -- Código de situação indicando que o registro está ativo
        AND abono.SITUACAO = '1'
        -- Código de abono referente a atestados médicos
        AND abono.CODABONO IN ('001')
        AND abono.DATAREFERENCIA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM')
),

-- =========================================================================
-- 5. FICHA FINANCEIRA - ATESTADOS EM FOLHA (EVENTO 0215)
-- =========================================================================
MovimentoFichaFinanceira AS (
    SELECT 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        CONCAT(pffin.ANOCOMP, '-', RIGHT(CONCAT('0', pffin.MESCOMP), 2)) AS MES_ANO,
        SUM(CAST(ISNULL(pffin.REF, 0) AS FLOAT)) AS HORAS_DESCONTADAS_FOLHA,
        SUM(CAST(ISNULL(pffin.VALOR, 0) AS FLOAT)) AS VALOR_DESCONTADO_FOLHA
    FROM 
        PFFINANC pffin
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = pffin.CODCOLIGADA
        AND fv.CHAPA = pffin.CHAPA
    WHERE 
        pffin.CODCOLIGADA = 3
        AND pffin.CODEVENTO IN ('0215')
        AND DATEFROMPARTS(pffin.ANOCOMP, pffin.MESCOMP, 1) BETWEEN @DataInicio AND DATEADD(MONTH, 1, @DataFim)
    GROUP BY 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        pffin.ANOCOMP,
        pffin.MESCOMP
),

-- =========================================================================
-- 8. DETALHAMENTO CONSOLIDADO POR FUNCIONÁRIO E MÊS
-- =========================================================================
ConsolidadoFuncionario AS (
    SELECT 
    	mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        fv.CHAPA,
        fv.NOME,
        fv.SEXO,
        fv.FAIXA_ETARIA,
        fv.NOME_FUNCAO,
        
        -- Cálculo estimado do valor das horas do atestado
        ISNULL(ab.HORAS_ATESTADO, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_ATESTADOS,
        
        -- Abonos de Atestado
        ISNULL(ab.QTD_ATESTADOS, 0) AS QTD_ATESTADOS,
        ISNULL(ab.HORAS_ATESTADO, 0) AS HORAS_ATESTADO,
        
        -- Ficha Financeira (Evento 0215)
        ISNULL(ff.HORAS_DESCONTADAS_FOLHA, 0) AS HORAS_DESCONTADAS_FOLHA,
        ISNULL(ff.VALOR_DESCONTADO_FOLHA, 0) AS VALOR_DESCONTADO_FOLHA
    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp ON mp.CODCOLIGADA = fv.CODCOLIGADA AND mp.CHAPA = fv.CHAPA
    LEFT JOIN AbonosAtestado ab ON ab.CODCOLIGADA = fv.CODCOLIGADA AND ab.CHAPA = fv.CHAPA AND ab.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoFichaFinanceira ff ON ff.CODCOLIGADA = fv.CODCOLIGADA AND ff.CHAPA = fv.CHAPA AND ff.MES_ANO = mp.MES_ANO
)

-- =========================================================================
-- BLOCO DE EXECUÇÃO: DAQUI PRA BAIXO É SO COMENTAR AS CTE QUE NÃO VÃO SER USADAS E EXECUTAR AS DE INTERESSE
-- =========================================================================

-- -------------------------------------------------------------------------
-- BLOCO 1: RESUMO MENSAL (Ponto, Atestados abonados e Folha) 
-- -------------------------------------------------------------------------


SELECT 
    cf.MES_ANO,
    ROUND(SUM(cf.HORAS_ATESTADO), 2) AS TOTAL_HORAS_ATESTADO,
    ROUND(SUM(cf.CUSTO_ESTIMADO_ATESTADOS), 2) AS TOTAL_CUSTO_ESTIMADO_ATESTADOS_R$,
    ROUND(SUM(cf.HORAS_DESCONTADAS_FOLHA), 2) AS TOTAL_HORAS_FOLHA,
    ROUND(SUM(cf.VALOR_DESCONTADO_FOLHA), 2) AS TOTAL_VALOR_DESCONTADO_FOLHA_R$
    
FROM 
    ConsolidadoFuncionario cf
GROUP BY 
    cf.MES_ANO
ORDER BY 
    cf.MES_ANO ASC;
    

""",


"top_5_atestados_por_centro_custo": """

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
        
        -- Usado para remover o caractere "¶" chamado pilcrow que possui o Line feed e o Carriage Return basicamente ele volta pro início e pula uma linha,
    	-- identificado no SQL Server com o código CHAR(10) e CHAR(13), porque estava quebrando o arquivo em csv na hora da formatação
    	REPLACE(REPLACE(psecao.DESCRICAO, CHAR(13), ''), CHAR(10), '') AS NOME_CENTRO_CUSTO,
        ISNULL(ppessoa.SEXO, 'N/I') AS SEXO,
        ISNULL(pfunc.CODFUNCAO, 'N/I') AS CODFUNCAO,
        ISNULL(pfuncao.NOME, 'NÃO INFORMADO') AS NOME_FUNCAO,
        
        -- Cálculo de idade
        DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) - 
        CASE 
            WHEN DATEADD(YEAR, DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()), ppessoa.DTNASCIMENTO) > GETDATE() THEN 1 
            ELSE 0 
        END AS IDADE,

        -- Classificação por Faixa Etária
        CASE 
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) < 25 THEN 'Até 24 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 25 AND 34 THEN '25 a 34 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 35 AND 44 THEN '35 a 44 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 45 AND 54 THEN '45 a 54 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) >= 55 THEN '55+ anos'
            ELSE 'NÃO INFORMADO'
        END AS FAIXA_ETARIA,

        -- Regionalização
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
        
        CAST((pfunc.JORNADAMENSAL / 60.0) AS FLOAT) AS JORNADAMENSAL,
        CAST(pfunc.SALARIO AS FLOAT) AS SALARIO,
        
        CASE 
            WHEN ISNULL(pfunc.JORNADAMENSAL, 0) = 0 THEN 0
            ELSE CAST(pfunc.SALARIO AS FLOAT) / (pfunc.JORNADAMENSAL / 60.0)
        END AS VALOR_HORA,
        
        CAST(pfunc.DATAADMISSAO AS DATE) AS DATAADMISSAO,
        CAST(pfunc.DATADEMISSAO AS DATE) AS DATADEMISSAO
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
-- 3. MOVIMENTAÇÃO DE PONTO E MESES EXISTENTES
-- =========================================================================
MovimentoPonto AS (
    SELECT 
        aafhtfun.CODCOLIGADA,
        aafhtfun.CHAPA,
        FORMAT(aafhtfun.DATA, 'yyyy-MM') AS MES_ANO,
        CAST(DATEADD(MONTH, DATEDIFF(MONTH, 0, aafhtfun.DATA), 0) AS DATE) AS PRIMEIRO_DIA_MES,
        CAST(EOMONTH(aafhtfun.DATA) AS DATE) AS ULTIMO_DIA_MES,
        SUM(CAST(ISNULL(aafhtfun.FALTA, 0) AS FLOAT) / 60.0) AS HORAS_FALTA,
        SUM(CAST(ISNULL(aafhtfun.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO
    FROM 
        AAFHTFUN aafhtfun
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = aafhtfun.CODCOLIGADA
        AND fv.CHAPA = aafhtfun.CHAPA
    WHERE
        aafhtfun.CODCOLIGADA = 3
        AND aafhtfun.DATA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        aafhtfun.CODCOLIGADA,
        aafhtfun.CHAPA,
        FORMAT(aafhtfun.DATA, 'yyyy-MM'),
        CAST(DATEADD(MONTH, DATEDIFF(MONTH, 0, aafhtfun.DATA), 0) AS DATE),
        CAST(EOMONTH(aafhtfun.DATA) AS DATE)
),

MesesExistentes AS (
    SELECT DISTINCT 
        MES_ANO, 
        PRIMEIRO_DIA_MES, 
        ULTIMO_DIA_MES 
    FROM 
        MovimentoPonto
),

-- =========================================================================
-- 4. ABONOS DE ATESTADO (AABONOFUNCIONARIO) (EVENTO 001 DE ATESTADOS MÉDICOS)
-- =========================================================================
AbonosAtestado AS (
    SELECT 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM') AS MES_ANO,
        COUNT(abono.ID) AS QTD_ATESTADOS,
        SUM(
            CASE 
                WHEN abono.DATAHORAINICIO IS NOT NULL AND abono.DATAHORAFIM IS NOT NULL THEN
                    CAST(DATEDIFF(MINUTE, abono.DATAHORAINICIO, abono.DATAHORAFIM) AS FLOAT) / 60.0
                ELSE
                    CAST(ISNULL(abono.NUMHORAS, 0) AS FLOAT) / 60.0
            END
        ) AS HORAS_ATESTADO
    FROM 
        AABONOFUNCIONARIO abono
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = abono.CODCOLIGADA
        AND fv.CHAPA = abono.CHAPA
    WHERE 
        abono.CODCOLIGADA = 3
        -- Código de situação indicando que o registro está ativo
        AND abono.SITUACAO = '1'
        -- Código de abono referente a atestados médicos
        AND abono.CODABONO IN ('001')
        AND abono.DATAREFERENCIA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM')
),

-- =========================================================================
-- 5. FICHA FINANCEIRA - ATESTADOS EM FOLHA (EVENTO 0215)
-- =========================================================================
MovimentoFichaFinanceira AS (
    SELECT 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        CONCAT(pffin.ANOCOMP, '-', RIGHT(CONCAT('0', pffin.MESCOMP), 2)) AS MES_ANO,
        SUM(CAST(ISNULL(pffin.REF, 0) AS FLOAT)) AS HORAS_DESCONTADAS_FOLHA,
        SUM(CAST(ISNULL(pffin.VALOR, 0) AS FLOAT)) AS VALOR_DESCONTADO_FOLHA
    FROM 
        PFFINANC pffin
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = pffin.CODCOLIGADA
        AND fv.CHAPA = pffin.CHAPA
    WHERE 
        pffin.CODCOLIGADA = 3
        AND pffin.CODEVENTO IN ('0215')
        AND DATEFROMPARTS(pffin.ANOCOMP, pffin.MESCOMP, 1) BETWEEN @DataInicio AND DATEADD(MONTH, 1, @DataFim)
    GROUP BY 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        pffin.ANOCOMP,
        pffin.MESCOMP
),

-- =========================================================================
-- 8. DETALHAMENTO CONSOLIDADO POR FUNCIONÁRIO E MÊS
-- =========================================================================
ConsolidadoFuncionario AS (
    SELECT 
    	mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        fv.CHAPA,
        fv.NOME,
        fv.SEXO,
        fv.FAIXA_ETARIA,
        fv.NOME_FUNCAO,
        
        -- Cálculo estimado do valor das horas do atestado
        ISNULL(ab.HORAS_ATESTADO, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_ATESTADOS,
        
        -- Abonos de Atestado
        ISNULL(ab.QTD_ATESTADOS, 0) AS QTD_ATESTADOS,
        ISNULL(ab.HORAS_ATESTADO, 0) AS HORAS_ATESTADO,
        
        -- Ficha Financeira (Evento 0215)
        ISNULL(ff.HORAS_DESCONTADAS_FOLHA, 0) AS HORAS_DESCONTADAS_FOLHA,
        ISNULL(ff.VALOR_DESCONTADO_FOLHA, 0) AS VALOR_DESCONTADO_FOLHA
    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp ON mp.CODCOLIGADA = fv.CODCOLIGADA AND mp.CHAPA = fv.CHAPA
    LEFT JOIN AbonosAtestado ab ON ab.CODCOLIGADA = fv.CODCOLIGADA AND ab.CHAPA = fv.CHAPA AND ab.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoFichaFinanceira ff ON ff.CODCOLIGADA = fv.CODCOLIGADA AND ff.CHAPA = fv.CHAPA AND ff.MES_ANO = mp.MES_ANO
)

-- =========================================================================
-- BLOCO DE EXECUÇÃO: DAQUI PRA BAIXO É SO COMENTAR AS CTE QUE NÃO VÃO SER USADAS E EXECUTAR AS DE INTERESSE
-- =========================================================================

-- -------------------------------------------------------------------------
-- BLOCO 2: TOP 5 CONTRATOS (CENTROS DE CUSTO) COM MAIOR HORAS DE ATESTADOS POR REGIONAL
-- -------------------------------------------------------------------------
,RankingContratos AS (
    SELECT 
    	cf.MES_ANO,
        cf.CENTRO_CUSTO,
        --SUM(cf.QTD_ATESTADOS) AS TOTAL_QTD_ATESTADOS,
        ROUND(SUM(cf.HORAS_ATESTADO), 2) AS TOTAL_HORAS_ATESTADO,
        ROUND(SUM(cf.HORAS_DESCONTADAS_FOLHA), 2) AS TOTAL_HORAS_ATESTADO_FOLHA,
        ROUND(SUM(cf.VALOR_DESCONTADO_FOLHA), 2) AS VALOR_TOTAL_ATESTADO_FOLHA_R$,
        ROW_NUMBER() OVER (PARTITION BY cf.MES_ANO ORDER BY SUM(cf.HORAS_ATESTADO) DESC) AS RANKING
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
    TOTAL_HORAS_ATESTADO,
    TOTAL_HORAS_ATESTADO_FOLHA,
    VALOR_TOTAL_ATESTADO_FOLHA_R$
FROM 
    RankingContratos
WHERE 
    RANKING <= 5
ORDER BY 
    MES_ANO, RANKING;

""",

"custo_atestados_por_mes": """


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
        
        -- Usado para remover o caractere "¶" chamado pilcrow que possui o Line feed e o Carriage Return basicamente ele volta pro início e pula uma linha,
    	-- identificado no SQL Server com o código CHAR(10) e CHAR(13), porque estava quebrando o arquivo em csv na hora da formatação
    	REPLACE(REPLACE(psecao.DESCRICAO, CHAR(13), ''), CHAR(10), '') AS NOME_CENTRO_CUSTO,
        ISNULL(ppessoa.SEXO, 'N/I') AS SEXO,
        ISNULL(pfunc.CODFUNCAO, 'N/I') AS CODFUNCAO,
        ISNULL(pfuncao.NOME, 'NÃO INFORMADO') AS NOME_FUNCAO,
        
        -- Cálculo de idade
        DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) - 
        CASE 
            WHEN DATEADD(YEAR, DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()), ppessoa.DTNASCIMENTO) > GETDATE() THEN 1 
            ELSE 0 
        END AS IDADE,

        -- Classificação por Faixa Etária
        CASE 
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) < 25 THEN 'Até 24 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 25 AND 34 THEN '25 a 34 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 35 AND 44 THEN '35 a 44 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 45 AND 54 THEN '45 a 54 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) >= 55 THEN '55+ anos'
            ELSE 'NÃO INFORMADO'
        END AS FAIXA_ETARIA,

        -- Regionalização
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
        
        CAST((pfunc.JORNADAMENSAL / 60.0) AS FLOAT) AS JORNADAMENSAL,
        CAST(pfunc.SALARIO AS FLOAT) AS SALARIO,
        
        CASE 
            WHEN ISNULL(pfunc.JORNADAMENSAL, 0) = 0 THEN 0
            ELSE CAST(pfunc.SALARIO AS FLOAT) / (pfunc.JORNADAMENSAL / 60.0)
        END AS VALOR_HORA,
        
        CAST(pfunc.DATAADMISSAO AS DATE) AS DATAADMISSAO,
        CAST(pfunc.DATADEMISSAO AS DATE) AS DATADEMISSAO
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
-- 3. MOVIMENTAÇÃO DE PONTO E MESES EXISTENTES
-- =========================================================================
MovimentoPonto AS (
    SELECT 
        aafhtfun.CODCOLIGADA,
        aafhtfun.CHAPA,
        FORMAT(aafhtfun.DATA, 'yyyy-MM') AS MES_ANO,
        CAST(DATEADD(MONTH, DATEDIFF(MONTH, 0, aafhtfun.DATA), 0) AS DATE) AS PRIMEIRO_DIA_MES,
        CAST(EOMONTH(aafhtfun.DATA) AS DATE) AS ULTIMO_DIA_MES,
        SUM(CAST(ISNULL(aafhtfun.FALTA, 0) AS FLOAT) / 60.0) AS HORAS_FALTA,
        SUM(CAST(ISNULL(aafhtfun.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO
    FROM 
        AAFHTFUN aafhtfun
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = aafhtfun.CODCOLIGADA
        AND fv.CHAPA = aafhtfun.CHAPA
    WHERE
        aafhtfun.CODCOLIGADA = 3
        AND aafhtfun.DATA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        aafhtfun.CODCOLIGADA,
        aafhtfun.CHAPA,
        FORMAT(aafhtfun.DATA, 'yyyy-MM'),
        CAST(DATEADD(MONTH, DATEDIFF(MONTH, 0, aafhtfun.DATA), 0) AS DATE),
        CAST(EOMONTH(aafhtfun.DATA) AS DATE)
),

MesesExistentes AS (
    SELECT DISTINCT 
        MES_ANO, 
        PRIMEIRO_DIA_MES, 
        ULTIMO_DIA_MES 
    FROM 
        MovimentoPonto
),

-- =========================================================================
-- 4. ABONOS DE ATESTADO (AABONOFUNCIONARIO) (EVENTO 001 DE ATESTADOS MÉDICOS)
-- =========================================================================
AbonosAtestado AS (
    SELECT 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM') AS MES_ANO,
        COUNT(abono.ID) AS QTD_ATESTADOS,
        SUM(
            CASE 
                WHEN abono.DATAHORAINICIO IS NOT NULL AND abono.DATAHORAFIM IS NOT NULL THEN
                    CAST(DATEDIFF(MINUTE, abono.DATAHORAINICIO, abono.DATAHORAFIM) AS FLOAT) / 60.0
                ELSE
                    CAST(ISNULL(abono.NUMHORAS, 0) AS FLOAT) / 60.0
            END
        ) AS HORAS_ATESTADO
    FROM 
        AABONOFUNCIONARIO abono
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = abono.CODCOLIGADA
        AND fv.CHAPA = abono.CHAPA
    WHERE 
        abono.CODCOLIGADA = 3
        -- Código de situação indicando que o registro está ativo
        AND abono.SITUACAO = '1'
        -- Código de abono referente a atestados médicos
        AND abono.CODABONO IN ('001')
        AND abono.DATAREFERENCIA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM')
),

-- =========================================================================
-- 5. FICHA FINANCEIRA - ATESTADOS EM FOLHA (EVENTO 0215)
-- =========================================================================
MovimentoFichaFinanceira AS (
    SELECT 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        CONCAT(pffin.ANOCOMP, '-', RIGHT(CONCAT('0', pffin.MESCOMP), 2)) AS MES_ANO,
        SUM(CAST(ISNULL(pffin.REF, 0) AS FLOAT)) AS HORAS_DESCONTADAS_FOLHA,
        SUM(CAST(ISNULL(pffin.VALOR, 0) AS FLOAT)) AS VALOR_DESCONTADO_FOLHA
    FROM 
        PFFINANC pffin
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = pffin.CODCOLIGADA
        AND fv.CHAPA = pffin.CHAPA
    WHERE 
        pffin.CODCOLIGADA = 3
        AND pffin.CODEVENTO IN ('0215')
        AND DATEFROMPARTS(pffin.ANOCOMP, pffin.MESCOMP, 1) BETWEEN @DataInicio AND DATEADD(MONTH, 1, @DataFim)
    GROUP BY 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        pffin.ANOCOMP,
        pffin.MESCOMP
),

-- =========================================================================
-- 8. DETALHAMENTO CONSOLIDADO POR FUNCIONÁRIO E MÊS
-- =========================================================================
ConsolidadoFuncionario AS (
    SELECT 
    	mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        fv.CHAPA,
        fv.NOME,
        fv.SEXO,
        fv.FAIXA_ETARIA,
        fv.NOME_FUNCAO,
        
        -- Cálculo estimado do valor das horas do atestado
        ISNULL(ab.HORAS_ATESTADO, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_ATESTADOS,
        
        -- Abonos de Atestado
        ISNULL(ab.QTD_ATESTADOS, 0) AS QTD_ATESTADOS,
        ISNULL(ab.HORAS_ATESTADO, 0) AS HORAS_ATESTADO,
        
        -- Ficha Financeira (Evento 0215)
        ISNULL(ff.HORAS_DESCONTADAS_FOLHA, 0) AS HORAS_DESCONTADAS_FOLHA,
        ISNULL(ff.VALOR_DESCONTADO_FOLHA, 0) AS VALOR_DESCONTADO_FOLHA
    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp ON mp.CODCOLIGADA = fv.CODCOLIGADA AND mp.CHAPA = fv.CHAPA
    LEFT JOIN AbonosAtestado ab ON ab.CODCOLIGADA = fv.CODCOLIGADA AND ab.CHAPA = fv.CHAPA AND ab.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoFichaFinanceira ff ON ff.CODCOLIGADA = fv.CODCOLIGADA AND ff.CHAPA = fv.CHAPA AND ff.MES_ANO = mp.MES_ANO
)

-- =========================================================================
-- BLOCO DE EXECUÇÃO: DAQUI PRA BAIXO É SO COMENTAR AS CTE QUE NÃO VÃO SER USADAS E EXECUTAR AS DE INTERESSE
-- =========================================================================

-- -------------------------------------------------------------------------
-- BLOCO 5: CUSTO DO ATESTADO MÉDICO DURANTE OS MESES (DESCONTO EM FOLHA)
-- -------------------------------------------------------------------------

SELECT
cf.MES_ANO,
ROUND(SUM(cf.VALOR_DESCONTADO_FOLHA), 2) AS VALOR_TOTAL_ATESTADO_FOLHA_R$
FROM ConsolidadoFuncionario cf
GROUP BY
cf.MES_ANO
ORDER BY
cf.MES_ANO ASC;


""",

"custo_atestados_por_centro_custo_e_mes": """

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
        
        -- Usado para remover o caractere "¶" chamado pilcrow que possui o Line feed e o Carriage Return basicamente ele volta pro início e pula uma linha,
    	-- identificado no SQL Server com o código CHAR(10) e CHAR(13), porque estava quebrando o arquivo em csv na hora da formatação
    	REPLACE(REPLACE(psecao.DESCRICAO, CHAR(13), ''), CHAR(10), '') AS NOME_CENTRO_CUSTO,
        ISNULL(ppessoa.SEXO, 'N/I') AS SEXO,
        ISNULL(pfunc.CODFUNCAO, 'N/I') AS CODFUNCAO,
        ISNULL(pfuncao.NOME, 'NÃO INFORMADO') AS NOME_FUNCAO,
        
        -- Cálculo de idade
        DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) - 
        CASE 
            WHEN DATEADD(YEAR, DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()), ppessoa.DTNASCIMENTO) > GETDATE() THEN 1 
            ELSE 0 
        END AS IDADE,

        -- Classificação por Faixa Etária
        CASE 
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) < 25 THEN 'Até 24 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 25 AND 34 THEN '25 a 34 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 35 AND 44 THEN '35 a 44 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) BETWEEN 45 AND 54 THEN '45 a 54 anos'
            WHEN DATEDIFF(YEAR, ppessoa.DTNASCIMENTO, GETDATE()) >= 55 THEN '55+ anos'
            ELSE 'NÃO INFORMADO'
        END AS FAIXA_ETARIA,

        -- Regionalização
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
        
        CAST((pfunc.JORNADAMENSAL / 60.0) AS FLOAT) AS JORNADAMENSAL,
        CAST(pfunc.SALARIO AS FLOAT) AS SALARIO,
        
        CASE 
            WHEN ISNULL(pfunc.JORNADAMENSAL, 0) = 0 THEN 0
            ELSE CAST(pfunc.SALARIO AS FLOAT) / (pfunc.JORNADAMENSAL / 60.0)
        END AS VALOR_HORA,
        
        CAST(pfunc.DATAADMISSAO AS DATE) AS DATAADMISSAO,
        CAST(pfunc.DATADEMISSAO AS DATE) AS DATADEMISSAO
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
-- 3. MOVIMENTAÇÃO DE PONTO E MESES EXISTENTES
-- =========================================================================
MovimentoPonto AS (
    SELECT 
        aafhtfun.CODCOLIGADA,
        aafhtfun.CHAPA,
        FORMAT(aafhtfun.DATA, 'yyyy-MM') AS MES_ANO,
        CAST(DATEADD(MONTH, DATEDIFF(MONTH, 0, aafhtfun.DATA), 0) AS DATE) AS PRIMEIRO_DIA_MES,
        CAST(EOMONTH(aafhtfun.DATA) AS DATE) AS ULTIMO_DIA_MES,
        SUM(CAST(ISNULL(aafhtfun.FALTA, 0) AS FLOAT) / 60.0) AS HORAS_FALTA,
        SUM(CAST(ISNULL(aafhtfun.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO
    FROM 
        AAFHTFUN aafhtfun
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = aafhtfun.CODCOLIGADA
        AND fv.CHAPA = aafhtfun.CHAPA
    WHERE
        aafhtfun.CODCOLIGADA = 3
        AND aafhtfun.DATA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        aafhtfun.CODCOLIGADA,
        aafhtfun.CHAPA,
        FORMAT(aafhtfun.DATA, 'yyyy-MM'),
        CAST(DATEADD(MONTH, DATEDIFF(MONTH, 0, aafhtfun.DATA), 0) AS DATE),
        CAST(EOMONTH(aafhtfun.DATA) AS DATE)
),

-- =========================================================================
-- 4. ABONOS DE ATESTADO (AABONOFUNCIONARIO) (EVENTO 001 DE ATESTADOS MÉDICOS)
-- =========================================================================
AbonosAtestado AS (
    SELECT 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM') AS MES_ANO,
        COUNT(abono.ID) AS QTD_ATESTADOS,
        SUM(
            CASE 
                WHEN abono.DATAHORAINICIO IS NOT NULL AND abono.DATAHORAFIM IS NOT NULL THEN
                    CAST(DATEDIFF(MINUTE, abono.DATAHORAINICIO, abono.DATAHORAFIM) AS FLOAT) / 60.0
                ELSE
                    CAST(ISNULL(abono.NUMHORAS, 0) AS FLOAT) / 60.0
            END
        ) AS HORAS_ATESTADO
    FROM 
        AABONOFUNCIONARIO abono
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = abono.CODCOLIGADA
        AND fv.CHAPA = abono.CHAPA
    WHERE 
        abono.CODCOLIGADA = 3
        -- Código de situação indicando que o registro está ativo
        AND abono.SITUACAO = '1'
        -- Código de abono referente a atestados médicos
        AND abono.CODABONO IN ('001')
        AND abono.DATAREFERENCIA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM')
),

-- =========================================================================
-- 5. FICHA FINANCEIRA - ATESTADOS EM FOLHA (EVENTO 0215)
-- =========================================================================
MovimentoFichaFinanceira AS (
    SELECT 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        CONCAT(pffin.ANOCOMP, '-', RIGHT(CONCAT('0', pffin.MESCOMP), 2)) AS MES_ANO,
        SUM(CAST(ISNULL(pffin.REF, 0) AS FLOAT)) AS HORAS_DESCONTADAS_FOLHA,
        SUM(CAST(ISNULL(pffin.VALOR, 0) AS FLOAT)) AS VALOR_DESCONTADO_FOLHA
    FROM 
        PFFINANC pffin
    INNER JOIN FuncionariosValidos fv
        ON fv.CODCOLIGADA = pffin.CODCOLIGADA
        AND fv.CHAPA = pffin.CHAPA
    WHERE 
        pffin.CODCOLIGADA = 3
        AND pffin.CODEVENTO IN ('0215')
        AND DATEFROMPARTS(pffin.ANOCOMP, pffin.MESCOMP, 1) BETWEEN @DataInicio AND DATEADD(MONTH, 1, @DataFim)
    GROUP BY 
        pffin.CODCOLIGADA,
        pffin.CHAPA,
        pffin.ANOCOMP,
        pffin.MESCOMP
),

-- =========================================================================
-- 8. DETALHAMENTO CONSOLIDADO POR FUNCIONÁRIO E MÊS
-- =========================================================================
ConsolidadoFuncionario AS (
    SELECT 
    	mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        fv.CHAPA,
        fv.NOME,
        fv.SEXO,
        fv.FAIXA_ETARIA,
        fv.NOME_FUNCAO,
        
        -- Cálculo estimado do valor das horas do atestado
        ISNULL(ab.HORAS_ATESTADO, 0) * fv.VALOR_HORA AS CUSTO_ESTIMADO_ATESTADOS,
        
        -- Abonos de Atestado
        ISNULL(ab.QTD_ATESTADOS, 0) AS QTD_ATESTADOS,
        ISNULL(ab.HORAS_ATESTADO, 0) AS HORAS_ATESTADO,
        
        -- Ficha Financeira (Evento 0215)
        ISNULL(ff.HORAS_DESCONTADAS_FOLHA, 0) AS HORAS_DESCONTADAS_FOLHA,
        ISNULL(ff.VALOR_DESCONTADO_FOLHA, 0) AS VALOR_DESCONTADO_FOLHA
    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp ON mp.CODCOLIGADA = fv.CODCOLIGADA AND mp.CHAPA = fv.CHAPA
    LEFT JOIN AbonosAtestado ab ON ab.CODCOLIGADA = fv.CODCOLIGADA AND ab.CHAPA = fv.CHAPA AND ab.MES_ANO = mp.MES_ANO
    LEFT JOIN MovimentoFichaFinanceira ff ON ff.CODCOLIGADA = fv.CODCOLIGADA AND ff.CHAPA = fv.CHAPA AND ff.MES_ANO = mp.MES_ANO
)

-- =========================================================================
-- BLOCO DE EXECUÇÃO: DAQUI PRA BAIXO É SO COMENTAR AS CTE QUE NÃO VÃO SER USADAS E EXECUTAR AS DE INTERESSE
-- =========================================================================

-- -------------------------------------------------------------------------
-- BLOCO 6: CUSTO DO ATESTADO MÉDICO POR CENTRO DE CUSTO (DESCONTO EM FOLHA)
-- -------------------------------------------------------------------------

SELECT
cf.MES_ANO,
cf.CENTRO_CUSTO,
ROUND(SUM(cf.VALOR_DESCONTADO_FOLHA), 2) AS VALOR_TOTAL_ATESTADO_FOLHA_R$

FROM ConsolidadoFuncionario cf

WHERE 
cf.VALOR_DESCONTADO_FOLHA > 0
AND cf.REGIONAL <> 'NÃO CLASSIFICADO'

GROUP BY
cf.MES_ANO,
cf.CENTRO_CUSTO

ORDER BY
cf.MES_ANO ASC,
VALOR_TOTAL_ATESTADO_FOLHA_R$ DESC;

"""

}