# Censored Follow-up Survival Analyzer

把本地随访记录整理成可复核的 Kaplan–Meier 生存分析报告。仅使用
Python 3.12 标准库，不做医学判断或模型外推断。

## 调用方法

```bash
python -m followup_survival --records examples/records.csv --config examples/config.json --out build/report
```

- `--records`：随访记录 CSV，必须包含列 `id,group,days,event`。
- `--config`：JSON 配置，包含非空数组 `query_days`（非负整数），自动去重升序。
- `--out`：报告输出目录（不存在会创建）。

全量校验通过后才写入；输入非法时以非零状态退出，定位到具体 CSV 行或
配置项，且不会覆盖已有的旧报告（输出采用临时文件 + 原子替换）。

## 数据口径

- 每个对象只有一条记录，从第 0 天开始观察。
- `id` 非空且唯一；`group` 非空；`days` 为非负整数。
- `event=1`：该天发生事件；`event=0`：该天右删失。删失不计为事件。
- 空数据表、重复编号、缺失字段、其他事件标记一律拒绝。

## 计算规则

- 先按观测天数聚合。某天的在险数 = 随访在该天或之后结束的对象数。
- 同一天既有事件又有删失时：先用当天全部在险对象计算事件影响
  （`S *= 1 - events/at_risk`），再一并移除事件与删失对象，
  因此结果与输入行顺序无关。
- 只有删失的日子生存概率不下降；生存概率初值为 1；降到 0 后保持 0。
- 查询日：恰逢事件日取下降后的概率；两次观测之间沿用最近观测日结果；
  首次观测之前为 1；超过该组最大观测日时概率为 `null` 并标记
  `out_of_followup=true`，不外推，但仍报告该日在险数。
- 中位生存天数 = 生存概率首次小于等于 0.5 的事件日；未达到为 `null`。
- 报告包含总体（`overall`）与全部真实分组，分组按名称排序。

## 输出文件

- `ladder.csv`：每个不同观测日的处理前在险数、事件数、删失数及处理后概率。
- `timepoints.csv`：总体与各组在每个查询日的在险数、概率与越界标记。
- `summary.json`：对象数、事件数、删失数、中位生存天数及说明。

## 测试

```bash
python -m unittest discover -s tests -v
```
