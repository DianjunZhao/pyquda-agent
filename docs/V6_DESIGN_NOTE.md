# V6 Design Note

## Priority

V6 的第一优先级不是继续堆更多 `workflow_id`，而是把系统收紧成一个更真实可用的自然语言到代码代理：

`rough request -> physics interpretation -> minimal clarification -> grounded implementation plan -> strict runnable script -> runtime evidence`

扩展 breadth 只能建立在可审查 provenance 和真实 PyQUDA grounding 之上。

## Provenance Terms

### Local curated citation

- 来源是仓库内的本地 JSON citation artifact，例如 `data/physics_citations/*.json`
- 作用是补充物理定义或约定说明
- 不是任务时在线查询
- artifact 中必须标记为 `local_curated_citation`

### Model inference

- 来源是规则或 LLM 对用户请求、公式候选、operator 含义的推断
- 不等于外部证据
- 只能解释、归一化、提出候选，不能伪装成引用
- artifact 中必须标记为 `model_inference`

### Live online lookup

- 来源是任务执行时显式触发的在线查询
- 默认关闭，只有在本地 PyQUDA 代码不足以定义 physics target 时才允许进入
- 当前触发策略被收紧为：仅对 `meson` 但 operator/channel 仍未明确的请求尝试 live lookup
- live lookup 当前只能补强 formula/operator proposal 与 provenance；不能直接替用户确认 workflow
- 必须记录：
  - lookup 是否启用
  - lookup 是否执行
  - 查询内容
  - 返回来源
  - 失败原因
- artifact 中必须标记为 `live_online_lookup`

## Runtime Terms

### Structurally grounded

- 生成脚本使用真实 PyQUDA imports / IO / inversion / contraction 路径
- 对应的实现路径能追溯到 `~/PyQUDA` 本地参考

### Runtime-ready

- 除结构 grounding 外，当前环境检查也通过
- 例如依赖、模块导入、路径约定、基础运行前提满足

### Runtime-proved

- 在当前环境中做过最小 probe，并拿到成功执行证据
- 这是比 runtime-ready 更强的状态

## Clarification Ordering

V6 的稳定顺序是：

1. `physics first`
   - 先确认 physics target
   - 再确认最小 physics-level task choice，例如 `start_from`、`source_timeslices`、`gauge_fixed`
2. `implementation second`
   - 只在 target 已确认且存在可匹配 family 时，再问 `fermion_action`、solver、propagator format 等
3. `runtime third`
   - 最后问路径、grid、resource path、cluster launch、output path

这个顺序的目的不是追求抽象纯度，而是避免一开始就把用户拖进 solver/path 细节，或把 propagator-entry 请求错误地先问 `mass`。

在当前实现中，这个顺序还会叠加一个“最小高价值问题”策略：

- 先问会改变 family 选择的问题
- 再问 complete generation 的真实阻塞项
- 已从 session 继承、已由当前请求给出、或已被 workflow 固定的字段不会重复追问

## V6 First Safe Generalization

V6 先只参数化一个已有 family：

- `pion_2pt` family
  - `start_from=gauge`
  - `start_from=propagator`

两条入口都必须保持真实 grounding：

- `gauge` 路径来自本地 meson / example / IO helpers
- `propagator` 路径必须基于本地真实 propagator I/O 和真实收缩路径

如果参数组合没有本地真实 grounding，系统必须显式拒绝，而不是退化成模板。
