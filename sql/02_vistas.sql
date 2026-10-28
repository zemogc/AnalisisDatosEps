/* =====================================================================
   ProyectoEPS - Vistas analíticas (SQL Server)
   ===================================================================== */

USE ProyectoEPS;
GO

/* Una fila por consulta con el costo de medicamentos ya agregado.
   Evita el error clásico de unir Medicamentos directamente, que repite
   el costo de la consulta por cada medicamento formulado. */
CREATE OR ALTER VIEW dbo.vw_CostoConsulta AS
SELECT
    c.ID_Consulta,
    p.ID_Paciente,
    p.EPS,
    p.Regimen,
    p.Ciudad,
    p.Sexo,
    p.Edad,
    c.Fecha_Consulta,
    c.Tipo_Atencion,
    c.Codigo_CIE10,
    c.Diagnostico,
    c.Costo                                    AS Costo_Consulta,
    COALESCE(m.Costo_Medicamentos, 0)          AS Costo_Medicamentos,
    c.Costo + COALESCE(m.Costo_Medicamentos, 0) AS Costo_Total
FROM dbo.ConsultasMedicas c
INNER JOIN dbo.Pacientes p ON p.ID_Paciente = c.ID_Paciente
LEFT JOIN (
    SELECT ID_Consulta, SUM(Costo) AS Costo_Medicamentos
    FROM dbo.Medicamentos
    GROUP BY ID_Consulta
) m ON m.ID_Consulta = c.ID_Consulta;
GO

CREATE OR ALTER VIEW dbo.vw_ResumenEPS AS
SELECT
    EPS,
    COUNT(DISTINCT ID_Paciente)                              AS Pacientes,
    COUNT(*)                                                 AS Consultas,
    SUM(Costo_Total)                                         AS Costo_Total,
    AVG(Costo_Total)                                         AS Costo_Promedio_Consulta,
    SUM(Costo_Total) / NULLIF(COUNT(DISTINCT ID_Paciente), 0) AS Costo_Por_Paciente
FROM dbo.vw_CostoConsulta
GROUP BY EPS;
GO
