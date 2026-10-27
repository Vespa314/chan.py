# 秒级 K 线与期货交易日

`CTime` 将实际时间与交易日分开保存：

- `year/month/day/hour/minute/second`、`ts` 和时间比较使用实际发生时间。
- `trading_day` 用于日线及以上父级别的归属和日线及以下级别的日期一致性检查，默认等于实际日期。
- 日内父子级别仍按实际结束时间对齐，跨午夜的夜盘不会因交易日相同而被塞入同一根分钟线。

请先将行情时间转换成交易所本地时间。当前时间戳沿用项目原有的本机时区行为，
运行环境的时区应与行情一致；本次没有增加时区或夏令时转换。

## 秒与午夜

```python
from Common.CTime import CTime

t = CTime.from_str('2026-07-04 00:00:01')
assert t.second == 1
assert str(t) == '2026/07/04 00:00:01'
```

支持 `YYYY-MM-DD`、`YYYYMMDD`、`YYYY-MM-DD HH:MM`、
`YYYY-MM-DD HH:MM:SS`、`YYYYMMDDHHMMSS` 和 BaoStock 风格的
`YYYYMMDDHHMMSSmmm`。最后一种格式只保留到秒，不支持毫秒 K 线。

日期字符串保留日线的 `auto=True` 行为；包含时间的字符串默认使用 `auto=False`，
包括 `00:00:00`。直接构造日内时间时也应显式传入 `auto=False`：

```python
t = CTime(2026, 7, 4, 0, 0, 0, auto=False)
```

非零秒会出现在 `str(t)` 和 `t.to_str()` 中。整分钟沿用 `HH:MM` 格式，
如需固定显示秒，可调用 `t.to_str(show_seconds=True)`。显式日内午夜显示为
`00:00`，而不是只有日期。图表标签和标记查找使用这些实际时间字符串。

## 优先使用行情源的交易日

自定义数据源应将交易所或行情供应商提供的交易日放进 `CTime`：

```python
t = CTime.from_str('2026-07-03 21:00:01', trading_day='2026-07-06')
# 或 CTime(..., auto=False, trading_day='20260706')
```

`trading_day` 接受 `datetime.date`、`datetime.datetime`、`YYYY-MM-DD` 或
`YYYYMMDD`。它不改写真实时间或时间戳，也不会让周五夜盘在排序时排到周一日盘之后。
日线记录本身应以所属交易日作为日期；所有日内级别都应携带一致的交易日。

例如，在供应商将该夜盘归属到周一的情况下，周五夜盘和周六凌晨 K 线会挂在周一日线下。
下一交易日的夜盘会留在缓存中，等待相应日线，而不会被前一根日线提前消费。
未传交易日的现有股票数据仍按自然日期匹配。

## 没有交易日字段时：使用真实交易时段表

`TradingCalendar` 按调用方提供的 `(开始时间, 结束时间, 交易日)` 映射交易日。
它不内置固定周末或节假日规则；请使用目标交易所、合约及日期范围的实际交易时段。
这能表达节前取消夜盘、不同品种的收盘时间，以及跨周末的夜盘。

```python
from datetime import datetime
from Common.TradingCalendar import TradingCalendar

# 接入示例，请用供应商或交易所的实际时段替换。
calendar = TradingCalendar([
    (datetime(2026, 7, 3, 21), datetime(2026, 7, 4, 2, 30), '2026-07-06'),
    (datetime(2026, 7, 6, 9), datetime(2026, 7, 6, 11, 30), '2026-07-06'),
    (datetime(2026, 7, 6, 13, 30), datetime(2026, 7, 6, 15), '2026-07-06'),
])
actual = datetime(2026, 7, 4, 0, 0, 1)
t = CTime(actual.year, actual.month, actual.day, actual.hour, actual.minute,
          actual.second, auto=False, trading_day=calendar(actual))
```

区间两端均包含，支持 K 线结束时间；区间不可重叠，应按需要拆分休市间隔。
未找到交易时段时抛出 `ValueError`，不会自行猜测下一个工作日。
交易日规则参考：[上期所交易规则](https://www.shfe.cn/regulation/exchangerules/rules/202606/t20260603_831934.html)。

## CSV 接入

在原有列的最后增加可选的 `trading_day` 列，CSV 加载器会从表头识别它：

```csv
time,open,high,low,close,trading_day
2026-07-03 21:00:01,10,12,9,11,2026-07-06
2026-07-04 00:00:00,11,13,10,12,2026-07-06
2026-07-06 09:00:01,12,14,11,13,2026-07-06
```

没有表头时，在自定义 `CSV_API` 中将 `'trading_day'` 追加到 `self.columns`。
空交易日字段回退到实际日期；期货数据应完整填写。
CSV 加载器不自动调用 `TradingCalendar`，可在生成 CSV 时预先用该工具补齐交易日。

日期形式的 `begin_time/end_time`（例如均为 `2026-07-06`）按交易日筛选，
因此包含归属该日的前一夜盘，也包含结束日期当天的日盘。
包含时间的边界按实际时间筛选，且边界包含在内。原有不带交易日列的 CSV 仍可使用。

这里只补齐已有数据的秒级时间和交易日处理；不会为 BaoStock、CCXT 或 Akshare
增加其自身不提供的期货或秒级行情接口。

## 验证

在仓库根目录运行，无需联网或行情供应商 SDK：

```bash
python -m unittest discover -s tests -v
```
