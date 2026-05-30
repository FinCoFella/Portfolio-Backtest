from pathlib import Path
import pandas as pd
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable, KeepTogether, PageBreak, Image,
)

from src.metrics import returns  as ret_metrics
from src.metrics import risk     as risk_metrics
from src.metrics import ratios   as ratio_metrics
from src.metrics import relative as rel_metrics
from src.portfolio import portfolio as port_module

# ── Palette ───────────────────────────────────────────────────────────────────
_NAVY      = colors.HexColor("#1F3864")
_ROW_ALT   = colors.HexColor("#F2F2F2")
_BORDER    = colors.HexColor("#CCCCCC")
_INNER     = colors.HexColor("#E0E0E0")
_WHITE     = colors.white
_BLACK     = colors.HexColor("#1A1A1A")

# ── Column label map (mirrors backtest.py) ────────────────────────────────────
_LABELS = {
    "total_return":          "Total Return",
    "cagr":                  "CAGR",
    "annualized_return":     "Annualized Return",
    "annualized_volatility": "Annualized Volatility",
    "std_dev_annualized":    "Std Dev (Ann.)",
    "max_drawdown":          "Max Drawdown",
    "var_95_daily":          "VaR 95% Daily",
    "es_95_daily":           "ES 95% Daily",
    "sharpe":                "Sharpe",
    "sortino":               "Sortino",
    "beta":                  "Beta",
    "alpha":                 "Alpha",
    "treynor":               "Treynor",
    "excess_return":         "Excess Return",
    "tracking_error":        "Tracking Error",
    "information_ratio":     "Information Ratio",
}

_TICKER_DISPLAY = {"^GSPC": "S&P 500", "^DJI": "Dow Jones", "^IXIC": "NASDAQ"}

def _lbl(col):   return _LABELS.get(col, col.replace("_", " ").title())
def _disp(ticker): return _TICKER_DISPLAY.get(ticker, ticker)


# ── Table builders ────────────────────────────────────────────────────────────

