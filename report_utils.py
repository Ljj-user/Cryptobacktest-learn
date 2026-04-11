from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation
from html import escape

import numpy as np


def _strategy_display_name(strategy_name: str) -> str:
    """Map strategy class name to Chinese display title."""
    name_map = {
        "RSIFuturesStrategy": "RSI 策略",
        "SuperTrendFuturesStrategy": "SuperTrend 策略",
        "EMA_ADX_Strategy": "EMA + ADX 趋势策略",
        "DCAStrategy": "定投策略（时间间隔）",
        "DCARsiStrategy": "定投策略（RSI 触发变种）",
        "LowDrawdownTrendStrategy": "低回撤趋势策略（EMA200 + ATR 风控）",
    }
    return name_map.get(strategy_name, strategy_name or "未命名策略")


def _warnings_html(stats):
    warnings = []
    trades = stats.get("# Trades")
    sharpe = stats.get("Sharpe Ratio")
    dd = stats.get("Max. Drawdown [%]")
    if trades is not None and float(trades) < 30:
        warnings.append("交易样本较少（<30），统计稳定性偏弱。")
    if sharpe is not None and float(sharpe) < 0:
        warnings.append("夏普比率为负，策略风险收益比不理想。")
    if dd is not None and float(dd) < -20:
        warnings.append("最大回撤较高（<-20%），实盘承受压力可能较大。")
    if not warnings:
        return ""
    items = "".join([f"<li>{escape(w)}</li>" for w in warnings])
    return (
        "<div style='margin:0 0 12px 0;padding:10px 12px;border:1px solid #f0d9a8;border-radius:8px;background:#fff9ea;'>"
        "<div style='font-weight:600;margin-bottom:6px;'>证据强度提示</div>"
        f"<ul style='margin:0;padding-left:18px;'>{items}</ul>"
        "</div>"
    )


def _comparison_html(compare_rows):
    if not compare_rows:
        return ""
    headers = ["Run", "Return [%]", "Max. Drawdown [%]", "Win Rate [%]", "Sharpe Ratio", "# Trades"]
    th = "".join(
        [
            f"<th style='text-align:left;padding:6px 8px;border-bottom:1px solid #eee;'>{escape(h)}</th>"
            for h in headers
        ]
    )
    trs = []
    for row in compare_rows:
        tds = "".join(
            [
                f"<td style='padding:6px 8px;border-bottom:1px dashed #eee;'>{escape(str(row.get(k, '-')))}</td>"
                for k in headers
            ]
        )
        trs.append(f"<tr>{tds}</tr>")
    tbody = "".join(trs)
    return (
        "<div style='margin:12px 0 16px 0;padding:12px;border:1px solid #ddd;border-radius:10px;background:#fff;'>"
        "<h3 style='margin:0 0 10px 0;font-size:16px;'>多次运行对比</h3>"
        f"<table style='width:100%;border-collapse:collapse;'><thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table>"
        "</div>"
    )


