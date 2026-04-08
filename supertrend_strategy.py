from backtesting import Strategy, Backtest
from backtesting.lib import FractionalBacktest
import pandas as pd
import numpy as np
from html import escape
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP
import os
from report_utils import write_stats_cards_to_html

def SuperTrend(high, low, close, atr_period=10, multiplier=3.0):
    """标准 SuperTrend（TR/ATR + Final Bands）"""
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(atr_period, min_periods=atr_period).mean()

    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    trend = pd.Series(1, index=close.index, dtype=int)  # 1 = up, -1 = down
    supertrend = pd.Series(np.nan, index=close.index, dtype=float)

    for i in range(1, len(close)):
        if pd.isna(atr.iloc[i]):
            trend.iloc[i] = trend.iloc[i - 1]
            continue

        if (basic_upper.iloc[i] < final_upper.iloc[i - 1]) or (close.iloc[i - 1] > final_upper.iloc[i - 1]):
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        if (basic_lower.iloc[i] > final_lower.iloc[i - 1]) or (close.iloc[i - 1] < final_lower.iloc[i - 1]):
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

        if trend.iloc[i - 1] == -1 and close.iloc[i] > final_upper.iloc[i]:
            trend.iloc[i] = 1
        elif trend.iloc[i - 1] == 1 and close.iloc[i] < final_lower.iloc[i]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i - 1]

        supertrend.iloc[i] = final_lower.iloc[i] if trend.iloc[i] == 1 else final_upper.iloc[i]

    # 可视化友好：预热期用首个有效值回填，避免图上出现长段 NaN 断线
    supertrend = supertrend.ffill().bfill()
    return np.array(supertrend, copy=True), np.array(trend, copy=True)


def SuperTrendLine(high, low, close, atr_period=10, multiplier=3.0):
    supertrend, _ = SuperTrend(high, low, close, atr_period, multiplier)
    return np.array(supertrend, copy=True)


def TrendDirection(high, low, close, atr_period=10, multiplier=3.0):
    _, trend = SuperTrend(high, low, close, atr_period, multiplier)
    return np.array(trend, copy=True)


def LongSLReference(close, sl_pct=0.04):
    close = pd.Series(close)
    return np.array(close * (1 - sl_pct), copy=True)


def ShortSLReference(close, sl_pct=0.04):
    close = pd.Series(close)
    return np.array(close * (1 + sl_pct), copy=True)


def BuySignalMarkers(high, low, close, atr_period=10, multiplier=3.0):
    close = pd.Series(close)
    _, trend = SuperTrend(high, low, close, atr_period, multiplier)
    trend_s = pd.Series(trend)
    markers = pd.Series(np.nan, index=close.index, dtype=float)
    # 趋势由 -1 翻转为 1 的位置标买点
    buy_mask = (trend_s.shift(1) == -1) & (trend_s == 1)
    markers[buy_mask] = close[buy_mask]
    return np.array(markers, copy=True)


def SellSignalMarkers(high, low, close, atr_period=10, multiplier=3.0):
    close = pd.Series(close)
    _, trend = SuperTrend(high, low, close, atr_period, multiplier)
    trend_s = pd.Series(trend)
    markers = pd.Series(np.nan, index=close.index, dtype=float)
    # 趋势由 1 翻转为 -1 的位置标卖点
    sell_mask = (trend_s.shift(1) == 1) & (trend_s == -1)
    markers[sell_mask] = close[sell_mask]
    return np.array(markers, copy=True)