_TABLE_STYLE = [
    ("BACKGROUND",    (0, 0), (-1, 0),  _NAVY),
    ("TEXTCOLOR",     (0, 0), (-1, 0),  _WHITE),
    ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
    ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE",      (0, 0), (-1, -1), 8),
    ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_WHITE, _ROW_ALT]),
    ("LINEBELOW",     (0, 0), (-1, 0),  0.5, _WHITE),
    ("INNERGRID",     (0, 1), (-1, -1), 0.3, _INNER),
    ("BOX",           (0, 0), (-1, -1), 0.5, _BORDER),
    ("TOPPADDING",    (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING",   (0, 0), (-1, -1), 5),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
]


def _df_table(df: pd.DataFrame, pct_cols: set, width: float) -> Table:
    """DataFrame (index + columns) → styled Table, fitting within `width` pts."""
    display = df.copy().astype(object)
    for col in display.columns:
        if col in pct_cols:
            display[col] = display[col].map(
                lambda x: f"{x:.2%}" if isinstance(x, float) else x
            )
        else:
            display[col] = display[col].map(
                lambda x: f"{x:.4f}" if isinstance(x, float) else x
            )
    display.columns = [_lbl(c) for c in display.columns]
    index_name = _lbl(df.index.name) if df.index.name else "Ticker"
    headers = [index_name] + list(display.columns)
    rows    = [[str(idx)] + list(row) for idx, row in display.iterrows()]
    data    = [headers] + rows
    n       = len(headers)
    col_w   = [width / n] * n
    tbl = Table(data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle(_TABLE_STYLE))
    return tbl


def _kv_table(rows: list[tuple], width: float) -> Table:
    """Two-column (Metric | Value) key-value table."""
    data = [["Metric", "Value"]] + list(rows)
    col_w = [width * 0.62, width * 0.38]
    tbl = Table(data, colWidths=col_w, repeatRows=1)
    style = list(_TABLE_STYLE)
    style.append(("ALIGN", (0, 1), (0, -1), "LEFT"))
    tbl.setStyle(TableStyle(style))
    return tbl


def _pricing_table(price_data: dict, rows: int, width: float) -> Table:
    """Date × Ticker adjusted-close table (last `rows` trading days)."""
    closes = pd.DataFrame(
        {_disp(t): df["adj_close"] for t, df in price_data.items()}
    ).tail(rows)
    closes.index = closes.index.strftime("%Y-%m-%d")
    headers = ["Date"] + list(closes.columns)
    data    = [headers] + [
        [str(idx)] + [f"{v:,.2f}" for v in row]
        for idx, row in closes.iterrows()
    ]
    n     = len(headers)
    col_w = [width / n] * n
    tbl   = Table(data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle(_TABLE_STYLE))
    return tbl


# ── Style helpers ─────────────────────────────────────────────────────────────

def _section(text: str) -> Paragraph:
    style = ParagraphStyle(
        "section",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=_NAVY,
        spaceAfter=4,
        spaceBefore=10,
    )
    return Paragraph(text, style)


def _side_by_side(left: Table, right: Table, width: float, gap: float = 12) -> Table:
    """Wrap two tables into a single two-column layout table."""
    half = (width - gap) / 2
    # Re-scale each sub-table to half width
    left._argW  = [half / sum(left._argW)  * w for w in left._argW]  if left._argW  else None
    right._argW = [half / sum(right._argW) * w for w in right._argW] if right._argW else None
    wrapper = Table([[left, right]], colWidths=[half, half])
    wrapper.setStyle(TableStyle([
        ("VALIGN",  (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
        ("ALIGN",        (1, 0), (1, -1), "RIGHT"),
    ]))
    return wrapper


# ── Main export function ──────────────────────────────────────────────────────

def export_tearsheet(
    price_data: dict[str, pd.DataFrame],
    ticker_data: dict[str, pd.DataFrame],
    portfolio_returns: pd.Series,
    weights: dict[str, float],
    benchmark_ticker: str | None,
    risk_free_rate: float,
    start_date: str,
    end_date: str,
    output_dir: Path,
    confidence: float = 0.95,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tickers      = list(ticker_data.keys())
    bench_disp   = _disp(benchmark_ticker) if benchmark_ticker else "N/A"
    ticker_str   = ", ".join(tickers)

    # Include benchmark in per-ticker comparison tables (excluding relative metrics)
    comparison_data = dict(ticker_data)
    if benchmark_ticker and benchmark_ticker in price_data:
        comparison_data[bench_disp] = price_data[benchmark_ticker]
    filename     = f"Tearsheet_{start_date}_to_{end_date}.pdf"
    filepath     = output_dir / filename

    PAGE_W, PAGE_H = landscape(letter)
    MARGIN = 0.6 * inch
    WIDTH  = PAGE_W - 2 * MARGIN

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=landscape(letter),
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
    )

    title_style = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=16,
        textColor=_NAVY, alignment=TA_CENTER, spaceAfter=0,
    )
    sub_style = ParagraphStyle(
        "sub", fontName="Helvetica", fontSize=9,
        textColor=_BLACK, alignment=TA_CENTER, spaceAfter=0,
    )

    story = []

    # ── Title block ───────────────────────────────────────────────────────────
    bench_disp_xml = bench_disp.replace("&", "&amp;")
    story.append(Paragraph("Portfolio Backtesting Tearsheet", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Period: {start_date} &nbsp;→&nbsp; {end_date}", sub_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Tickers: {ticker_str} &nbsp;|&nbsp; Benchmark: {bench_disp_xml} &nbsp;|&nbsp; Risk-Free Rate: {risk_free_rate:.2%}", sub_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_NAVY, spaceAfter=10))

    # ── Pricing table ─────────────────────────────────────────────────────────
    story.append(_section("Adjusted Closing Prices (Last 10 Trading Days)"))
    story.append(_pricing_table(price_data, rows=10, width=WIDTH))
    story.append(Spacer(1, 10))

    # ── Per-ticker metrics ────────────────────────────────────────────────────
    ret_sum  = ret_metrics.summary(comparison_data)
    risk_sum = risk_metrics.summary(comparison_data, confidence=confidence)
    rat_sum  = ratio_metrics.summary(comparison_data, risk_free_rate=risk_free_rate)

    pct_ret  = {"total_return", "cagr", "annualized_return", "annualized_volatility"}
    pct_risk = set(risk_sum.columns)

    story.append(KeepTogether([
        _section("Return Metrics"),
        _df_table(ret_sum, pct_ret, WIDTH),
    ]))
    story.append(Spacer(1, 6))

    story.append(KeepTogether([
        _section(f"Risk Metrics ({int(confidence*100)}% Confidence)"),
        _df_table(risk_sum, pct_risk, WIDTH),
    ]))
    story.append(Spacer(1, 6))

    story.append(KeepTogether([
        _section("Risk-Adjusted Ratios"),
        _df_table(rat_sum, set(), WIDTH),
    ]))
    story.append(Spacer(1, 6))

    if benchmark_ticker and benchmark_ticker in price_data:
        rel_sum = rel_metrics.summary(
            ticker_data, price_data[benchmark_ticker], benchmark_ticker, risk_free_rate
        )
        pct_rel = {"alpha", "excess_return", "tracking_error"}
        story.append(KeepTogether([
            _section(f"Relative Metrics vs {bench_disp.replace('&', '&amp;')}"),
            _df_table(rel_sum, pct_rel, WIDTH),
        ]))
        story.append(Spacer(1, 6))

    # ── Portfolio section (new page) ──────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Portfolio Summary", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Period: {start_date} &nbsp;→&nbsp; {end_date} &nbsp;|&nbsp; Benchmark: {bench_disp_xml} &nbsp;|&nbsp; Risk-Free Rate: {risk_free_rate:.2%}", sub_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_NAVY, spaceAfter=10))

    # ── Growth of $10,000 chart ───────────────────────────────────────────────
    from src.export.charts import growth_of_10k
    bench_ret_series = (ret_metrics.daily_returns(price_data[benchmark_ticker])
                        if benchmark_ticker and benchmark_ticker in price_data
                        else None)
    chart_buf = growth_of_10k(
        portfolio_returns=portfolio_returns,
        benchmark_returns=bench_ret_series,
        portfolio_label="Portfolio",
        benchmark_label=bench_disp,
        width_in=WIDTH / inch,
        height_in=3.2,
    )
    story.append(Image(chart_buf, width=WIDTH, height=3.2 * inch))
    story.append(Spacer(1, 12))

    dr   = portfolio_returns
    half = (WIDTH - 12) / 2

    weight_rows = [(t, f"{w:.2%}") for t, w in weights.items()]
    story.append(KeepTogether([
        _section("Portfolio Weights"),
        _kv_table(weight_rows, half),
    ]))
    story.append(Spacer(1, 6))

    ret_rows = [
        ("Total Return",          f"{port_module.total_return(dr):.2%}"),
        ("CAGR",                  f"{port_module.cagr(dr):.2%}"),
        ("Annualized Return",     f"{ret_metrics.annualized_return(dr):.2%}"),
        ("Annualized Volatility", f"{risk_metrics.std_dev_annualized(dr):.2%}"),
    ]
    risk_rows = [
        ("Max Drawdown",                      f"{risk_metrics.max_drawdown(dr):.2%}"),
        (f"VaR {int(confidence*100)}% Daily", f"{risk_metrics.var(dr, confidence):.2%}"),
        (f"ES {int(confidence*100)}% Daily",  f"{risk_metrics.expected_shortfall(dr, confidence):.2%}"),
    ]
    ratio_rows = [
        ("Sharpe Ratio",  f"{ratio_metrics.sharpe(dr, risk_free_rate):.4f}"),
        ("Sortino Ratio", f"{ratio_metrics.sortino(dr, risk_free_rate):.4f}"),
    ]
    if bench_ret_series is not None:
        ratio_rows.append(("Treynor Ratio", f"{rel_metrics.treynor(dr, bench_ret_series, risk_free_rate):.4f}"))

    story.append(KeepTogether([
        _section("Portfolio Return Metrics"),
        _kv_table(ret_rows, half),
    ]))
    story.append(Spacer(1, 6))

    story.append(KeepTogether([
        _section(f"Portfolio Risk Metrics ({int(confidence*100)}% Confidence)"),
        _kv_table(risk_rows, half),
    ]))
    story.append(Spacer(1, 6))

    story.append(KeepTogether([
        _section("Portfolio Risk-Adjusted Ratios"),
        _kv_table(ratio_rows, half),
    ]))
    story.append(Spacer(1, 6))

    if benchmark_ticker and benchmark_ticker in price_data:
        bench_returns = ret_metrics.daily_returns(price_data[benchmark_ticker])
        rel_rows = [
            ("Beta",               f"{rel_metrics.beta(dr, bench_returns):.4f}"),
            ("Alpha (annualized)", f"{rel_metrics.alpha(dr, bench_returns, risk_free_rate):.2%}"),
            ("Excess Return",      f"{rel_metrics.excess_return(dr, bench_returns):.2%}"),
            ("Tracking Error",     f"{rel_metrics.tracking_error(dr, bench_returns):.2%}"),
            ("Information Ratio",  f"{rel_metrics.information_ratio(dr, bench_returns):.4f}"),
        ]
        story.append(KeepTogether([
            _section(f"Portfolio Relative Metrics vs {bench_disp.replace('&', '&amp;')}"),
            _kv_table(rel_rows, half),
        ]))

    doc.build(story)
    return filepath
