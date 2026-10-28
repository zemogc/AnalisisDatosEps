/* =====================================================================
   ProyectoEPS - Consultas analíticas de referencia (SQL Server)
   ===================================================================== */

USE ProyectoEPS;
GO

-- 1. Ranking de diagnósticos por costo total con participación acumulada (Pareto)
WITH costo_dx AS (
    SELECT Diagnostico, SUM(Costo_Total) AS Costo_Total
    FROM dbo.vw_CostoConsulta
    GROUP BY Diagnostico
)
SELECT
    Diagnostico,
    Costo_Total,
    CAST(100.0 * Costo_Total / SUM(Costo_Total) OVER () AS DECIMAL(5, 2)) AS Participacion_Pct,
    CAST(100.0 * SUM(Costo_Total) OVER (ORDER BY Costo_Total DESC ROWS UNBOUNDED PRECEDING)
         / SUM(Costo_Total) OVER () AS DECIMAL(5, 2))                     AS Acumulado_Pct
FROM costo_dx
ORDER BY Costo_Total DESC;

-- 2. Tendencia mensual con variación frente al mes anterior
WITH mensual AS (
    SELECT DATEFROMPARTS(YEAR(Fecha_Consulta), MONTH(Fecha_Consulta), 1) AS Mes,
           COUNT(*)         AS Consultas,
           SUM(Costo_Total) AS Costo_Total
    FROM dbo.vw_CostoConsulta
    GROUP BY DATEFROMPARTS(YEAR(Fecha_Consulta), MONTH(Fecha_Consulta), 1)
)
SELECT Mes, Consultas, Costo_Total,
       CAST(100.0 * (Costo_Total - LAG(Costo_Total) OVER (ORDER BY Mes))
            / NULLIF(LAG(Costo_Total) OVER (ORDER BY Mes), 0) AS DECIMAL(6, 2)) AS Variacion_Pct
FROM mensual
ORDER BY Mes;

-- 3. Pacientes de alto costo: top 1 % por gasto acumulado
WITH gasto AS (
    SELECT ID_Paciente, EPS, SUM(Costo_Total) AS Gasto_Total, COUNT(*) AS Consultas
    FROM dbo.vw_CostoConsulta
    GROUP BY ID_Paciente, EPS
)
SELECT TOP 1 PERCENT *
FROM gasto
ORDER BY Gasto_Total DESC;

-- 4. Medicamentos más formulados por EPS
SELECT p.EPS, m.Nombre_Medicamento, COUNT(*) AS Formulaciones, SUM(m.Costo) AS Costo_Total
FROM dbo.Medicamentos m
INNER JOIN dbo.ConsultasMedicas c ON c.ID_Consulta = m.ID_Consulta
INNER JOIN dbo.Pacientes p ON p.ID_Paciente = c.ID_Paciente
GROUP BY p.EPS, m.Nombre_Medicamento
ORDER BY p.EPS, Formulaciones DESC;
