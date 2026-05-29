from pathlib import Path
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ── Shared styles ─────────────────────────────────────────────────────────────
_HEADER_FILL  = PatternFill("solid", fgColor="1F3864")
_HEADER_FONT  = Font(name="Calibri", bold=True,   color="FFFFFF", size=11)
_DATE_FONT    = Font(name="Calibri", size=10)
_CELL_FONT    = Font(name="Calibri", size=10)
_SECTION_FILL = PatternFill("solid", fgColor="2E5F8A")
_SECTION_FONT = Font(name="Calibri", bold=True,   color="FFFFFF", size=10)
_LABEL_FILL   = PatternFill("solid", fgColor="D6E4F0")
_LABEL_FONT   = Font(name="Calibri", bold=True,   color="1F3864", size=10)
_NOTE_FONT    = Font(name="Calibri", italic=True,  color="666666", size=9)
_THIN_BORDER  = Border(bottom=Side(style="thin", color="D9D9D9"))
_SECT_BORDER  = Border(
    top=Side(style="thin",   color="1F3864"),
    bottom=Side(style="thin", color="1F3864"),
)
_CENTER  = Alignment(horizontal="center", vertical="center")
_LEFT    = Alignment(horizontal="left",   vertical="center")
_PCT     = "0.00%"
_DEC4    = "0.0000"

