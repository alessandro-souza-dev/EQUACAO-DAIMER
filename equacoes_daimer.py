from __future__ import annotations

from math import isfinite, log10


MIN_POSITIVE = 1e-6
MIN_H = 0.01
LOG20_FACTOR = log10(20)


def _as_float(value: float | int | str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if not text or text == "-":
            return default
        value = text
    result = float(value)
    if not isfinite(result):
        return default
    return result


def _log_margin(
    value: float,
    reference: float,
    higher_is_better: bool,
    floor: float = MIN_POSITIVE,
    log_base: float = 10.0,
) -> float:
    value = max(_as_float(value), floor)
    if higher_is_better:
        margin = log10(value / reference)
    else:
        margin = log10(reference / value)
    return margin / LOG20_FACTOR if log_base == 20.0 else margin


def _log20_threshold(threshold_log10: float) -> float:
    return threshold_log10 / LOG20_FACTOR


def _log20_coefficient(coefficient_log10: float) -> float:
    return coefficient_log10 * LOG20_FACTOR


def _hinge(threshold_margin: float, margin: float) -> float:
    return max(0.0, threshold_margin - margin)


def _margins(
    ip: float,
    delta_i: float,
    pi1_vn: float,
    pd: float,
    delta_tan_delta: float,
    tang_delta_h: float,
    tan_delta: float,
    h: float | str | None,
    log_base: float = 10.0,
) -> dict[str, float]:
    return {
        "ip": _log_margin(ip, 2.0, True, log_base=log_base),
        "delta_i": _log_margin(delta_i, 4.5, False, log_base=log_base),
        "pi1_vn": _log_margin(pi1_vn, 0.57, True, log_base=log_base),
        "pd": _log_margin(pd, 17000.0, False, log_base=log_base),
        "delta_tan_delta": _log_margin(delta_tan_delta, 1.0, False, log_base=log_base),
        "tang_delta_h": _log_margin(tang_delta_h, 0.05, False, log_base=log_base),
        "tan_delta": _log_margin(tan_delta, 4.0, False, log_base=log_base),
        "h": _log_margin(_as_float(h, 0.0), 7.0, False, MIN_H, log_base=log_base),
    }


def calcular_d10(
    ip: float,
    delta_i: float,
    pi1_vn: float,
    pd: float,
    delta_tan_delta: float,
    tang_delta_h: float,
    tan_delta: float,
    h: float | str | None = 0.0,
    arredondar: bool = True,
) -> float:
    m = _margins(ip, delta_i, pi1_vn, pd, delta_tan_delta, tang_delta_h, tan_delta, h)
    value = 0.48099133076674183
    value += 4.7352929414 * m["pi1_vn"]
    value += 2.0324724184 * _hinge(-0.187673132, m["pi1_vn"])
    value += -0.8935811025 * _hinge(0.0, m["tan_delta"])
    value += -0.8727027058 * _hinge(-0.477121255, m["tan_delta"])
    value += 0.7077394005 * m["pd"]
    value += 0.6615225327 * m["delta_i"]
    value += 0.5940052636 * m["delta_tan_delta"]
    value += -0.5846672503 * _hinge(-0.176091259, m["tan_delta"])
    value += 0.5503026270 * m["tang_delta_h"]
    value += 0.4195144391 * m["tan_delta"]
    value += 0.2327062135 * m["ip"]
    value += -0.0285128739 * _hinge(0.0, m["delta_tan_delta"])
    value += -0.0217847299 * _hinge(-1.0, m["tang_delta_h"])
    value += -0.0150712128 * _hinge(0.0, m["tang_delta_h"])
    return round(value, 2) if arredondar else value


def calcular_d20(
    ip: float,
    delta_i: float,
    pi1_vn: float,
    pd: float,
    delta_tan_delta: float,
    tang_delta_h: float,
    tan_delta: float,
    h: float | str | None = 0.0,
    arredondar: bool = True,
) -> float:
    m = _margins(ip, delta_i, pi1_vn, pd, delta_tan_delta, tang_delta_h, tan_delta, h, log_base=20.0)
    c = _log20_coefficient
    t = _log20_threshold
    value = 1.912812122382414
    value += c(-3.64695459) * m["pi1_vn"]
    value += c(-2.91109386) * _hinge(t(0.0), m["h"])
    value += c(-2.90494819) * _hinge(t(-0.552841969), m["h"])
    value += c(-1.48543788) * _hinge(t(-0.187673132), m["pi1_vn"])
    value += c(1.32150251) * m["ip"]
    value += c(-1.07687847) * _hinge(t(-0.330993219), m["h"])
    value += c(0.67088590) * m["tang_delta_h"]
    value += c(-0.50338589) * m["pd"]
    value += c(0.47363259) * m["delta_tan_delta"]
    value += c(0.26759780) * _hinge(t(0.0), m["ip"])
    value += c(-0.23319941) * _hinge(t(-0.602059991), m["delta_tan_delta"])
    value += c(0.19988613) * m["h"]
    value += c(0.18593911) * _hinge(t(-0.176091259), m["tan_delta"])
    value += c(0.16242290) * _hinge(t(-1.0), m["tang_delta_h"])
    value += c(0.07398838) * _hinge(t(0.0), m["tan_delta"])
    value += c(-0.02969294) * m["delta_i"]
    return round(value, 2) if arredondar else value


def calcular_avaliacao_global(
    ip: float,
    delta_i: float,
    pi1_vn: float,
    pd: float,
    delta_tan_delta: float,
    tang_delta_h: float,
    tan_delta: float,
    h: float | str | None = 0.0,
    arredondar: bool = True,
) -> float:
    d10 = calcular_d10(ip, delta_i, pi1_vn, pd, delta_tan_delta, tang_delta_h, tan_delta, h, False)
    d20 = calcular_d20(ip, delta_i, pi1_vn, pd, delta_tan_delta, tang_delta_h, tan_delta, h, False)
    value = d10 + d20
    return round(value, 2) if arredondar else value


def calcular_gei(
    ip: float,
    delta_i: float,
    pi1_vn: float,
    pd: float,
    delta_tan_delta: float,
    tang_delta_h: float,
    tan_delta: float,
    h: float | str | None = 0.0,
    tempo_operacao_anos: float | None = None,
    ajuste_historico_anos: float = 0.0,
    arredondar: bool = True,
) -> float | int:
    m = _margins(ip, delta_i, pi1_vn, pd, delta_tan_delta, tang_delta_h, tan_delta, h)
    value = 16.13934061640554
    value += -1.106626217754 * m["ip"]
    value += -1.434426266083 * m["delta_i"]
    value += -13.755033142952 * m["pi1_vn"]
    value += -3.159764396046 * m["pd"]
    value += -1.218023115611 * m["delta_tan_delta"]
    value += -1.256581659707 * m["tang_delta_h"]
    value += -6.287254258221 * m["tan_delta"]
    value += -0.110647689724 * m["h"]
    value += ajuste_historico_anos
    if tempo_operacao_anos is not None:
        value = min(value, _as_float(tempo_operacao_anos, value))
    value = max(0.0, value)
    return int(round(value)) if arredondar else value
