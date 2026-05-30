import io
import matplotlib
matplotlib.use("Agg")                   # non-interactive backend — no display required
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import pandas as pd


_NAVY    = "#1F3864"
_RED     = "#C0392B"
_GRID    = "#DDDDDD"
_SPINE   = "#CCCCCC"
_LABEL   = "#555555"


def growth_of_10k(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series | None,
    portfolio_label: str = "Portfolio",
    benchmark_label: str = "S&P 500",
    start_value: float = 10_000,
    width_in: float = 9.0,
    height_in: float = 3.2,
) -> io.BytesIO:
    """
    Render a Growth of $10,000 line chart and return a PNG BytesIO buffer
    ready for embedding in reportlab (PDF) or openpyxl (Excel).

    X-axis ticks at 6-month (Jan / Jul) boundaries.
    Y-axis formatted as USD currency.
    Shaded region between portfolio and benchmark lines.
    """
    # Align both series on shared trading dates
    if benchmark_returns is not None:
        aligned = pd.concat(
            [portfolio_returns.rename(portfolio_label),
             benchmark_returns.rename(benchmark_label)],
            axis=1,
        ).dropna()
    else:
        aligned = portfolio_returns.rename(portfolio_label).to_frame().dropna()

    growth = (1 + aligned).cumprod() * start_value

    fig, ax = plt.subplots(figsize=(width_in, height_in))

    # Portfolio line
    ax.plot(growth.index, growth[portfolio_label],
            color=_NAVY, linewidth=2.0, label=portfolio_label, zorder=3)

    # Benchmark line + shaded region between the two
    if benchmark_label in growth.columns:
        ax.plot(growth.index, growth[benchmark_label],
                color=_RED, linewidth=1.5, linestyle="--",
                label=benchmark_label, zorder=2)

        ax.fill_between(
            growth.index,
            growth[portfolio_label], growth[benchmark_label],
            where=growth[portfolio_label] >= growth[benchmark_label],
            alpha=0.07, color=_NAVY, interpolate=True,
        )
        ax.fill_between(
            growth.index,
            growth[portfolio_label], growth[benchmark_label],
            where=growth[portfolio_label] < growth[benchmark_label],
            alpha=0.07, color=_RED, interpolate=True,
        )

    # ── X-axis: 6-month (Jan / Jul) ticks ────────────────────────────────────
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)

    # ── Y-axis: dollar format ─────────────────────────────────────────────────
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"${x:,.0f}")
    )
    ax.tick_params(axis="y", labelsize=8)
    ax.set_ylabel("Value (USD)", fontsize=8, color=_LABEL, labelpad=6)

    # ── Styling ───────────────────────────────────────────────────────────────
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6, color=_GRID)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(_SPINE)

    ax.set_title(
        f"Growth of ${start_value:,.0f}",
        fontsize=11, fontweight="bold", color=_NAVY, pad=8, loc="left",
    )
    ax.legend(fontsize=9, framealpha=0.9, loc="upper left",
              frameon=True, edgecolor=_SPINE)

    plt.tight_layout(pad=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf
