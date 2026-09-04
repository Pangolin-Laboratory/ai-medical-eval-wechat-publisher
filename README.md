# AI Medical Evaluation WeChat Publisher

山甲实验室用于把**已经批准的 2D 医生端或 2C 患者端 AI 医疗测评结果**整理为微信公众号竖版长图与短文案的 Codex Skill。

它负责数据契约、图表语义、移动端排版、品牌一致性和发布前校验；它**不生成源评分，不读取模型 API，也不能替代临床专家复核**。

## 仓库结构

```text
.
├─ SKILL.md                         # Skill 主入口与标准工作流
├─ agents/openai.yaml              # Codex 展示与默认提示词
├─ assets/                         # 经批准的品牌素材
├─ references/
│  ├─ data-contract.md             # 数据字段、权威来源和审计规则
│  ├─ chart-policy.md              # 九图结构与图表语义
│  └─ writing-style.md             # 中文公众号文案规范
└─ scripts/
   ├─ render_2d_nine_cards.py      # 2D 九图参考渲染器
   ├─ validate_package.py          # 图片、Logo、占位符与字数校验
   └─ count_markdown.py            # Markdown 精确字符统计
```

## 部署逻辑

### 1. 安装为个人 Codex Skill

将仓库克隆到 Codex 的个人技能目录：

```powershell
git clone https://github.com/Pangolin-Laboratory/ai-medical-eval-wechat-publisher.git "$env:CODEX_HOME\skills\ai-medical-eval-wechat-publisher"
```

如果没有设置 `CODEX_HOME`，请将项目放入当前 Codex 配置目录下的 `skills/ai-medical-eval-wechat-publisher`。重新启动 Codex 或开启新任务后，即可通过以下方式调用：

```text
Use $ai-medical-eval-wechat-publisher to turn the approved evaluation report into a WeChat publication package.
```

Skill 会先读取数据契约与图表规则，再围绕用户指定的报告进行只读盘点、数据归一化、九图重绘、文案编写和双重校验。

### 2. 安装脚本运行环境

需要 Python 3.10 或更高版本。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Linux/macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

默认 Logo 是 PNG，因此只需要 Pillow。只有在运行时传入 SVG Logo 时，才需要额外安装 `cairosvg`。

### 3. 准备输入

渲染器接收两个 UTF-8 JSON 文件：

- `analysis_summary.json`：产品、临床分、技术分、排名、安全闸门、专科均值、相关性和历史排名。
- `radar_data.json`：技术雷达维度及其 0—100 归一化结果。

字段定义与审计公式见 [`references/data-contract.md`](references/data-contract.md)。输入应放在仓库外部或 `private_data/` 等忽略目录中。不要提交真实病历、患者标识或未公开测评结果。

### 4. 配置中文字体

公开脚本不硬编码本机路径。可通过参数直接指定字体：

```powershell
python scripts/render_2d_nine_cards.py `
  --analysis "<analysis_summary.json>" `
  --radar "<radar_data.json>" `
  --out "<output_directory>" `
  --period-label "2026年9月" `
  --data-cutoff "2026-09-30" `
  --font-regular "<regular_chinese_font_file>" `
  --font-bold "<bold_chinese_font_file>"
```

也可以设置：

- `MEDICAL_EVAL_FONT_REGULAR`
- `MEDICAL_EVAL_FONT_BOLD`

若系统可按字体文件名解析 Noto Sans CJK、思源黑体或微软雅黑，可省略字体参数；生产环境建议显式指定并固定字体版本。

### 5. 检查发布包

渲染完成后会生成 9 张 `900×1500` PNG、总览图和重点卡片的 375 px 移动端预览。随后执行：

```powershell
python scripts/validate_package.py "<output_directory>" `
  --copy "<wechat_copy.md>" `
  --logo "assets/shanjia-pangolin-logo.png"

python scripts/count_markdown.py "<wechat_copy.md>" --max-chars 900
```

程序校验通过后，仍需人工查看总览图和信息最密集的卡片，确认字号、截断、脚注、产品全名和数值均可读。

## 推荐生产流程

```text
批准的报告/工作簿
        ↓
字段级来源登记与脱敏
        ↓
归一化 JSON + 数学复核
        ↓
九图渲染 + 公众号文案
        ↓
程序校验 + 375 px 视觉检查
        ↓
临床专家/测评负责人签字
        ↓
人工上传微信公众号后台
```

本仓库不会连接微信公众号后台，也不会自动发布内容。这样可以把数据处理、内容审查和外部发布保持为三个独立安全关口。

## 数据与医学边界

- 排名只适用于声明的批次、题目、模型版本、专科和评分口径。
- 安全闸门失败默认表示一次输出样本事件，不能自动外推为产品级结论。
- 不同月份方法不一致时只能比较名次，并必须标注方法变化。
- 相关性是描述性的，不代表因果关系。
- 输出不构成临床诊疗、采购、投资或商业背书。

详细要求见 [`SECURITY.md`](SECURITY.md) 和 [`PUBLIC_RELEASE_REVIEW.md`](PUBLIC_RELEASE_REVIEW.md)。

## 许可证与品牌

当前仓库未附加开源许可证。公开可见不等于授权复制、修改或再分发；山甲实验室可在确认代码与品牌授权范围后另行选择许可证。`assets/` 中的山甲实验室名称和 Logo 属于品牌资产，不因代码仓库公开而授予商标使用权。