def write_stats_cards_to_html(html_path, stats, strategy_name=None, compare_rows=None):
    percent_keys = {
        "Exposure Time [%]",
        "Return [%]",
        "Realism-Adjusted Return [%]",
        "Buy & Hold Return [%]",
        "Return (Ann.) [%]",
        "Volatility (Ann.) [%]",
        "CAGR [%]",
        "Max. Drawdown [%]",
        "Win Rate [%]",
        "Capital Utilization [%]",
        "Margin Utilization [%]",
        "Best Trade [%]",
        "Worst Trade [%]",
        "Avg. Trade [%]",
        "Expectancy [%]",
    }

    def fmt_value(key, value):
        if key == "# Trades":
            try:
                return str(int(value))
            except (ValueError, TypeError):
                return str(value)

        if isinstance(value, (int, float, np.integer, np.floating)):
            if isinstance(value, (float, np.floating)) and not np.isfinite(value):
                return str(value)
            try:
                rounding_mode = (
                    ROUND_HALF_UP if key in {"Win Rate [%]", "Profit Factor"} else ROUND_DOWN
                )
                d = Decimal(str(value)).quantize(Decimal("0.001"), rounding=rounding_mode)
                s = format(d, "f")
                return f"{s}%" if key in percent_keys else s
            except (InvalidOperation, ValueError):
                return str(value)
        return str(value)

    def get_value(key):
        return fmt_value(key, stats[key]) if key in stats else "-"

    def item(label, key, note=""):
        value = get_value(key)
        note_html = (
            f"<span style='color:#666;font-size:12px;'> {escape(note)}</span>" if note else ""
        )
        return (
            "<div style='display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px dashed #eee;'>"
            f"<div style='color:#333;'>{escape(label)}{note_html}</div>"
            f"<div style='font-weight:600;color:#111;'>{escape(value)}</div>"
            "</div>"
        )

    card1 = "".join(
        [
            item("最终权益", "Equity Final [$]"),
            item("权益峰值", "Equity Peak [$]"),
            item("策略收益率", "Return [%]"),
            item("实盘修正收益率", "Realism-Adjusted Return [%]"),
            item("买入持有收益率", "Buy & Hold Return [%]", "（未跑赢大盘可关注）"),
            item("年化收益率", "Return (Ann.) [%]"),
            item("复合年增长率", "CAGR [%]"),
            item("持仓时间占比", "Exposure Time [%]"),
        ]
    )
    card2 = "".join(
        [
            item("最大回撤", "Max. Drawdown [%]"),
            item("年化波动率", "Volatility (Ann.) [%]"),
            item("资金使用率", "Capital Utilization [%]"),
            item("保证金占用率", "Margin Utilization [%]"),
            item("总手续费", "Commissions [$]"),
            item("估算滑点成本", "Est. Slippage [$]"),
            item("估算资金费率成本", "Est. Funding [$]"),
            item("估算额外成本", "Est. Extra Costs [$]"),
            item("回测周期", "Duration"),
        ]
    )
    card3 = "".join(
        [
            item("夏普比率", "Sharpe Ratio", "（>1 常用基线，>2 较优秀）"),
            item("索提诺比率", "Sortino Ratio", "（>1 可接受，>2 较稳健）"),
            item("卡玛比率", "Calmar Ratio", "（>1 说明收益覆盖回撤）"),
            item("系统质量指数(SQN)", "SQN", "（<1 弱，1-2 普通，>2 较好）"),
        ]
    )
    card4 = "".join(
        [
            item("交易次数", "# Trades"),
            item("胜率", "Win Rate [%]"),
            item("盈亏比", "Profit Factor"),
            item("期望收益", "Expectancy [%]"),
            item("单笔平均收益", "Avg. Trade [%]"),
            item("单笔最大收益", "Best Trade [%]"),
            item("单笔最大亏损", "Worst Trade [%]"),
        ]
    )

    if strategy_name is None:
        strategy_name = str(stats.get("_strategy", ""))
    strategy_title = escape(_strategy_display_name(strategy_name))

    stats_block = (
        "<div id='backtest-summary' style='max-width:1100px;margin:20px auto;padding:0 4px;'>"
        f"<h1 style='margin:0 0 8px 0;font-size:24px;line-height:1.3;'>{strategy_title}</h1>"
        "<h2 style='margin:0 0 12px 0;font-size:20px;'>回测结果卡片总览</h2>"
        f"{_warnings_html(stats)}"
        f"{_comparison_html(compare_rows)}"
        "<div style='display:grid;grid-template-columns:repeat(2, minmax(320px, 1fr));gap:12px;'>"
        "<div style='padding:14px;border:1px solid #ddd;border-radius:10px;background:#fff;'>"
        "<h3 style='margin:0 0 10px 0;font-size:16px;'>一、收益规模 (Returns & Growth)</h3>"
        f"{card1}</div>"
        "<div style='padding:14px;border:1px solid #ddd;border-radius:10px;background:#fff;'>"
        "<h3 style='margin:0 0 10px 0;font-size:16px;'>二、风险与波动 (Risk & Volatility)</h3>"
        f"{card2}</div>"
        "<div style='padding:14px;border:1px solid #ddd;border-radius:10px;background:#fff;'>"
        "<h3 style='margin:0 0 10px 0;font-size:16px;'>三、综合质量 (Efficiency/Risk-Adjusted)</h3>"
        f"{card3}</div>"
        "<div style='padding:14px;border:1px solid #ddd;border-radius:10px;background:#fff;'>"
        "<h3 style='margin:0 0 10px 0;font-size:16px;'>四、交易统计 (Trade Statistics)</h3>"
        f"{card4}</div>"
        "</div></div>"
    )

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("</body>", f"{stats_block}</body>")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
