SCRIPTS_SQL = {

    "absenteismo_geral_por_mes": """

DECLARE @DataInicio DATE = ?;
DECLARE @DataFim    DATE = ?;

    WITH FuncionariosValidos AS (
    SELECT
        pfunc.CODCOLIGADA,
        pfunc.CHAPA,
        pfunc.NOME,
        psecao.NROCENCUSTOCONT AS CENTRO_CUSTO,
        psecao.DESCRICAO AS NOME_CENTRO_CUSTO,
        
        -- Mapeamento de Regionais
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
        
        CAST(pfunc.DATAADMISSAO AS DATE) AS DATAADMISSAO,
        CAST(pfunc.DATADEMISSAO AS DATE) AS DATADEMISSAO
    FROM 
        PFUNC pfunc
    INNER JOIN PSECAO psecao 
        ON psecao.CODCOLIGADA = pfunc.CODCOLIGADA 
        AND psecao.CODIGO = pfunc.CODSECAO
    WHERE 
        pfunc.CODCOLIGADA = 3
        AND pfunc.CHAPA NOT LIKE '%T%'
        AND pfunc.CODCATEGORIAESOCIAL NOT IN ('111', '701')
        -- Retira da contagem a filial da INVERNADA SP
        AND pfunc.CODFILIAL <> 10
),
-- =========================================================================
-- 3. MOVIMENTAÇÃO DE FALTAS E ATRASOS DO PONTO (AAFHTFUN)
-- =========================================================================

MovimentoPonto AS (
    SELECT 
        aafhtfun.CODCOLIGADA,
        aafhtfun.CHAPA,
        --COUNT(DISTINCT aafhtfun.CHAPA) AS QTD_FUNCIONARIOS,
        FORMAT(aafhtfun.DATA, 'yyyy-MM') AS MES_ANO,
        CAST(DATEADD(MONTH, DATEDIFF(MONTH, 0, aafhtfun.DATA), 0) AS DATE) AS PRIMEIRO_DIA_MES,
        CAST(EOMONTH(aafhtfun.DATA) AS DATE) AS ULTIMO_DIA_MES,
        SUM(CAST(ISNULL(aafhtfun.FALTA, 0) AS FLOAT) / 60.0) AS HORAS_FALTA,
        SUM(CAST(ISNULL(aafhtfun.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO,
         SUM(CAST(ISNULL(aafhtfun.BASE, 0) AS FLOAT) / 60.0) AS HORAS_MENSAIS
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

-- Extração dinâmica dos meses existentes no movimento de ponto
MesesExistentes AS (
    SELECT DISTINCT 
        MES_ANO, 
        PRIMEIRO_DIA_MES, 
        ULTIMO_DIA_MES 
    FROM 
        MovimentoPonto
),

-- =========================================================================
-- 4. MOVIMENTAÇÃO DE ATESTADOS MÉDICOS (AABONOFUNCIONARIO)
-- =========================================================================
AbonosAtestado AS (
    SELECT 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM') AS MES_ANO,
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
        AND abono.SITUACAO = '1' -- Registro Ativo
        AND abono.CODABONO IN ('001')
        AND abono.DATAREFERENCIA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM')
),

ConsolidadoFuncionario AS (
    SELECT 
    	mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        
        
        -- Ausências do Ponto
        SUM(ISNULL(mp.HORAS_FALTA, 0)) AS TOTAL_HORAS_FALTA,
        SUM(ISNULL(mp.HORAS_ATRASO, 0)) AS TOTAL_HORAS_ATRASO,
        SUM(ISNULL(mp.HORAS_MENSAIS, 0)) AS TOTAL_HORAS_MENSAIS,
        
        -- Horas de Atestado
        SUM(ISNULL(ab.HORAS_ATESTADO, 0)) AS TOTAL_HORAS_ATESTADO,
        
        -- Somatório das ausências
        (SUM(ISNULL(mp.HORAS_FALTA, 0)) + SUM(ISNULL(mp.HORAS_ATRASO, 0)) + SUM(ISNULL(ab.HORAS_ATESTADO, 0))) AS TOTAL_HORAS_AUSENTES

    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp 
        ON mp.CODCOLIGADA = fv.CODCOLIGADA 
        AND mp.CHAPA = fv.CHAPA
    LEFT JOIN AbonosAtestado ab 
        ON ab.CODCOLIGADA = fv.CODCOLIGADA 
        AND ab.CHAPA = fv.CHAPA 
        AND ab.MES_ANO = mp.MES_ANO
   GROUP BY 
   		mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO
        
)

-- =========================================================================
-- BLOCO DE EXECUÇÃO: DAQUI PRA BAIXO É SO COMENTAR AS CTE QUE NÃO VÃO SER USADAS E EXECUTAR AS DE INTERESSE
-- =========================================================================


----------------------------------------------------------------------------
-- BLOCO 1: TAXA DE ABSENTEÍSMO MENSAL POR MÊS
----------------------------------------------------------------------------


SELECT 
    cf.MES_ANO,

    ROUND(SUM(ISNULL(cf.TOTAL_HORAS_FALTA, 0)), 2) AS TOTAL_HORAS_FALTAS,
    ROUND(SUM(ISNULL(cf.TOTAL_HORAS_ATRASO, 0)), 2) AS TOTAL_HORAS_ATRASOS,
    ROUND(SUM(ISNULL(cf.TOTAL_HORAS_ATESTADO, 0)), 2) AS TOTAL_HORAS_ATESTADOS,
    ROUND(SUM(ISNULL(cf.TOTAL_HORAS_AUSENTES, 0)), 2) AS TOTAL_HORAS_AUSENTES,
        ROUND(SUM(ISNULL(cf.TOTAL_HORAS_MENSAIS, 0)), 2) AS TOTAL_HORAS_TRABALHADAS,
    
    ROUND(
        CASE 
            WHEN SUM(ISNULL(cf.TOTAL_HORAS_MENSAIS, 0)) = 0 THEN 0
            ELSE (SUM(ISNULL(cf.TOTAL_HORAS_AUSENTES, 0)) / SUM(cf.TOTAL_HORAS_MENSAIS)) * 100
        END, 2
    ) AS TAXA_ABSENTEISMO_PERC
FROM
    ConsolidadoFuncionario cf 
GROUP BY 
    cf.MES_ANO
ORDER BY 
    cf.MES_ANO ASC;
""",


"absenteismo_geral_por_regional": """


DECLARE @DataInicio DATE = ?;
DECLARE @DataFim    DATE = ?;

    WITH FuncionariosValidos AS (
    SELECT
        pfunc.CODCOLIGADA,
        pfunc.CHAPA,
        pfunc.NOME,
        psecao.NROCENCUSTOCONT AS CENTRO_CUSTO,
        psecao.DESCRICAO AS NOME_CENTRO_CUSTO,
        
        -- Mapeamento de Regionais
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
        
        CAST(pfunc.DATAADMISSAO AS DATE) AS DATAADMISSAO,
        CAST(pfunc.DATADEMISSAO AS DATE) AS DATADEMISSAO
    FROM 
        PFUNC pfunc
    INNER JOIN PSECAO psecao 
        ON psecao.CODCOLIGADA = pfunc.CODCOLIGADA 
        AND psecao.CODIGO = pfunc.CODSECAO
    WHERE 
        pfunc.CODCOLIGADA = 3
        AND pfunc.CHAPA NOT LIKE '%T%'
        AND pfunc.CODCATEGORIAESOCIAL NOT IN ('111', '701')
        -- Retira da contagem a filial da INVERNADA SP
        AND pfunc.CODFILIAL <> 10
),
-- =========================================================================
-- 3. MOVIMENTAÇÃO DE FALTAS E ATRASOS DO PONTO (AAFHTFUN)
-- =========================================================================

MovimentoPonto AS (
    SELECT 
        aafhtfun.CODCOLIGADA,
        aafhtfun.CHAPA,
        --COUNT(DISTINCT aafhtfun.CHAPA) AS QTD_FUNCIONARIOS,
        FORMAT(aafhtfun.DATA, 'yyyy-MM') AS MES_ANO,
        CAST(DATEADD(MONTH, DATEDIFF(MONTH, 0, aafhtfun.DATA), 0) AS DATE) AS PRIMEIRO_DIA_MES,
        CAST(EOMONTH(aafhtfun.DATA) AS DATE) AS ULTIMO_DIA_MES,
        SUM(CAST(ISNULL(aafhtfun.FALTA, 0) AS FLOAT) / 60.0) AS HORAS_FALTA,
        SUM(CAST(ISNULL(aafhtfun.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO,
         SUM(CAST(ISNULL(aafhtfun.BASE, 0) AS FLOAT) / 60.0) AS HORAS_MENSAIS
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

-- Extração dinâmica dos meses existentes no movimento de ponto
MesesExistentes AS (
    SELECT DISTINCT 
        MES_ANO, 
        PRIMEIRO_DIA_MES, 
        ULTIMO_DIA_MES 
    FROM 
        MovimentoPonto
),

-- =========================================================================
-- 4. MOVIMENTAÇÃO DE ATESTADOS MÉDICOS (AABONOFUNCIONARIO)
-- =========================================================================
AbonosAtestado AS (
    SELECT 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM') AS MES_ANO,
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
        AND abono.SITUACAO = '1' -- Registro Ativo
        AND abono.CODABONO IN ('001')
        AND abono.DATAREFERENCIA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM')
),

ConsolidadoFuncionario AS (
    SELECT 
    	mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        
        
        -- Ausências do Ponto
        SUM(ISNULL(mp.HORAS_FALTA, 0)) AS TOTAL_HORAS_FALTA,
        SUM(ISNULL(mp.HORAS_ATRASO, 0)) AS TOTAL_HORAS_ATRASO,
        SUM(ISNULL(mp.HORAS_MENSAIS, 0)) AS TOTAL_HORAS_MENSAIS,
        
        -- Horas de Atestado
        SUM(ISNULL(ab.HORAS_ATESTADO, 0)) AS TOTAL_HORAS_ATESTADO,
        
        -- Somatório das ausências
        (SUM(ISNULL(mp.HORAS_FALTA, 0)) + SUM(ISNULL(mp.HORAS_ATRASO, 0)) + SUM(ISNULL(ab.HORAS_ATESTADO, 0))) AS TOTAL_HORAS_AUSENTES

    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp 
        ON mp.CODCOLIGADA = fv.CODCOLIGADA 
        AND mp.CHAPA = fv.CHAPA
    LEFT JOIN AbonosAtestado ab 
        ON ab.CODCOLIGADA = fv.CODCOLIGADA 
        AND ab.CHAPA = fv.CHAPA 
        AND ab.MES_ANO = mp.MES_ANO
   GROUP BY 
   		mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO
        
)

-- =========================================================================
-- BLOCO DE EXECUÇÃO: DAQUI PRA BAIXO É SO COMENTAR AS CTE QUE NÃO VÃO SER USADAS E EXECUTAR AS DE INTERESSE
-- =========================================================================


----------------------------------------------------------------------------
-- BLOCO 2: TAXA DE ABSENTEÍSMO MENSAL POR REGIONAL
----------------------------------------------------------------------------

SELECT 
    cf.MES_ANO,
    cf.REGIONAL,

    ROUND(SUM(ISNULL(cf.TOTAL_HORAS_FALTA, 0)), 2) AS TOTAL_HORAS_FALTAS,
    ROUND(SUM(ISNULL(cf.TOTAL_HORAS_ATRASO, 0)), 2) AS TOTAL_HORAS_ATRASOS,
    ROUND(SUM(ISNULL(cf.TOTAL_HORAS_ATESTADO, 0)), 2) AS TOTAL_HORAS_ATESTADOS,
    ROUND(SUM(ISNULL(cf.TOTAL_HORAS_AUSENTES, 0)), 2) AS TOTAL_HORAS_AUSENTES,
        ROUND(SUM(ISNULL(cf.TOTAL_HORAS_MENSAIS, 0)), 2) AS TOTAL_HORAS_TRABALHADAS,
    
    ROUND(
        CASE 
            WHEN SUM(ISNULL(cf.TOTAL_HORAS_MENSAIS, 0)) = 0 THEN 0
            ELSE (SUM(ISNULL(cf.TOTAL_HORAS_AUSENTES, 0)) / SUM(cf.TOTAL_HORAS_MENSAIS)) * 100
        END, 2
    ) AS TAXA_ABSENTEISMO_PERC
    
FROM  
    ConsolidadoFuncionario cf 
GROUP BY 
    cf.MES_ANO,
    cf.REGIONAL
ORDER BY 
    cf.MES_ANO ASC,
    cf.REGIONAL ASC;

""", 


   "absenteismo_geral_por_contrato": """



DECLARE @DataInicio DATE = ?;
DECLARE @DataFim    DATE = ?;

    WITH FuncionariosValidos AS (
    SELECT
        pfunc.CODCOLIGADA,
        pfunc.CHAPA,
        pfunc.NOME,
        psecao.NROCENCUSTOCONT AS CENTRO_CUSTO,
        psecao.DESCRICAO AS NOME_CENTRO_CUSTO,
        
        -- Mapeamento de Regionais
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
        
        CAST(pfunc.DATAADMISSAO AS DATE) AS DATAADMISSAO,
        CAST(pfunc.DATADEMISSAO AS DATE) AS DATADEMISSAO
    FROM 
        PFUNC pfunc
    INNER JOIN PSECAO psecao 
        ON psecao.CODCOLIGADA = pfunc.CODCOLIGADA 
        AND psecao.CODIGO = pfunc.CODSECAO
    WHERE 
        pfunc.CODCOLIGADA = 3
        AND pfunc.CHAPA NOT LIKE '%T%'
        AND pfunc.CODCATEGORIAESOCIAL NOT IN ('111', '701')
        -- Retira da contagem a filial da INVERNADA SP
        AND pfunc.CODFILIAL <> 10
),
-- =========================================================================
-- 3. MOVIMENTAÇÃO DE FALTAS E ATRASOS DO PONTO (AAFHTFUN)
-- =========================================================================

MovimentoPonto AS (
    SELECT 
        aafhtfun.CODCOLIGADA,
        aafhtfun.CHAPA,
        --COUNT(DISTINCT aafhtfun.CHAPA) AS QTD_FUNCIONARIOS,
        FORMAT(aafhtfun.DATA, 'yyyy-MM') AS MES_ANO,
        CAST(DATEADD(MONTH, DATEDIFF(MONTH, 0, aafhtfun.DATA), 0) AS DATE) AS PRIMEIRO_DIA_MES,
        CAST(EOMONTH(aafhtfun.DATA) AS DATE) AS ULTIMO_DIA_MES,
        SUM(CAST(ISNULL(aafhtfun.FALTA, 0) AS FLOAT) / 60.0) AS HORAS_FALTA,
        SUM(CAST(ISNULL(aafhtfun.ATRASO, 0) AS FLOAT) / 60.0) AS HORAS_ATRASO,
         SUM(CAST(ISNULL(aafhtfun.BASE, 0) AS FLOAT) / 60.0) AS HORAS_MENSAIS
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

-- Extração dinâmica dos meses existentes no movimento de ponto
MesesExistentes AS (
    SELECT DISTINCT 
        MES_ANO, 
        PRIMEIRO_DIA_MES, 
        ULTIMO_DIA_MES 
    FROM 
        MovimentoPonto
),

-- =========================================================================
-- 4. MOVIMENTAÇÃO DE ATESTADOS MÉDICOS (AABONOFUNCIONARIO)
-- =========================================================================
AbonosAtestado AS (
    SELECT 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM') AS MES_ANO,
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
        AND abono.SITUACAO = '1' -- Registro Ativo
        AND abono.CODABONO IN ('001')
        AND abono.DATAREFERENCIA BETWEEN @DataInicio AND @DataFim
    GROUP BY 
        abono.CODCOLIGADA,
        abono.CHAPA,
        FORMAT(abono.DATAREFERENCIA, 'yyyy-MM')
),

ConsolidadoFuncionario AS (
    SELECT 
    	mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO,
        
        
        -- Ausências do Ponto
        SUM(ISNULL(mp.HORAS_FALTA, 0)) AS TOTAL_HORAS_FALTA,
        SUM(ISNULL(mp.HORAS_ATRASO, 0)) AS TOTAL_HORAS_ATRASO,
        SUM(ISNULL(mp.HORAS_MENSAIS, 0)) AS TOTAL_HORAS_MENSAIS,
        
        -- Horas de Atestado
        SUM(ISNULL(ab.HORAS_ATESTADO, 0)) AS TOTAL_HORAS_ATESTADO,
        
        -- Somatório das ausências
        (SUM(ISNULL(mp.HORAS_FALTA, 0)) + SUM(ISNULL(mp.HORAS_ATRASO, 0)) + SUM(ISNULL(ab.HORAS_ATESTADO, 0))) AS TOTAL_HORAS_AUSENTES

    FROM 
        FuncionariosValidos fv
    INNER JOIN MovimentoPonto mp 
        ON mp.CODCOLIGADA = fv.CODCOLIGADA 
        AND mp.CHAPA = fv.CHAPA
    LEFT JOIN AbonosAtestado ab 
        ON ab.CODCOLIGADA = fv.CODCOLIGADA 
        AND ab.CHAPA = fv.CHAPA 
        AND ab.MES_ANO = mp.MES_ANO
   GROUP BY 
   		mp.MES_ANO,
        fv.REGIONAL,
        fv.CENTRO_CUSTO,
        fv.NOME_CENTRO_CUSTO
        
)

-- =========================================================================
-- BLOCO DE EXECUÇÃO: DAQUI PRA BAIXO É SO COMENTAR AS CTE QUE NÃO VÃO SER USADAS E EXECUTAR AS DE INTERESSE
-- =========================================================================


----------------------------------------------------------------------------
-- BLOCO 3: TAXA DE ABSENTEÍSMO MENSAL POR CONTRATO / CENTRO DE CUSTO
----------------------------------------------------------------------------

SELECT 
    cf.MES_ANO,
    cf.REGIONAL,
    cf.CENTRO_CUSTO,
    cf.NOME_CENTRO_CUSTO,

    ROUND(ISNULL(cf.TOTAL_HORAS_FALTA, 0), 2) AS TOTAL_HORAS_FALTAS,
    ROUND(ISNULL(cf.TOTAL_HORAS_ATRASO, 0), 2) AS TOTAL_HORAS_ATRASOS,
    ROUND(ISNULL(cf.TOTAL_HORAS_ATESTADO, 0), 2) AS TOTAL_HORAS_ATESTADOS,
    ROUND(ISNULL(cf.TOTAL_HORAS_AUSENTES, 0), 2) AS TOTAL_HORAS_AUSENTES,
    ROUND(ISNULL(cf.TOTAL_HORAS_MENSAIS, 0), 2) AS TOTAL_HORAS_TRABALHADAS,
    
    ROUND(
        CASE 
            WHEN ISNULL(cf.TOTAL_HORAS_MENSAIS, 0) = 0 THEN 0
            ELSE (ISNULL(cf.TOTAL_HORAS_AUSENTES, 0) / ISNULL(cf.TOTAL_HORAS_MENSAIS, 0)) * 100
        END, 2
    ) AS TAXA_ABSENTEISMO_PERC
FROM 
    ConsolidadoFuncionario cf 
ORDER BY 
    cf.MES_ANO ASC,
    cf.REGIONAL ASC,
    cf.NOME_CENTRO_CUSTO ASC;

"""

}