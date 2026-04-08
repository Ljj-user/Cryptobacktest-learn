# 用 CCXT 下载数据
 
import ccxt
import pandas as pd
from ccxt.base.errors import RequestTimeout, NetworkError

def fetch_futures_ohlcv(
    symbol='BTC/USDT:USDT',
    timeframe='1h',
    limit=1000,
    max_retries=3,
    proxy_url='http://127.0.0.1:7897',
    start='2024-01-01T00:00:00Z',
    end='2026-01-01T00:00:00Z',
):
    exchange = ccxt.binance({
        'timeout': 30000,  # 30s，默认 10s 在网络慢时容易超时
        'enableRateLimit': True,
        'proxies': {'http': proxy_url, 'https': proxy_url},
        'options': {'defaultType': 'future'}  # 关键：合约模式
    })
    print(f"当前代理: {proxy_url}")
    start_ms = exchange.parse8601(start)
    end_ms = exchange.parse8601(end)

    if start_ms is None or end_ms is None or start_ms >= end_ms:
        raise ValueError("时间范围无效，请检查 start/end 格式与先后顺序。")

    timeframe_ms = exchange.parse_timeframe(timeframe) * 1000
    all_ohlcv = []
    since = start_ms
    page = 0

    while since < end_ms:
        ohlcv = None
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
                break
            except (RequestTimeout, NetworkError) as e:
                last_error = e
                print(f"[第 {page + 1} 页 {attempt}/{max_retries}] 网络超时或连接异常：{e}")
                if attempt < max_retries:
                    print("正在重试...")

        if ohlcv is None:
            raise RuntimeError(
                "获取 Binance 数据失败：多次重试后仍超时。"
                "请检查网络/代理是否可访问 api.binance.com。"
            ) from last_error

        if not ohlcv:
            print("接口返回空数据，提前结束。")
            break

        page += 1
        all_ohlcv.extend(ohlcv)
        last_ts = ohlcv[-1][0]
        print(f"第 {page} 页下载完成：{len(ohlcv)} 根，最后时间戳 = {pd.to_datetime(last_ts, unit='ms')}")

        next_since = last_ts + timeframe_ms
        if next_since <= since:
            break
        since = next_since

    if not all_ohlcv:
        raise RuntimeError("未下载到任何K线数据。")

    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df[(df['timestamp'] >= start_ms) & (df['timestamp'] < end_ms)]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.dropna()
    df = df.drop_duplicates(subset='timestamp').sort_values('timestamp')
    df.set_index('timestamp', inplace=True)

    # 数据质量闸门：必须保持严格的 1h 连续
    expected_delta = pd.Timedelta(hours=exchange.parse_timeframe(timeframe))
    gaps = df.index.to_series().diff().dropna()
    bad_gaps = gaps[gaps != expected_delta]
    if not bad_gaps.empty:
        sample = bad_gaps.head(5)
        raise RuntimeError(
            "K线时间序列不连续，存在缺失或异常间隔。"
            f"\n期望间隔: {expected_delta}, 异常数量: {len(bad_gaps)}"
            f"\n示例:\n{sample}"
        )

    # 简单异常K线过滤检查（高低价反转或非正价格）
    invalid_rows = df[(df['high'] < df['low']) | (df[['open', 'high', 'low', 'close']] <= 0).any(axis=1)]
    if not invalid_rows.empty:
        raise RuntimeError(f"检测到异常K线数据行: {len(invalid_rows)}")

    df.to_csv('data/btc_futures_1h.csv')
    print(
        f"下载完成！时间范围 {start} ~ {end}，共 {len(df)} 根 K 线。"
        f"\n最后三条：\n{df.tail(3)}"
    )
    return df

if __name__ == "__main__":
    fetch_futures_ohlcv()