_TICKER_DISPLAY = {"^GSPC": "S&P 500", "^DJI": "Dow Jones", "^IXIC": "NASDAQ"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _col(idx: int) -> str:
    return get_column_letter(idx)


def _disp(ticker: str) -> str:
    return _TICKER_DISPLAY.get(ticker, ticker)


def _max_drawdown(prices: pd.Series) -> float:
    peak = prices.cummax()
    return float(((prices - peak) / peak).min())


def _style_header_row(ws, n_cols: int) -> None:
    for c in range(1, n_cols + 1):
        cell           = ws.cell(row=1, column=c)
        cell.fill      = _HEADER_FILL
        cell.font      = _HEADER_FONT
        cell.alignment = _CENTER


def _style_data_rows(ws, first_row: int, last_row: int, n_cols: int,
                     date_col: bool = True, num_format: str = "#,##0.00") -> None:
    for row in ws.iter_rows(min_row=first_row, max_row=last_row,
                            min_col=1, max_col=n_cols):
        for i, cell in enumerate(row):
            cell.border = _THIN_BORDER
            if date_col and i == 0:
                cell.font          = _DATE_FONT
                cell.alignment     = _CENTER
                cell.number_format = "YYYY-MM-DD"
            else:
                cell.font          = _CELL_FONT
                cell.alignment     = _CENTER
                cell.number_format = num_format


# ── Daily Returns sheet ───────────────────────────────────────────────────────

def _build_returns_sheet(wb, closes: pd.DataFrame, n_data_rows: int) -> None:
    """
    Add a 'Daily Returns' sheet with formulas:
        = 'Adj Close Prices'!Ct+1 / 'Adj Close Prices'!Ct - 1
    Rows 2..n_data_rows hold the n_data_rows-1 daily return observations.
    """
    ws         = wb.create_sheet("Daily Returns")
    n_tickers  = len(closes.columns)
    total_cols = n_tickers + 1

    ws.cell(row=1, column=1).value = "Date"
    for j, ticker in enumerate(closes.columns):
        ws.cell(row=1, column=j + 2).value = ticker
    _style_header_row(ws, total_cols)

    for i in range(1, n_data_rows):
        ret_row   = i + 1
        price_row = i + 1
        next_row  = i + 2

        date_cell                = ws.cell(row=ret_row, column=1)
        date_cell.value          = f"='Adj Close Prices'!A{next_row}"
        date_cell.font           = _DATE_FONT
        date_cell.alignment      = _CENTER
        date_cell.number_format  = "YYYY-MM-DD"
        date_cell.border         = _THIN_BORDER

        for j in range(n_tickers):
            c             = _col(j + 2)
            cell          = ws.cell(row=ret_row, column=j + 2)
            cell.value    = (f"='Adj Close Prices'!{c}{next_row}"
                             f"/'Adj Close Prices'!{c}{price_row}-1")
            cell.font          = _CELL_FONT
            cell.alignment     = _CENTER
            cell.number_format = _PCT
            cell.border        = _THIN_BORDER

    ws.column_dimensions[_col(1)].width = 14
    for ci in range(2, total_cols + 1):
        ws.column_dimensions[_col(ci)].width = 14

    ws.freeze_panes             = "A2"
    ws.sheet_view.showGridLines = False


# ── Metrics section in Adj Close Prices ──────────────────────────────────────

def _add_metrics_section(
    ws,
    closes: pd.DataFrame,
    n_data_rows: int,
    benchmark_ticker: str = None,
    risk_free_rate: float = 0.0,
) -> None:
    n_tickers  = len(closes.columns)
    last_price = n_data_rows + 1
    sec_start  = last_price + 2
    n_returns  = n_data_rows
    total_cols = n_tickers + 1

    # Benchmark column index in both sheets (None if not present)
    ticker_list   = list(closes.columns)
    bench_col_idx = (ticker_list.index(benchmark_ticker) + 2
                     if benchmark_ticker and benchmark_ticker in ticker_list
                     else None)
    bench_col = _col(bench_col_idx) if bench_col_idx else None

    # ── Row builders ──────────────────────────────────────────────────────────
    def section_header(row_num: int, title: str) -> None:
        for c in range(1, total_cols + 1):
            cell           = ws.cell(row=row_num, column=c)
            cell.fill      = _SECTION_FILL
            cell.font      = _SECTION_FONT
            cell.alignment = _CENTER
            cell.border    = _SECT_BORDER
        ws.cell(row=row_num, column=1).value = title

    def metric_row(row_num: int, label: str, values: list,
                   num_format: str = _PCT) -> None:
        lc           = ws.cell(row=row_num, column=1)
        lc.value     = label
        lc.fill      = _LABEL_FILL
        lc.font      = _LABEL_FONT
        lc.alignment = _LEFT
        lc.border    = _THIN_BORDER
        for i, val in enumerate(values):
            cell           = ws.cell(row=row_num, column=i + 2)
            cell.font      = _CELL_FONT
            cell.alignment = _CENTER
            cell.border    = _THIN_BORDER
            if val == "—":
                cell.value         = "—"
                cell.number_format = "@"
            else:
                cell.value         = val
                cell.number_format = num_format

    # ── Return Metrics ────────────────────────────────────────────────────────
    section_header(sec_start, "RETURN METRICS")

    metric_row(sec_start + 1, "Total Return",
        [f"=({_col(j+2)}{last_price}-{_col(j+2)}2)/{_col(j+2)}2"
         for j in range(n_tickers)])

    metric_row(sec_start + 2, "CAGR",
        [f"=({_col(j+2)}{last_price}/{_col(j+2)}2)"
         f"^(252/(ROWS({_col(j+2)}2:{_col(j+2)}{last_price})-1))-1"
         for j in range(n_tickers)])

    metric_row(sec_start + 3, "Annualized Return",
        [f"=AVERAGE('Daily Returns'!{_col(j+2)}2"
         f":'Daily Returns'!{_col(j+2)}{n_returns})*252"
         for j in range(n_tickers)])

    metric_row(sec_start + 4, "Annualized Volatility",
        [f"=STDEV('Daily Returns'!{_col(j+2)}2"
         f":'Daily Returns'!{_col(j+2)}{n_returns})*SQRT(252)"
         for j in range(n_tickers)])

    # ── Risk Metrics ──────────────────────────────────────────────────────────
    section_header(sec_start + 6, "RISK METRICS  (95% confidence)")

    metric_row(sec_start + 7, "Max Drawdown *",
        [_max_drawdown(closes.iloc[:, j]) for j in range(n_tickers)])

    metric_row(sec_start + 8, "VaR 95% Daily",
        [f"=-PERCENTILE('Daily Returns'!{_col(j+2)}2"
         f":'Daily Returns'!{_col(j+2)}{n_returns},0.05)"
         for j in range(n_tickers)])

    metric_row(sec_start + 9, "ES 95% Daily",
        [f"=-AVERAGEIF('Daily Returns'!{_col(j+2)}2"
         f":'Daily Returns'!{_col(j+2)}{n_returns},"
         f"\"<=\"&PERCENTILE('Daily Returns'!{_col(j+2)}2"
         f":'Daily Returns'!{_col(j+2)}{n_returns},0.05))"
         for j in range(n_tickers)])

    note = ws.cell(row=sec_start + 11, column=1)
    note.value = ("* Max Drawdown: pre-computed (max peak-to-trough decline). "
                  "All other metrics use 'Daily Returns' sheet formulas.")
    note.font  = _NOTE_FONT

    # ── Relative Metrics ──────────────────────────────────────────────────────
    if bench_col is None:
        ws.column_dimensions[_col(1)].width = 26
        return

    bench_rng = f"'Daily Returns'!{bench_col}2:'Daily Returns'!{bench_col}{n_returns}"
    rel_start       = sec_start + 13
    beta_row        = rel_start + 1
    excess_ret_row  = rel_start + 4
    tracking_err_row = rel_start + 5
    bench_label     = _disp(benchmark_ticker)

    section_header(rel_start, f"RELATIVE METRICS vs {bench_label}")

    def rel_vals(formula_fn, num_format=_PCT):
        vals = []
        for j in range(n_tickers):
            col_idx = j + 2
            if col_idx == bench_col_idx:
                vals.append("—")
            else:
                c = _col(col_idx)
                rng = f"'Daily Returns'!{c}2:'Daily Returns'!{c}{n_returns}"
                vals.append(formula_fn(c, rng))
        return vals

    # Beta — SLOPE(ticker_returns, bench_returns) is available in all Excel versions
    metric_row(beta_row, "Beta",
        rel_vals(lambda c, rng:
            f"=SLOPE({rng},{bench_rng})"),
        num_format=_DEC4)

    # Alpha (annualized Jensen's Alpha)
    metric_row(rel_start + 2, "Alpha (Annualized)",
        rel_vals(lambda c, rng:
            f"=(AVERAGE({rng})*252-{risk_free_rate})"
            f"-{c}{beta_row}*(AVERAGE({bench_rng})*252-{risk_free_rate})"))

    # Treynor Ratio
    metric_row(rel_start + 3, "Treynor Ratio",
        rel_vals(lambda c, rng:
            f"=(AVERAGE({rng})*252-{risk_free_rate})/{c}{beta_row}"),
        num_format=_DEC4)

    # Excess Return
    metric_row(excess_ret_row, "Excess Return",
        rel_vals(lambda c, rng:
            f"=AVERAGE({rng})*252-AVERAGE({bench_rng})*252"))

    # Tracking Error — uses SUMPRODUCT to avoid array-formula entry
    metric_row(tracking_err_row, "Tracking Error",
        rel_vals(lambda c, rng:
            f"=SQRT(SUMPRODUCT(({rng}-{bench_rng}"
            f"-AVERAGE({rng})+AVERAGE({bench_rng}))^2)"
            f"/(ROWS({rng})-1))*SQRT(252)"))

    # Information Ratio
    metric_row(rel_start + 6, "Information Ratio",
        rel_vals(lambda c, rng:
            f"={c}{excess_ret_row}/{c}{tracking_err_row}"),
        num_format=_DEC4)

    ws.column_dimensions[_col(1)].width = 26


# ── Main export ───────────────────────────────────────────────────────────────

def export_pricing(
    price_data: dict,
    output_dir: Path,
    start_date: str,
    end_date: str,
    benchmark_ticker: str = None,
    risk_free_rate: float = 0.0,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    closes = pd.DataFrame(
        {ticker: df["adj_close"] for ticker, df in price_data.items()}
    ).sort_index()

    filename = f"Pricing_Data_{start_date}_to_{end_date}.xlsx"
    filepath = output_dir / filename

    n_data_rows   = len(closes)
    n_ticker_cols = len(closes.columns)
    n_cols        = n_ticker_cols + 1

    with pd.ExcelWriter(filepath, engine="openpyxl", date_format="YYYY-MM-DD") as writer:
        closes.to_excel(writer, sheet_name="Adj Close Prices", index=True)

        ws = writer.sheets["Adj Close Prices"]
        wb = writer.book

        _style_header_row(ws, n_cols)
        ws.cell(row=1, column=1).value = "Date"
        _style_data_rows(ws, 2, n_data_rows + 1, n_cols)

        _build_returns_sheet(wb, closes, n_data_rows)

        _add_metrics_section(ws, closes, n_data_rows, benchmark_ticker, risk_free_rate)

        ws.column_dimensions[_col(1)].width = 26
        for ci in range(2, n_cols + 1):
            ws.column_dimensions[_col(ci)].width = 18

        ws.freeze_panes             = "A2"
        ws.sheet_view.showGridLines = False

    return filepath
