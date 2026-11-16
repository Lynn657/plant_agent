---
name: design-patterns
description: GoF 创建型、结构型、行为型模式的角色、关系与类图判别规则
tags: gof,uml,class-diagram,architecture
---

# 设计模式绘图技能

## 建立模式类图

1. 从题目识别模式名称与意图。
2. 列出抽象角色、具体角色、协作对象和客户端。
3. 用 stereotype 区分 `<<interface>>`、`<<abstract>>`。
4. 关系必须能解释模式协作，而不是只追求“看起来像”。
5. 只画与该模式有关的成员，避免把业务系统全图塞入模式图。

## 常见模式的判别关系

| 模式 | 关键关系 |
| --- | --- |
| 工厂方法 | ConcreteCreator 继承 Creator；产品实现 Product；Creator 依赖产品抽象 |
| 抽象工厂 | 具体工厂实现抽象工厂；同一产品族由同一个工厂创建 |
| 建造者 | Director 聚合 Builder；ConcreteBuilder 逐步构造 Product |
| 单例 | 私有构造器、静态实例和静态 getInstance；客户端依赖唯一实例 |
| 适配器 | Adapter 实现 Target 并委托 Adaptee |
| 桥接 | Abstraction 聚合 Implementor，两个维度独立扩展 |
| 组合 | Composite 与 Leaf 实现 Component；Composite 组合多个 Component |
| 装饰器 | Decorator 实现 Component 并聚合一个 Component，可递归包装 |
| 外观 | Facade 依赖多个子系统，客户端只依赖 Facade |
| 享元 | Factory 缓存并复用 Flyweight；内在状态共享、外在状态传入 |
| 代理 | Proxy 与 RealSubject 实现同一 Subject；Proxy 控制 RealSubject 访问 |
| 职责链 | Handler 持有后继 Handler；请求沿链传递 |
| 命令 | Invoker 持有 Command；ConcreteCommand 调用 Receiver |
| 解释器 | 终结/非终结表达式实现 AbstractExpression；非终结表达式组合子表达式 |
| 迭代器 | ConcreteIterator 实现 Iterator 并访问 Aggregate |
| 中介者 | Colleague 只与 Mediator 通信，减少多对多耦合 |
| 备忘录 | Originator 创建/恢复 Memento；Caretaker 保存快照 |
| 观察者 | Subject 聚合 Observer；状态变化后 notify 全部观察者 |
| 状态 | Context 聚合 State；具体状态负责行为与转换 |
| 策略 | Context 聚合 Strategy；算法族可替换 |
| 模板方法 | 抽象类定义骨架，具体子类实现可变步骤 |
| 访问者 | Element.accept(Visitor)，通过双重分派扩展操作 |

## 易错点

- 工厂方法不是简单工厂；简单工厂通常不是 GoF 模式。
- 策略解决算法可替换，状态解决对象行为随状态改变。
- 装饰器与代理结构相似，但装饰器用于叠加职责，代理用于控制访问。
- 组合不等于组合关系：Composite 模式通常含“整体-部分”的组合/聚合关系。
- 观察者图中 Subject 依赖抽象 Observer，不能只依赖某一个具体观察者。

用户只给出模式名称时，输出经典角色结构，并在 notes 中说明“可替换为题目业务类名”。
