from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP
from html import escape
import numpy as np


def write_stats_cards_to_html(html_path, stats):
    percent_keys = {
        'Exposure Time [%]',
        'Return [%]',
        'Buy & Hold Return [%]',
        'Return (Ann.) [%]',
        'Volatility (Ann.) [%]',
        'CAGR [%]',
        'Max. Drawdown [%]',
        'Win Rate [%]',
        'Best Trade [%]',
        'Worst Trade [%]',
        'Avg. Trade [%]',
        'Expectancy [%]',
    }

    def fmt_value(key, value):
        if key == '# Trades':
            try:
                return str(int(value))
            except (ValueError, TypeError):
                return str(value)

        if isinstance(value, (int, float, np.integer, np.floating)):
            if isinstance(value, (float, np.floating)) and not np.isfinite(value):
                return str(value)
            try:
                rounding_mode = ROUND_HALF_UP if key in {'Win Rate [%]', 'Profit Factor'} else ROUND_DOWN
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
        note_html = f"<span style='color:#666;font-size:12px;'> {escape(note)}</span>" if note else ""
        return (
            "<div style='display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px dashed #eee;'>"
            f"<div style='color:#333;'>{escape(label)}{note_html}</div>"
            f"<div style='font-weight:600;color:#111;'>{escape(value)}</div>"
            "</div>"
        )

    card1 = "".join([
        item("最终权益", "Equity Final [$]"),
        item("权益峰值", "Equity Peak [$]"),
        item("策略收益率", "Return [%]"),
        item("买入持有收益率", "Buy & Hold Return [%]", "（未跑赢大盘可关注）"),
        item("年化收益率", "Return (Ann.) [%]"),
        item("复合年增长率", "CAGR [%]"),
        item("持仓时间占比", "Exposure Time [%]"),
    ])
    card2 = "".join([
        item("最大回撤", "Max. Drawdown [%]"),
        item("年化波动率", "Volatility (Ann.) [%]"),
        item("总手续费", "Commissions [$]"),
        item("回测周期", "Duration"),
    ])
    card3 = "".join([
        item("夏普比率", "Sharpe Ratio", "（>1 常用基线，>2 较优秀）"),
        item("索提诺比率", "Sortino Ratio", "（>1 可接受，>2 较稳健）"),
        item("卡玛比率", "Calmar Ratio", "（>1 说明收益覆盖回撤）"),
        item("系统质量指数(SQN)", "SQN", "（<1 弱，1-2 普通，>2 较好）"),
    ])
    card4 = "".join([
        item("交易次数", "# Trades"),
        item("胜率", "Win Rate [%]"),
        item("盈亏比", "Profit Factor"),
        item("期望收益", "Expectancy [%]"),
        item("单笔平均收益", "Avg. Trade [%]"),
        item("单笔最大收益", "Best Trade [%]"),
        item("单笔最大亏损", "Worst Trade [%]"),
    ])

    stats_block = (
        "<div id='backtest-summary' style='max-width:1100px;margin:20px auto;padding:0 4px;'>"
        "<h2 style='margin:0 0 12px 0;font-size:20px;'>回测结果卡片总览</h2>"
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

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    html = html.replace('</body>', f'{stats_block}</body>')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

