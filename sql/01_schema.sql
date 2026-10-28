/* =====================================================================
   ProyectoEPS - Esquema relacional (SQL Server)
   Ejecutar en SSMS o con: sqlcmd -S localhost -E -i sql/01_schema.sql
   ===================================================================== */

IF DB_ID('ProyectoEPS') IS NULL
    CREATE DATABASE ProyectoEPS;
GO

USE ProyectoEPS;
GO

IF OBJECT_ID('dbo.Medicamentos', 'U') IS NOT NULL DROP TABLE dbo.Medicamentos;
IF OBJECT_ID('dbo.ConsultasMedicas', 'U') IS NOT NULL DROP TABLE dbo.ConsultasMedicas;
IF OBJECT_ID('dbo.Pacientes', 'U') IS NOT NULL DROP TABLE dbo.Pacientes;
GO

CREATE TABLE dbo.Pacientes (
    ID_Paciente  INT           NOT NULL CONSTRAINT PK_Pacientes PRIMARY KEY,
    Nombre       NVARCHAR(120) NOT NULL,
    Edad         INT           NOT NULL CONSTRAINT CK_Pacientes_Edad CHECK (Edad BETWEEN 0 AND 120),
    Sexo         CHAR(1)       NOT NULL CONSTRAINT CK_Pacientes_Sexo CHECK (Sexo IN ('F', 'M')),
    EPS          NVARCHAR(60)  NOT NULL,
    Regimen      NVARCHAR(20)  NOT NULL CONSTRAINT CK_Pacientes_Regimen CHECK (Regimen IN ('Contributivo', 'Subsidiado')),
    Ciudad       NVARCHAR(60)  NOT NULL
);

CREATE TABLE dbo.ConsultasMedicas (
    ID_Consulta     INT            NOT NULL CONSTRAINT PK_ConsultasMedicas PRIMARY KEY,
    ID_Paciente     INT            NOT NULL CONSTRAINT FK_Consultas_Pacientes REFERENCES dbo.Pacientes (ID_Paciente),
    Fecha_Consulta  DATE           NOT NULL,
    Tipo_Atencion   NVARCHAR(30)   NOT NULL,
    Codigo_CIE10    VARCHAR(10)    NOT NULL,
    Diagnostico     NVARCHAR(120)  NOT NULL,
    Costo           DECIMAL(14, 2) NOT NULL CONSTRAINT CK_Consultas_Costo CHECK (Costo >= 0)
);

CREATE TABLE dbo.Medicamentos (
    ID_Medicamento      INT            NOT NULL CONSTRAINT PK_Medicamentos PRIMARY KEY,
    ID_Consulta         INT            NOT NULL CONSTRAINT FK_Medicamentos_Consultas REFERENCES dbo.ConsultasMedicas (ID_Consulta),
    Nombre_Medicamento  NVARCHAR(120)  NOT NULL,
    Cantidad            INT            NOT NULL CONSTRAINT CK_Medicamentos_Cantidad CHECK (Cantidad > 0),
    Costo               DECIMAL(14, 2) NOT NULL CONSTRAINT CK_Medicamentos_Costo CHECK (Costo >= 0)
);
GO

-- Índices para los JOIN y filtros más frecuentes del análisis
CREATE INDEX IX_Consultas_Paciente ON dbo.ConsultasMedicas (ID_Paciente);
CREATE INDEX IX_Consultas_Fecha    ON dbo.ConsultasMedicas (Fecha_Consulta) INCLUDE (Costo, Codigo_CIE10);
CREATE INDEX IX_Medicamentos_Consulta ON dbo.Medicamentos (ID_Consulta) INCLUDE (Costo);
CREATE INDEX IX_Pacientes_EPS      ON dbo.Pacientes (EPS);
GO
