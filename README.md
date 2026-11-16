# PlantAgent

面向软件工程与设计模式的本地绘图代理。输入题目信息，代理会规划、加载领域知识、生成结构化图表、渲染 SVG/Mermaid，并执行一次结构自检。

## 快速开始

Windows 双击 `start.bat`，或在该目录运行：

```powershell
python run.py
```

浏览器会自动打开 `http://127.0.0.1:8765`。程序仅使用 Python 标准库，不需要安装额外依赖。

不配置模型也可以直接使用。此时进入**离线模板模式**，内置 23 个 GoF 设计模式，以及常见用例、时序、状态、ER、活动、组件、部署与数据流图模板。要处理任意业务题目，请在 `.env` 中配置 OpenAI 兼容接口或 Anthropic：

```powershell
Copy-Item .env.example .env
notepad .env
```

OpenAI 兼容接口示例：

```dotenv
PLANT_AGENT_PROVIDER=openai
PLANT_AGENT_OPENAI_API_KEY=sk-your-key
PLANT_AGENT_BASE_URL=https://api.openai.com/v1
PLANT_AGENT_MODEL=gpt-4.1-mini
```

Anthropic 示例：

```dotenv
PLANT_AGENT_PROVIDER=anthropic
PLANT_AGENT_ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_BASE_URL=https://api.anthropic.com
MODEL_ID=claude-sonnet-4-5
```

## 支持的图

- 类图与 GoF 设计模式类图
- 时序图
- 用例图
- 活动图
- 状态图
- ER 图
- 组件图
- 部署图
- 数据流图
- 普通流程图

每次运行同时生成：

- 自包含 SVG，可直接用于论文、PPT 和文档
- Mermaid 源码
- 可编辑的 DiagramSpec JSON
- 会话记录、执行轨迹与待办计划

## 代理能力

本项目吸收了 `learn-claude-code` 中 s01-s09 的核心机制，并按绘图任务做了收敛：

| 课程机制 | PlantAgent 中的实现 |
| --- | --- |
| Agent Loop | `plant_agent/agent.py` 中模型调用、工具结果回填、停止条件 |
| Tool Dispatch | 技能、计划、绘图、校验、记忆、MCP 等统一工具派发 |
| Todo | `set_plan` 工具和持久化计划状态 |
| Subagent | `delegate_review` 使用无历史上下文评审 |
| Skill Loading | 启动只注入技能目录，正文由 `load_skill` 按需加载 |
| Context Compact | 旧工具结果裁剪与超阈值关键状态压缩 |
| Persistent Tasks | 会话 JSON 保存题目、规格、计划、轨迹和产物 |
| Background Tasks | SVG 与 Mermaid 在后台线程并行渲染 |
| Agent Team | `review_panel` 由 UML 与需求两个独立评审员并行复核 |

## MCP 外接工具

编辑 `config/mcp_servers.json` 添加 stdio MCP server。示例：

```json
{
  "mcpServers": {
    "my-server": {
      "enabled": true,
      "command": "npx",
      "args": ["-y", "your-mcp-server-package"],
      "policy": {
        "*": "confirm",
        "search": "allow"
      }
    }
  }
}
```

代理可调用 `connect_mcp` 启动服务；成功后发现的新工具会以 `mcp__server__tool` 出现在下一轮工具池中。

宿主策略可取：

- `allow`：可直接调用
- `confirm`：需要用户授权，当前 Web 端会拒绝并要求显式改为 `allow`
- `deny`：禁止调用

内置 `uml-lint` MCP server 默认启用，用来演示真实 MCP stdio 握手并提供 `validate_spec`、`conventions` 两个工具。它只允许这两个精确工具，其他工具默认拒绝。

## 常用命令

```powershell
# 启动工作台，不自动打开浏览器
python run.py --no-browser

# 生成一个离线示例会话
python run.py --demo "画出观察者模式类图" --kind class

# 运行测试
python -m unittest discover -s tests -v
```

## 目录

```text
plant_agent/
├─ run.py                     # 启动入口
├─ plant_agent/
│  ├─ agent.py                # 代理循环、工具、上下文压缩
│  ├─ providers.py            # OpenAI compatible / Anthropic 适配
│  ├─ render.py               # 自包含 SVG 布局与渲染
│  ├─ mermaid.py              # Mermaid 导出
│  ├─ validation.py           # DiagramSpec 校验
│  ├─ templates.py            # 离线模式与设计模式模板
│  ├─ mcp.py                  # MCP stdio 客户端
│  └─ server.py               # 本地 Web API
├─ skills/                    # 按需加载知识
├─ config/mcp_servers.json    # MCP server 配置
├─ mcp_servers/               # 内置 UML 校验 MCP server
├─ web/                       # 无构建步骤的前端
├─ data/sessions/             # 历史会话与产物
└─ tests/
```

## 数据与隐私

- 服务默认只监听 `127.0.0.1`。
- 会话保存在本机 `data/sessions`。
- 只有配置在线模型时，题目与当前图表上下文才会发送到所配置的模型接口。
- MCP server 是独立子进程。外部工具权限由本地 `policy` 控制，不信任 server 自报的只读属性。
