# 自动导演 · 镜头规则（内容拍内）

混剪 `shot` 取值：`closeup` | `wide`。音频始终用特写轨。  
在语气词快剪后的保留区间上再挂机位；**切镜必须落在停顿点**，禁止句中硬切。  
本规则只做 A/B 粗挂；终态以 Agent [`shot_director.md`](./shot_director.md) 为准。不做推拉摇。

min_shot_seconds: 2.5
establish_wide_seconds: 2.5
max_closeup_run_seconds: 8
punchline_closeup: 1

wide_keywords: 有请,欢迎,鼓掌,掌声,谢谢,感谢,致谢,各位来宾,大家好
theme_force_closeup_keywords: FDE,OPC,流程革命,洞察革命,组织提效,个人提效,懂业务,部落型组织,岗位能力

镜头启发：
- 主特写、辅全景；定场/换气切入点对齐词间隙停顿；找不到停顿则整段一种 shot（默认特写）。
- 特写连续过长才在停顿处插入全景换气。
- 主题词 / 金句强制特写。
- 礼仪词倾向全景。
- 单镜短于 min_shot 则并入相邻镜。
