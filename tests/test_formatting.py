import pytest

from eps_analytics.adaptadores import formato as fmt


def test_numero_y_cop_usan_la_convencion_colombiana():
    assert fmt.numero(1234567.891, 2) == "1.234.567,89"
    assert fmt.cop(1234567) == "$ 1.234.567"
    assert fmt.porcentaje(0.1234) == "12,3 %"


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (500, "$ 500"),
        (950_000, "$ 950 mil"),
        (85_300_000, "$ 85,3 M"),
        (1_500_000_000, "$ 1,50 MM"),
        # Justo debajo del cambio de unidad: el redondeo ya pertenece a la unidad siguiente.
        (999_600, "$ 1,0 M"),
        (999_960_000, "$ 1,00 MM"),
        (-999_960_000, "$ -1,00 MM"),
        # Sin redondear a la unidad siguiente, se queda en la propia.
        (999_400, "$ 999 mil"),
        (999_940_000, "$ 999,9 M"),
    ],
)
def test_cop_compacto(valor, esperado):
    assert fmt.cop_compacto(valor) == esperado