def write_stats_to_html(html_path, stats):
    metric_map = {
        'Start': '开始时间',
        'End': '结束时间',
        'Duration': '回测周期',
        'Exposure Time [%]': '持仓时间占比[%]',
        'Equity Final [$]': '最终权益[$]',
        'Equity Peak [$]': '权益峰值[$]',
        'Commissions [$]': '总手续费[$]',
        'Return [%]': '策略收益率[%]',
        'Buy & Hold Return [%]': '买入持有收益率[%]',
        'Return (Ann.) [%]': '年化收益率[%]',
        'Volatility (Ann.) [%]': '年化波动率[%]',
        'CAGR [%]': '复合年增长率[%]',
        'Sharpe Ratio': '夏普比率',
        'Sortino Ratio': '索提诺比率',
        'Calmar Ratio': '卡玛比率',
        'Max. Drawdown [%]': '最大回撤[%]',
        '# Trades': '交易次数',
        'Win Rate [%]': '胜率[%]',
        'Best Trade [%]': '单笔最大收益[%]',
        'Worst Trade [%]': '单笔最大亏损[%]',
        'Avg. Trade [%]': '单笔平均收益[%]',
        'Profit Factor': '盈亏比',
        'Expectancy [%]': '期望收益[%]',
        'SQN': '系统质量指数',
    }
    def get_value(key):
        return fmt_value(key, stats[key]) if key in stats else "-"
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
        # 统一口径：
        # - 交易次数保留整数
        # - 胜率/盈亏比采用四舍五入到 3 位
        # - 其余数值默认截断到 3 位（偏保守）
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
                if key in percent_keys:
                    return f"{s}%"
                return s
            except (InvalidOperation, ValueError):
                return str(value)
        return str(value)

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
        item("夏普比率", "Sharpe Ratio", "（风险收益比）"),
        item("索提诺比率", "Sortino Ratio"),
        item("卡玛比率", "Calmar Ratio"),
        item("系统质量指数(SQN)", "SQN", "（统计稳定性）"),
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

    move_equity_script = (
        "<script>"
        "window.addEventListener('load', function () {"
        "  const labels = Array.from(document.querySelectorAll('div, span'));"
        "  const equityLabel = labels.find(el => (el.textContent || '').trim() === 'Equity');"
        "  if (!equityLabel) return;"
        "  const panel = equityLabel.closest('[class*=bk]')?.parentElement;"
        "  const root = document.querySelector('.bk-root') || document.body;"
        "  if (panel && root.contains(panel)) root.appendChild(panel);"
        "});"
        "</script>"
    )

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    html = html.replace('</body>', f'{stats_block}{move_equity_script}</body>')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

class SuperTrendFuturesStrategy(Strategy):
    atr_period = 10
    multiplier = 3.0
    risk_per_trade = 0.02  # 单笔风险控制
    
    def init(self):
        self.supertrend = self.I(
            SuperTrendLine,
            self.data.High,
            self.data.Low,
            self.data.Close,
            self.atr_period,
            self.multiplier,
            name='SuperTrend',
            overlay=True,
            color='#FFB000',
        )
        self.trend = self.I(
            TrendDirection,
            self.data.High,
            self.data.Low,
            self.data.Close,
            self.atr_period,
            self.multiplier,
            name='Trend',
            plot=False,
        )
        # 这两条是参考止损带（不是每笔交易真实动态SL轨迹）
        self.long_sl_ref = self.I(
            LongSLReference,
            self.data.Close,
            0.04,
            name='Long SL Ref',
            overlay=True,
            color='rgba(46, 139, 87, 0.3)',
        )
        self.short_sl_ref = self.I(
            ShortSLReference,
            self.data.Close,
            0.04,
            name='Short SL Ref',
            overlay=True,
            color='rgba(205, 92, 92, 0.3)',
        )
        self.buy_markers = self.I(
            BuySignalMarkers,
            self.data.High,
            self.data.Low,
            self.data.Close,
            self.atr_period,
            self.multiplier,
            name='Buy',
            overlay=True,
            color='#00AA00',
            scatter=True,
        )
        self.sell_markers = self.I(
            SellSignalMarkers,
            self.data.High,
            self.data.Low,
            self.data.Close,
            self.atr_period,
            self.multiplier,
            name='Sell',
            overlay=True,
            color='#CC0000',
            scatter=True,
        )
    
    def next(self):
        price = self.data.Close[-1]
        
        if not self.position:
            # 开仓
            if self.trend[-1] == 1:   # 上涨趋势 → 多
                self.buy(size=0.08, sl=price * 0.96)   # 约 4% 止损
            elif self.trend[-1] == -1:  # 下跌趋势 → 空
                self.sell(size=0.08, sl=price * 1.04)
                
        else:
            # 趋势反转平仓并反手
            if (self.position.is_long and self.trend[-1] == -1) or \
               (self.position.is_short and self.trend[-1] == 1):
                self.position.close()

# 测试运行
if __name__ == "__main__":
    data = pd.read_csv('data/btc_futures_1h.csv', parse_dates=True, index_col='timestamp')
    data = data.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'})
    
    bt = FractionalBacktest(data, SuperTrendFuturesStrategy,
                  cash=10000, 
                  commission=0.0004, 
                  margin=0.1,          # 10x 杠杆
                  trade_on_close=True,
                  exclusive_orders=True)
    
    stats = bt.run()
    print(stats)
    os.makedirs('charts', exist_ok=True)
    output_html = 'charts/SuperTrendFuturesStrategy.html'
    bt.plot(resample='4h', filename=output_html, open_browser=False, show_legend=False)
    write_stats_cards_to_html(output_html, stats)