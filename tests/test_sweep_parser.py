import pytest

from src.sweep_parser import check_sweep, parse_sweep_csv

BASIC = "Frequency_Hz,S11_dB\n100000000,-1.0\n200000000,-12.5\n300000000,-2.0\n"


def test_parses_required_columns_into_mhz() -> None:
    sweep = parse_sweep_csv(BASIC)

    assert sweep.f_mhz == (100.0, 200.0, 300.0)
    assert sweep.s11_db == (-1.0, -12.5, -2.0)
    assert sweep.gamma is None


def test_parses_optional_complex_columns() -> None:
    text = (
        "Frequency_Hz,S11_dB,S11_real,S11_imag\n"
        "100000000,-1.0,0.5,-0.25\n"
        "200000000,-12.5,0.1,0.2\n"
        "300000000,-2.0,-0.3,0.0\n"
    )

    sweep = parse_sweep_csv(text)

    assert sweep.gamma == (complex(0.5, -0.25), complex(0.1, 0.2), complex(-0.3, 0.0))


def test_ignores_other_columns_bom_and_blank_lines() -> None:
    text = (
        "﻿Note, Frequency_Hz ,S11_dB,Phase\n"
        "a,100000000,-1.0,10\n"
        "\n"
        "b,200000000,-12.5,20\n"
        "c,300000000,-2.0,30\n"
    )

    sweep = parse_sweep_csv(text)

    assert sweep.f_mhz == (100.0, 200.0, 300.0)
    assert sweep.gamma is None


def test_only_one_complex_column_means_no_complex() -> None:
    text = "Frequency_Hz,S11_dB,S11_real\n1e8,-1,0.5\n2e8,-2,0.4\n3e8,-3,0.3\n"

    assert parse_sweep_csv(text).gamma is None


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "비어"),
        ("Freq,S11_dB\n1e8,-1\n2e8,-2\n3e8,-3\n", "Frequency_Hz"),
        ("Frequency_Hz,Gain\n1e8,-1\n2e8,-2\n3e8,-3\n", "S11_dB"),
        ("Frequency_Hz,S11_dB\n1e8,-1\n2e8,-2\n", "3점"),
        ("Frequency_Hz,S11_dB\n1e8,-1\n3e8,-2\n2e8,-3\n", "오름차순"),
        ("Frequency_Hz,S11_dB\n1e8,-1\n1e8,-2\n2e8,-3\n", "오름차순"),
        ("Frequency_Hz,S11_dB\n1e8,-1\n2e8,nan\n3e8,-3\n", "3행"),
        ("Frequency_Hz,S11_dB\n1e8,-1\n2e8,-2\n3e8,inf\n", "유한"),
        ("Frequency_Hz,S11_dB\n1e8,-1\n2e8,abc\n3e8,-3\n", "숫자"),
        ("Frequency_Hz,S11_dB\n1e8,-1\n2e8\n3e8,-3\n", "숫자"),
        ("Frequency_Hz,S11_dB,S11_real,S11_imag\n1e8,-1,0.1,0.1\n2e8,-2,x,0\n3e8,-3,0,0\n", "숫자"),
    ],
)
def test_rejects_bad_input_with_korean_message(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_sweep_csv(text)


COMPLEX_HEADER = "Frequency_Hz,S11_dB,S11_real,S11_imag\n"


@pytest.mark.parametrize(
    ("row", "column"),
    [
        ("0,-2,0,0", "Frequency_Hz"),
        ("-1e8,-2,0,0", "Frequency_Hz"),
        ("0.999,-2,0,0", "Frequency_Hz"),
        ("1.000001e12,-2,0,0", "Frequency_Hz"),
        ("2e8,1000.001,0,0", "S11_dB"),
        ("2e8,-1000.001,0,0", "S11_dB"),
        ("2e8,-2,1000.001,0", "S11_real"),
        ("2e8,-2,0,-1000.001", "S11_imag"),
    ],
)
def test_rejects_values_outside_the_measurable_range(row: str, column: str) -> None:
    text = COMPLEX_HEADER + f"1e8,-1,0,0\n{row}\n3e8,-3,0,0\n"

    with pytest.raises(ValueError, match=f"3행: {column} .*범위"):
        parse_sweep_csv(text)


def test_accepts_values_on_the_range_limits() -> None:
    text = COMPLEX_HEADER + "1,1000,1000,-1000\n2,-1000,-1000,1000\n1e12,0,0,0\n"

    sweep = parse_sweep_csv(text)

    assert (sweep.f_mhz[0], sweep.f_mhz[-1]) == (1e-6, 1e6)
    check_sweep(sweep)  # the service runs both; a parsed sweep must pass the shared check


@pytest.mark.parametrize("newline", ["\r\n", "\r"])
def test_accepts_other_line_endings(newline: str) -> None:
    sweep = parse_sweep_csv(BASIC.replace("\n", newline))

    assert sweep.f_mhz == (100.0, 200.0, 300.0)


def test_rows_with_only_delimiters_are_skipped_like_blank_lines() -> None:
    text = "Frequency_Hz,S11_dB\n1e8,-1\n,\n2e8,-2\n3e8,-3\n,\n"

    assert parse_sweep_csv(text).f_mhz == (100.0, 200.0, 300.0)


def test_unterminated_quote_is_rejected_instead_of_swallowing_rows() -> None:
    text = 'Frequency_Hz,S11_dB,Note\n1e8,-1,a\n2e8,-2,b\n3e8,-3,"c\n4e8,-4,d\n5e8,-5,e\n'

    with pytest.raises(ValueError, match="형식"):
        parse_sweep_csv(text)


@pytest.mark.parametrize("name", ["Frequency_Hz", "S11_dB", "S11_real", "S11_imag"])
def test_duplicate_recognised_header_is_rejected(name: str) -> None:
    header = f"Frequency_Hz,S11_dB,S11_real,S11_imag, {name} "
    text = header + "\n1e8,-1,0,0,9\n2e8,-2,0,0,9\n3e8,-3,0,0,9\n"

    with pytest.raises(ValueError, match=f"{name} 열이 두 번"):
        parse_sweep_csv(text)


def test_duplicate_ignored_header_is_fine() -> None:
    text = "Frequency_Hz,S11_dB,Note,Note\n1e8,-1,a,b\n2e8,-2,a,b\n3e8,-3,a,b\n"

    assert parse_sweep_csv(text).s11_db == (-1.0, -2.0, -3.0)
