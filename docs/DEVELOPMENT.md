# Ada 开发指南

> 本文档面向 Ada 开发者，介绍如何扩展和定制 Ada。

## 目录

1. [快速开始](#快速开始)
2. [创建自定义技能](#创建自定义技能)
3. [事件系统](#事件系统)
4. [记忆系统](#记忆系统)
5. [API 参考](#api-参考)
6. [测试](#测试)
7. [部署](#部署)

---

## 快速开始

### 环境设置

```bash
# 克隆仓库
git clone https://github.com/nebula/ada.git
cd ada

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
make test

# 启动开发服务器
make dev
```

### 项目结构

```
Ada/
├── src/ada/           # 核心源码
│   ├── core/          # 核心组件
│   ├── skill/         # 技能系统
│   ├── memory/        # 记忆系统
│   ├── events/        # 事件系统
│   └── intent/        # 意图解析
├── platform/ada/      # 平台适配
├── security/ada/      # 安全模块
├── ui/gtk/            # GTK 界面
├── cli/               # 命令行工具
├── api/               # REST API
├── skills/            # 技能包
├── tests/             # 测试用例
└── docs/              # 文档
```

---

## 创建自定义技能

### 方式一：Python 类

创建 `skills/my_skill/__init__.py`:

```python
from ada.skill.base import Skill, SkillMetadata, SkillContext, SkillResult

class MyCustomSkill(Skill):
    """自定义技能"""

    metadata = SkillMetadata(
        id="user.my.custom",
        name="我的技能",
        version="1.0.0",
        description="技能描述",
        author="Your Name",
        category="custom",
        tags=["自定义", "example"],
        permissions=["file.read"],
        examples=["示例命令1", "示例命令2"]
    )

    def can_handle(self, context: SkillContext) -> float:
        """判断是否能处理此输入，返回 0.0-1.0 的分数"""
        if "关键词" in context.user_input:
            return 0.8
        return 0.0

    async def execute(self, context: SkillContext) -> SkillResult:
        """执行技能"""
        user_input = context.user_input
        entities = context.entities

        # 你的逻辑
        result = do_something(user_input)

        if result:
            return SkillResult.ok(
                message="执行成功",
                output={"data": result}
            )
        else:
            return SkillResult.fail("执行失败")
```

### 方式二：SKILL.md + handler.py

创建 `skills/my_skill/SKILL.md`:

```markdown
---
id: user.weather
name: 天气查询
version: 1.0.0
description: 查询城市天气
author: User
category: information
tags: [weather, 天气]
permissions: [network.request]
examples:
  - 今天北京天气
  - 上海明天会下雨吗
---

# 天气查询

查询全球城市的天气情况。
```

创建 `skills/my_skill/handler.py`:

```python
from ada.skill.base import SkillContext, SkillResult

async def handle(context: SkillContext) -> SkillResult:
    """处理天气查询"""
    city = context.entities.get("city", "北京")

    # 查询天气
    weather = await fetch_weather(city)

    return SkillResult.ok(
        message=f"{city} 今天{weather['condition']}，温度{weather['temp']}°C",
        output=weather
    )
```

### 技能上下文

```python
@dataclass
class SkillContext:
    user_input: str                  # 用户输入
    entities: Dict[str, Any]         # 提取的实体
    conversation_history: List       # 对话历史
    user_preferences: Dict           # 用户偏好
    executor: Executor               # 执行器
    progress_callback: Callable      # 进度回调
```

### 技能结果

```python
# 成功
return SkillResult.ok(
    message="操作完成",
    output={"key": "value"}
)

# 失败
return SkillResult.fail("错误原因")

# 需要确认
return SkillResult(
    success=True,
    requires_confirmation=True,
    confirmation_message="确认执行此操作？",
    output={"plans": plans}
)

# 进度更新
context.progress_callback(50, "正在处理...")
```

---

## 事件系统

### 订阅事件

```python
from ada.events import EventBus, EventType

bus = EventBus()

# 订阅特定事件
def on_focus_change(event):
    print(f"Focus changed: {event.data}")

bus.subscribe(EventType.FOCUS_CHANGED, on_focus_change)

# 订阅多种事件
bus.subscribe(
    [EventType.WINDOW_ACTIVATED, EventType.WINDOW_CLOSED],
    handle_window_event
)

# 订阅所有事件
bus.subscribe(None, log_all_events)

# 带过滤器
bus.subscribe(
    EventType.USER_MESSAGE,
    handle_important,
    filter_func=lambda e: "重要" in e.data.get("message", "")
)
```

### 发布事件

```python
from ada.events import Event

# 发布自定义事件
event = Event.custom(
    "my.event",
    {"data": "value"},
    source="my_skill"
)

await bus.publish(event)
```

### 事件类型

```python
class EventType(Enum):
    # AT-SPI 事件
    FOCUS_CHANGED
    WINDOW_ACTIVATED
    STATE_CHANGED
    TEXT_CHANGED

    # 用户事件
    USER_MESSAGE
    KEY_PRESSED
    MOUSE_CLICKED

    # 系统事件
    CLIPBOARD_CHANGED
    NOTIFICATION_RECEIVED

    # Ada 事件
    AGENT_STARTED
    SKILL_EXECUTED
    CUSTOM
```

---

## 记忆系统

### 存储记忆

```python
from ada.memory.base import Memory, MemoryType

memory = Memory(
    content="用户喜欢深色模式",
    memory_type=MemoryType.SEMANTIC,
    importance=0.8,
    tags=["preference", "ui"]
)

await memory_store.save(memory)
```

### 搜索记忆

```python
from ada.memory.base import MemoryQuery

query = MemoryQuery(
    text="用户偏好",
    memory_types=[MemoryType.SEMANTIC],
    limit=10
)

results = memory_store.search(query)

for mem in results:
    print(f"{mem.content} (importance: {mem.importance})")
```

### 记忆类型

- `EPISODIC` - 事件和经历
- `SEMANTIC` - 事实和知识
- `PROCEDURAL` - 技能和程序
- `WORKING` - 临时工作记忆
- `CONVERSATION` - 对话历史

---

## API 参考

### REST API

```bash
# 处理输入
POST /process
{
    "text": "打开 Firefox",
    "context": {}
}

# 响应
{
    "success": true,
    "message": "已启动 Firefox",
    "skill_used": "builtin.app.launcher"
}

# 列出技能
GET /skills

# 执行技能
POST /skills/{skill_id}/execute
{
    "input_text": "整理下载文件夹"
}

# 搜索记忆
POST /memory/search
{
    "query": "用户偏好",
    "limit": 10
}
```

### WebSocket API

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// 发送消息
ws.send(JSON.stringify({
    type: 'process',
    text: '你好'
}));

// 接收响应
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'status') {
        console.log('Status:', data.status);
    } else if (data.type === 'response') {
        console.log('Response:', data.message);
    }
};
```

### D-Bus 接口

```python
import dbus

bus = dbus.SessionBus()
ada = bus.get_object('org.nebula.Ada', '/org/nebula/Ada')

# 处理输入
response = ada.ProcessInput('打开 Firefox')

# 获取状态
status = ada.GetStatus()
```

---

## 测试

### 单元测试

```python
# tests/test_my_skill.py
import pytest
from ada.skill.base import SkillContext, SkillResult
from skills.my_skill import MyCustomSkill

@pytest.fixture
def skill():
    return MyCustomSkill()

def test_can_handle(skill):
    context = SkillContext(
        user_input="测试关键词匹配",
        entities={}
    )

    score = skill.can_handle(context)
    assert score > 0.5

@pytest.mark.asyncio
async def test_execute(skill):
    context = SkillContext(
        user_input="执行测试",
        entities={}
    )

    result = await skill.execute(context)
    assert result.success
```

### 运行测试

```bash
# 所有测试
pytest tests/

# 带覆盖率
pytest --cov=ada tests/

# 特定测试
pytest tests/test_my_skill.py -v

# 异步测试
pytest tests/ -k "async"
```

---

## 部署

### Flatpak

```bash
# 构建
flatpak-builder build org.nebula.Ada.json

# 安装
flatpak-builder --user --install build org.nebula.Ada.json

# 运行
flatpak run org.nebula.Ada
```

### Systemd 服务

```bash
# 安装
ada install

# 启用
systemctl --user enable ada

# 启动
systemctl --user start ada

# 查看状态
systemctl --user status ada
```

### 手动部署

```bash
# 安装依赖
pip install -r requirements.txt

# 启动守护进程
ada daemon

# 启动 API 服务器
uvicorn ada.api.main:app --host 0.0.0.0 --port 8000
```

---

## 最佳实践

### 技能设计

1. **单一职责** - 每个技能只做一件事
2. **明确描述** - 提供清晰的描述和示例
3. **权限最小化** - 只请求必要的权限
4. **优雅降级** - 处理功能不可用的情况
5. **用户确认** - 破坏性操作需要确认

### 错误处理

```python
async def execute(self, context: SkillContext) -> SkillResult:
    try:
        result = await risky_operation()

        if not result:
            return SkillResult.fail("操作未完成")

        return SkillResult.ok(message="成功")

    except PermissionError:
        return SkillResult.fail("权限不足")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return SkillResult.fail(f"发生错误: {e}")
```

### 性能优化

1. 使用异步 I/O
2. 缓存频繁访问的数据
3. 避免在 `can_handle` 中执行耗时操作
4. 使用进度回调处理长时间操作

---

## 贡献指南

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 代码规范

- 使用 Black 格式化
- 通过 Ruff 检查
- 添加类型注解
- 编写测试用例
- 更新文档

---

## 常见问题

**Q: 技能没有被加载？**

A: 检查技能目录配置和文件结构。确保 `__init__.py` 或 `SKILL.md` 存在。

**Q: 权限被拒绝？**

A: 在配置文件中启用相应权限，或在运行时请求授权。

**Q: LLM 响应很慢？**

A: 考虑使用本地 Ollama，或配置更快的模型。

---

*更多问题请提交 Issue: https://github.com/nebula/ada/issues*
