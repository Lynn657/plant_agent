from __future__ import annotations

from typing import Any

from .models import blank_spec


PATTERNS: dict[str, dict[str, Any]] = {
    "abstract_factory": {
        "aliases": ("抽象工厂", "abstract factory"),
        "title": "抽象工厂模式",
        "nodes": [
            ("factory", "AbstractFactory", "interface", "", [], ["createProductA()", "createProductB()"]),
            ("factory1", "ConcreteFactory1", "class", "", [], ["createProductA()", "createProductB()"]),
            ("factory2", "ConcreteFactory2", "class", "", [], ["createProductA()", "createProductB()"]),
            ("product_a", "AbstractProductA", "interface", "", [], []),
            ("product_b", "AbstractProductB", "interface", "", [], []),
            ("product_a1", "ProductA1", "class", "", [], []),
            ("product_a2", "ProductA2", "class", "", [], []),
            ("product_b1", "ProductB1", "class", "", [], []),
            ("product_b2", "ProductB2", "class", "", [], []),
        ],
        "edges": [
            ("factory1", "factory", "realization", ""),
            ("factory2", "factory", "realization", ""),
            ("product_a1", "product_a", "realization", ""),
            ("product_a2", "product_a", "realization", ""),
            ("product_b1", "product_b", "realization", ""),
            ("product_b2", "product_b", "realization", ""),
            ("factory", "product_a", "dependency", "创建"),
            ("factory", "product_b", "dependency", "创建"),
        ],
    },
    "builder": {
        "aliases": ("建造者", "builder"),
        "title": "建造者模式",
        "nodes": [
            ("director", "Director", "class", "", ["builder: Builder"], ["construct()"]),
            ("builder", "Builder", "interface", "", [], ["reset()", "buildPart()", "getResult()"]),
            ("concrete", "ConcreteBuilder", "class", "", ["product: Product"], ["reset()", "buildPart()", "getResult()"]),
            ("product", "Product", "class", "", ["parts: Part[]"], ["addPart(part)"]),
        ],
        "edges": [
            ("director", "builder", "aggregation", "1"),
            ("concrete", "builder", "realization", ""),
            ("concrete", "product", "composition", "创建"),
        ],
    },
    "factory_method": {
        "aliases": ("工厂方法", "factory method", "工厂模式"),
        "title": "工厂方法模式",
        "nodes": [
            ("creator", "Creator", "abstract", "", [], ["factoryMethod(): Product", "operation()"]),
            ("concrete_creator", "ConcreteCreator", "class", "", [], ["factoryMethod(): Product"]),
            ("product", "Product", "interface", "", [], ["use()"]),
            ("concrete_product", "ConcreteProduct", "class", "", [], ["use()"]),
        ],
        "edges": [
            ("concrete_creator", "creator", "inheritance", ""),
            ("concrete_product", "product", "realization", ""),
            ("creator", "product", "dependency", "创建"),
        ],
    },
    "prototype": {
        "aliases": ("原型", "prototype"),
        "title": "原型模式",
        "nodes": [
            ("prototype", "Prototype", "interface", "", [], ["clone(): Prototype"]),
            ("concrete", "ConcretePrototype", "class", "", ["field: State"], ["clone(): Prototype"]),
            ("client", "Client", "class", "", [], ["copy(obj)"]),
        ],
        "edges": [
            ("concrete", "prototype", "realization", ""),
            ("client", "prototype", "dependency", "复制"),
        ],
    },
    "singleton": {
        "aliases": ("单例", "singleton"),
        "title": "单例模式",
        "nodes": [
            (
                "singleton",
                "Singleton",
                "class",
                "",
                ["- instance: Singleton", "- Singleton()"],
                ["+ getInstance(): Singleton", "+ operation()"],
            ),
            ("client", "Client", "class", "", [], ["useSingleton()"]),
        ],
        "edges": [("client", "singleton", "dependency", "getInstance")],
    },
    "adapter": {
        "aliases": ("适配器", "adapter"),
        "title": "适配器模式",
        "nodes": [
            ("target", "Target", "interface", "", [], ["request()"]),
            ("adapter", "Adapter", "class", "", ["adaptee: Adaptee"], ["request()"]),
            ("adaptee", "Adaptee", "class", "", [], ["specificRequest()"]),
            ("client", "Client", "class", "", [], ["use(Target)"]),
        ],
        "edges": [
            ("adapter", "target", "realization", ""),
            ("adapter", "adaptee", "association", "委托"),
            ("client", "target", "dependency", ""),
        ],
    },
    "bridge": {
        "aliases": ("桥接", "bridge"),
        "title": "桥接模式",
        "nodes": [
            ("abstraction", "Abstraction", "abstract", "", ["implementor: Implementor"], ["operation()"]),
            ("refined", "RefinedAbstraction", "class", "", [], ["operation()"]),
            ("implementor", "Implementor", "interface", "", [], ["operationImpl()"]),
            ("impl_a", "ConcreteImplementorA", "class", "", [], ["operationImpl()"]),
            ("impl_b", "ConcreteImplementorB", "class", "", [], ["operationImpl()"]),
        ],
        "edges": [
            ("refined", "abstraction", "inheritance", ""),
            ("abstraction", "implementor", "aggregation", "1"),
            ("impl_a", "implementor", "realization", ""),
            ("impl_b", "implementor", "realization", ""),
        ],
    },
    "composite": {
        "aliases": ("组合模式", "composite"),
        "title": "组合模式",
        "nodes": [
            ("component", "Component", "interface", "", [], ["operation()", "add(Component)", "remove(Component)"]),
            ("leaf", "Leaf", "class", "", [], ["operation()"]),
            ("composite", "Composite", "class", "", ["children: Component[]"], ["operation()", "add(Component)", "remove(Component)"]),
        ],
        "edges": [
            ("leaf", "component", "realization", ""),
            ("composite", "component", "realization", ""),
            ("composite", "component", "composition", "0..*"),
        ],
    },
    "decorator": {
        "aliases": ("装饰器", "装饰", "decorator"),
        "title": "装饰器模式",
        "nodes": [
            ("component", "Component", "interface", "", [], ["operation()"]),
            ("concrete", "ConcreteComponent", "class", "", [], ["operation()"]),
            ("decorator", "Decorator", "abstract", "", ["component: Component"], ["operation()"]),
            ("decorator_a", "ConcreteDecoratorA", "class", "", ["addedState"], ["operation()"]),
        ],
        "edges": [
            ("concrete", "component", "realization", ""),
            ("decorator", "component", "realization", ""),
            ("decorator_a", "decorator", "inheritance", ""),
            ("decorator", "component", "aggregation", "1"),
        ],
    },
    "facade": {
        "aliases": ("外观", "门面", "facade"),
        "title": "外观模式",
        "nodes": [
            ("facade", "Facade", "class", "", [], ["operation()"]),
            ("subsystem_a", "SubsystemA", "class", "", [], ["operationA()"]),
            ("subsystem_b", "SubsystemB", "class", "", [], ["operationB()"]),
            ("subsystem_c", "SubsystemC", "class", "", [], ["operationC()"]),
            ("client", "Client", "class", "", [], ["request()"]),
        ],
        "edges": [
            ("client", "facade", "dependency", ""),
            ("facade", "subsystem_a", "association", ""),
            ("facade", "subsystem_b", "association", ""),
            ("facade", "subsystem_c", "association", ""),
        ],
    },
    "flyweight": {
        "aliases": ("享元", "flyweight"),
        "title": "享元模式",
        "nodes": [
            ("flyweight", "Flyweight", "interface", "", [], ["operation(extrinsicState)"]),
            ("concrete", "ConcreteFlyweight", "class", "", ["intrinsicState"], ["operation(extrinsicState)"]),
            ("factory", "FlyweightFactory", "class", "", ["pool: Map"], ["getFlyweight(key)"]),
            ("client", "Client", "class", "", [], ["use()"]),
        ],
        "edges": [
            ("concrete", "flyweight", "realization", ""),
            ("factory", "flyweight", "dependency", "创建/缓存"),
            ("client", "factory", "dependency", ""),
        ],
    },
    "proxy": {
        "aliases": ("代理", "proxy"),
        "title": "代理模式",
        "nodes": [
            ("subject", "Subject", "interface", "", [], ["request()"]),
            ("real", "RealSubject", "class", "", [], ["request()"]),
            ("proxy", "Proxy", "class", "", ["realSubject: RealSubject"], ["request()"]),
            ("client", "Client", "class", "", [], ["request()"]),
        ],
        "edges": [
            ("real", "subject", "realization", ""),
            ("proxy", "subject", "realization", ""),
            ("proxy", "real", "association", "控制访问"),
            ("client", "subject", "dependency", ""),
        ],
    },
    "chain": {
        "aliases": ("职责链", "责任链", "chain of responsibility"),
        "title": "职责链模式",
        "nodes": [
            ("handler", "Handler", "interface", "", [], ["setNext(Handler)", "handle(request)"]),
            ("base", "BaseHandler", "abstract", "", ["next: Handler"], ["setNext(Handler)", "handle(request)"]),
            ("handler_a", "ConcreteHandlerA", "class", "", [], ["handle(request)"]),
            ("handler_b", "ConcreteHandlerB", "class", "", [], ["handle(request)"]),
            ("client", "Client", "class", "", [], ["submit(request)"]),
        ],
        "edges": [
            ("base", "handler", "realization", ""),
            ("handler_a", "base", "inheritance", ""),
            ("handler_b", "base", "inheritance", ""),
            ("base", "handler", "association", "next"),
            ("client", "handler", "dependency", ""),
        ],
    },
    "command": {
        "aliases": ("命令模式", "command"),
        "title": "命令模式",
        "nodes": [
            ("command", "Command", "interface", "", [], ["execute()", "undo()"]),
            ("concrete", "ConcreteCommand", "class", "", ["receiver: Receiver"], ["execute()", "undo()"]),
            ("invoker", "Invoker", "class", "", ["commands: Command[]"], ["setCommand(Command)", "execute()"]),
            ("receiver", "Receiver", "class", "", [], ["action()"]),
        ],
        "edges": [
            ("concrete", "command", "realization", ""),
            ("invoker", "command", "aggregation", "0..*"),
            ("concrete", "receiver", "association", "调用"),
        ],
    },
    "interpreter": {
        "aliases": ("解释器", "interpreter"),
        "title": "解释器模式",
        "nodes": [
            ("expression", "AbstractExpression", "interface", "", [], ["interpret(Context)"]),
            ("terminal", "TerminalExpression", "class", "", [], ["interpret(Context)"]),
            ("nonterminal", "NonterminalExpression", "class", "", ["children: Expression[]"], ["interpret(Context)"]),
            ("context", "Context", "class", "", ["state"], []),
            ("client", "Client", "class", "", [], ["buildTree()"]),
        ],
        "edges": [
            ("terminal", "expression", "realization", ""),
            ("nonterminal", "expression", "realization", ""),
            ("nonterminal", "expression", "composition", "子表达式"),
            ("client", "expression", "dependency", "构建语法树"),
        ],
    },
    "iterator": {
        "aliases": ("迭代器", "iterator"),
        "title": "迭代器模式",
        "nodes": [
            ("iterator", "Iterator", "interface", "", [], ["hasNext()", "next()"]),
            ("concrete_iterator", "ConcreteIterator", "class", "", [], ["hasNext()", "next()"]),
            ("aggregate", "Aggregate", "interface", "", [], ["createIterator(): Iterator"]),
            ("concrete_aggregate", "ConcreteAggregate", "class", "", ["items: T[]"], ["createIterator(): Iterator"]),
            ("client", "Client", "class", "", [], ["traverse()"]),
        ],
        "edges": [
            ("concrete_iterator", "iterator", "realization", ""),
            ("concrete_aggregate", "aggregate", "realization", ""),
            ("concrete_iterator", "concrete_aggregate", "association", "游标"),
            ("client", "iterator", "dependency", ""),
        ],
    },
    "mediator": {
        "aliases": ("中介者", "mediator"),
        "title": "中介者模式",
        "nodes": [
            ("mediator", "Mediator", "interface", "", [], ["notify(sender, event)"]),
            ("concrete_mediator", "ConcreteMediator", "class", "", ["colleagues: Colleague[]"], ["notify(sender, event)"]),
            ("colleague", "Colleague", "abstract", "", ["mediator: Mediator"], ["send(message)", "receive(message)"]),
            ("colleague_a", "ConcreteColleagueA", "class", "", [], ["receive(message)"]),
            ("colleague_b", "ConcreteColleagueB", "class", "", [], ["receive(message)"]),
        ],
        "edges": [
            ("concrete_mediator", "mediator", "realization", ""),
            ("colleague_a", "colleague", "inheritance", ""),
            ("colleague_b", "colleague", "inheritance", ""),
            ("colleague", "mediator", "association", ""),
            ("concrete_mediator", "colleague", "aggregation", "协调"),
        ],
    },
    "memento": {
        "aliases": ("备忘录", "memento"),
        "title": "备忘录模式",
        "nodes": [
            ("originator", "Originator", "class", "", ["state"], ["createMemento()", "restore(Memento)"]),
            ("memento", "Memento", "class", "", ["- state"], ["getState()"]),
            ("caretaker", "Caretaker", "class", "", ["history: Memento[]"], ["save()", "undo()"]),
        ],
        "edges": [
            ("originator", "memento", "dependency", "创建"),
            ("caretaker", "memento", "aggregation", "保存"),
        ],
    },
    "observer": {
        "aliases": ("观察者", "observer", "发布订阅", "pub sub"),
        "title": "观察者模式",
        "nodes": [
            ("subject", "Subject", "interface", "", [], ["attach(Observer)", "detach(Observer)", "notify()"]),
            ("concrete_subject", "ConcreteSubject", "class", "", ["state", "observers: Observer[]"], ["getState()", "setState(state)"]),
            ("observer", "Observer", "interface", "", [], ["update(subject)"]),
            ("concrete_observer", "ConcreteObserver", "class", "", ["observerState"], ["update(subject)"]),
        ],
        "edges": [
            ("concrete_subject", "subject", "realization", ""),
            ("concrete_observer", "observer", "realization", ""),
            ("subject", "observer", "aggregation", "0..*"),
            ("concrete_observer", "concrete_subject", "dependency", "读取状态"),
        ],
    },
    "state": {
        "aliases": ("状态模式", "state pattern"),
        "title": "状态模式",
        "nodes": [
            ("context", "Context", "class", "", ["state: State"], ["request()", "changeState(State)"]),
            ("state", "State", "interface", "", [], ["handle(context)"]),
            ("state_a", "ConcreteStateA", "class", "", [], ["handle(context)"]),
            ("state_b", "ConcreteStateB", "class", "", [], ["handle(context)"]),
        ],
        "edges": [
            ("context", "state", "aggregation", "1"),
            ("state_a", "state", "realization", ""),
            ("state_b", "state", "realization", ""),
            ("state_a", "state_b", "dependency", "状态转换"),
        ],
    },
    "strategy": {
        "aliases": ("策略", "strategy"),
        "title": "策略模式",
        "nodes": [
            ("context", "Context", "class", "", ["strategy: Strategy"], ["setStrategy(Strategy)", "execute()"]),
            ("strategy", "Strategy", "interface", "", [], ["execute(data)"]),
            ("strategy_a", "ConcreteStrategyA", "class", "", [], ["execute(data)"]),
            ("strategy_b", "ConcreteStrategyB", "class", "", [], ["execute(data)"]),
        ],
        "edges": [
            ("context", "strategy", "aggregation", "1"),
            ("strategy_a", "strategy", "realization", ""),
            ("strategy_b", "strategy", "realization", ""),
        ],
    },
    "template_method": {
        "aliases": ("模板方法", "template method"),
        "title": "模板方法模式",
        "nodes": [
            ("abstract", "AbstractClass", "abstract", "", [], ["templateMethod()", "# primitiveOperation()"]),
            ("concrete", "ConcreteClass", "class", "", [], ["# primitiveOperation()"]),
            ("client", "Client", "class", "", [], ["templateMethod()"]),
        ],
        "edges": [
            ("concrete", "abstract", "inheritance", ""),
            ("client", "abstract", "dependency", ""),
        ],
    },
    "visitor": {
        "aliases": ("访问者", "visitor"),
        "title": "访问者模式",
        "nodes": [
            ("visitor", "Visitor", "interface", "", [], ["visitElementA(ElementA)", "visitElementB(ElementB)"]),
            ("concrete_visitor_a", "ConcreteVisitorA", "class", "", [], ["visitElementA(ElementA)", "visitElementB(ElementB)"]),
            ("element", "Element", "interface", "", [], ["accept(Visitor)"]),
            ("element_a", "ConcreteElementA", "class", "", [], ["accept(Visitor)"]),
            ("element_b", "ConcreteElementB", "class", "", [], ["accept(Visitor)"]),
            ("object_structure", "ObjectStructure", "class", "", ["elements: Element[]"], ["accept(Visitor)"]),
        ],
        "edges": [
            ("concrete_visitor_a", "visitor", "realization", ""),
            ("element_a", "element", "realization", ""),
            ("element_b", "element", "realization", ""),
            ("element", "visitor", "dependency", "double dispatch"),
            ("object_structure", "element", "aggregation", "0..*"),
        ],
    },
}


def build_offline_diagram(
    prompt: str,
    requested_kind: str = "auto",
    theme: str = "ocean",
) -> dict[str, Any]:
    text = prompt.strip()
    lower = text.lower()
    kind = _resolve_kind(requested_kind, lower)
    if kind in {"class", "auto"}:
        for key, pattern in PATTERNS.items():
            if any(alias in lower for alias in pattern["aliases"]):
                return _pattern_spec(key, pattern, text, theme)
        kind = "class"
    if kind == "class":
        return _domain_class_spec(text, theme)
    if kind == "sequence":
        return _sequence_spec(text, lower, theme)
    if kind == "usecase":
        return _usecase_spec(text, lower, theme)
    if kind == "er":
        return _er_spec(text, lower, theme)
    if kind == "state":
        return _state_spec(text, lower, theme)
    if kind == "activity":
        return _activity_spec(text, lower, theme)
    if kind == "component":
        return _component_spec(text, theme, "component")
    if kind == "deployment":
        return _component_spec(text, theme, "deployment")
    if kind == "dfd":
        return _dfd_spec(text, theme)
    return _flow_spec(text, theme)


def _resolve_kind(requested: str, lower: str) -> str:
    requested = (requested or "auto").lower()
    if requested != "auto":
        return requested
    keyword_map = [
        ("sequence", ("时序", "顺序图", "sequence", "交互")),
        ("usecase", ("用例", "use case", "actor")),
        ("er", ("er图", "e-r", "实体关系", "数据库设计")),
        ("state", ("状态图", "状态机", "state diagram", "生命周期")),
        ("activity", ("活动图", "activity")),
        ("deployment", ("部署图", "deployment", "物理架构")),
        ("component", ("组件图", "component", "微服务架构", "系统架构")),
        ("dfd", ("数据流", "dfd")),
        ("class", ("类图", "class diagram", "设计模式")),
        ("flow", ("流程", "flowchart", "步骤")),
    ]
    for kind, words in keyword_map:
        if any(word in lower for word in words):
            return kind
    if any(pattern["aliases"][0] in lower for pattern in PATTERNS.values()):
        return "class"
    return "flow"


def _pattern_spec(key: str, pattern: dict[str, Any], prompt: str, theme: str) -> dict[str, Any]:
    spec = blank_spec(pattern["title"], "class")
    spec["theme"] = theme
    spec["direction"] = "LR"
    spec["subtitle"] = "GoF 设计模式 · 角色协作与静态结构"
    spec["nodes"] = [
        {
            "id": node_id,
            "label": label,
            "type": node_type,
            "stereotype": stereotype,
            "attributes": attrs,
            "methods": methods,
        }
        for node_id, label, node_type, stereotype, attrs, methods in pattern["nodes"]
    ]
    spec["edges"] = [
        {"from": source, "to": target, "type": edge_type, "label": label}
        for source, target, edge_type, label in pattern["edges"]
    ]
    spec["notes"] = [
        "请求摘要：" + prompt[:96],
        "图示聚焦角色结构与关系；具体业务类名可按题目进一步替换。",
    ]
    return spec


def _domain_class_spec(prompt: str, theme: str) -> dict[str, Any]:
    if any(word in prompt for word in ("图书", "借阅", "图书馆")):
        nodes = [
            ("Reader", "读者", "class", ["readerId", "name"], ["borrow(Book)", "returnBook(Book)"]),
            ("Book", "图书", "class", ["isbn", "title", "status"], ["isAvailable()"]),
            ("Loan", "借阅记录", "class", ["loanDate", "dueDate"], ["overdue()"]),
            ("Librarian", "图书管理员", "class", ["staffId"], ["manageBook()"]),
        ]
        edges = [
            ("Reader", "Loan", "association", "1..*"),
            ("Loan", "Book", "association", "1"),
            ("Librarian", "Book", "association", "维护"),
        ]
    elif any(word in prompt for word in ("订单", "商城", "电商", "支付")):
        nodes = [
            ("Customer", "客户", "class", ["customerId", "name"], ["placeOrder()"]),
            ("Order", "订单", "class", ["orderId", "status", "total"], ["submit()", "cancel()"]),
            ("OrderItem", "订单项", "class", ["quantity", "price"], ["subtotal()"]),
            ("Product", "商品", "class", ["productId", "name", "price"], ["available()"]),
            ("Payment", "支付", "class", ["paymentId", "method"], ["pay(amount)"]),
        ]
        edges = [
            ("Customer", "Order", "association", "1..*"),
            ("Order", "OrderItem", "composition", "1..*"),
            ("OrderItem", "Product", "association", "1"),
            ("Order", "Payment", "association", "0..1"),
        ]
    else:
        nodes = [
            ("Entity", "业务实体", "class", ["id", "状态"], ["校验()"]),
            ("Repository", "仓储", "class", ["数据源"], ["保存()", "查询()"]),
            ("Service", "领域服务", "class", ["仓储"], ["执行用例()"]),
            ("Controller", "接口控制器", "class", ["服务"], ["接收请求()"]),
        ]
        edges = [
            ("Controller", "Service", "dependency", "调用"),
            ("Service", "Entity", "association", "处理"),
            ("Service", "Repository", "association", "持久化"),
            ("Repository", "Entity", "dependency", "读取"),
        ]
    spec = blank_spec(_title_from_prompt(prompt, "领域类图"), "class")
    spec["theme"] = theme
    spec["subtitle"] = "领域实体、职责与关系（离线模板）"
    spec["nodes"] = [
        {
            "id": node_id,
            "label": label,
            "type": node_type,
            "attributes": attrs,
            "methods": methods,
        }
        for node_id, label, node_type, attrs, methods in nodes
    ]
    spec["edges"] = [
        {"from": a, "to": b, "type": relation, "label": label}
        for a, b, relation, label in edges
    ]
    spec["notes"] = ["离线模式依据常见业务场景生成；配置模型后可针对题目自由扩展。"]
    return spec


def _sequence_spec(prompt: str, lower: str, theme: str) -> dict[str, Any]:
    if any(word in lower for word in ("支付", "payment", "付款")):
        actors = [("user", "用户", "actor"), ("client", "收银台", "participant"), ("order", "订单服务", "participant"), ("pay", "支付网关", "participant"), ("bank", "银行/渠道", "participant")]
        messages = [
            ("user", "client", "提交支付", "sync"),
            ("client", "order", "创建支付单", "sync"),
            ("order", "pay", "发起支付", "sync"),
            ("pay", "bank", "请求扣款", "sync"),
            ("bank", "pay", "扣款结果", "return"),
            ("pay", "order", "支付回调", "async"),
            ("order", "client", "返回订单状态", "return"),
        ]
    elif any(word in lower for word in ("登录", "login", "认证")):
        actors = [("user", "用户", "actor"), ("web", "客户端", "participant"), ("auth", "认证服务", "participant"), ("cache", "会话存储", "participant"), ("db", "用户库", "participant")]
        messages = [
            ("user", "web", "输入账号密码", "sync"),
            ("web", "auth", "提交登录请求", "sync"),
            ("auth", "db", "查询用户与凭据", "sync"),
            ("db", "auth", "返回用户记录", "return"),
            ("auth", "cache", "写入会话", "sync"),
            ("auth", "web", "返回访问令牌", "return"),
            ("web", "user", "进入系统", "return"),
        ]
    else:
        actors = [("user", "用户", "actor"), ("ui", "交互界面", "participant"), ("api", "业务服务", "participant"), ("repo", "数据访问", "participant"), ("db", "数据库", "participant")]
        messages = [
            ("user", "ui", "发起业务请求", "sync"),
            ("ui", "api", "调用接口", "sync"),
            ("api", "repo", "读取/写入数据", "sync"),
            ("repo", "db", "执行 SQL", "sync"),
            ("db", "repo", "返回结果集", "return"),
            ("repo", "api", "返回领域对象", "return"),
            ("api", "ui", "返回响应", "return"),
            ("ui", "user", "展示结果", "return"),
        ]
    spec = blank_spec(_title_from_prompt(prompt, "业务交互时序图"), "sequence")
    spec["theme"] = theme
    spec["subtitle"] = "正常路径交互（离线模板）"
    spec["nodes"] = [{"id": node_id, "label": label, "type": node_type} for node_id, label, node_type in actors]
    spec["edges"] = [
        {"from": source, "to": target, "label": label, "type": edge_type, "order": index + 1}
        for index, (source, target, label, edge_type) in enumerate(messages)
    ]
    return spec


def _usecase_spec(prompt: str, lower: str, theme: str) -> dict[str, Any]:
    known_actors = [("用户", "user"), ("客户", "customer"), ("管理员", "admin"), ("教师", "teacher"), ("学生", "student"), ("商家", "merchant"), ("运营人员", "operator")]
    actors = [(node_id, label) for label, node_id in known_actors if label in prompt]
    if not actors:
        actors = [("user", "用户")]
    case_words = [
        ("登录", "登录系统"), ("注册", "注册账号"), ("下单", "提交订单"), ("支付", "支付订单"),
        ("查询", "查询信息"), ("管理", "管理数据"), ("审批", "审批申请"), ("上传", "上传资料"),
        ("下载", "下载文件"), ("发布", "发布内容"), ("评价", "提交评价"),
    ]
    cases = [case for word, case in case_words if word in prompt]
    if not cases:
        cases = (["浏览商品", "提交订单", "支付订单"] if any(x in lower for x in ("商城", "电商", "订单")) else ["完成核心业务", "查询业务状态"])
    spec = blank_spec(_title_from_prompt(prompt, "系统用例图"), "usecase")
    spec["theme"] = theme
    spec["direction"] = "LR"
    spec["subtitle"] = "参与者与功能边界（离线模板）"
    node_list = [{"id": node_id, "label": label, "type": "actor"} for node_id, label in actors]
    case_ids = []
    for index, case in enumerate(cases[:8]):
        node_id = f"uc{index + 1}"
        case_ids.append(node_id)
        node_list.append({"id": node_id, "label": case, "type": "usecase"})
    edges = []
    for actor in actors:
        for case_id in case_ids[:4]:
            edges.append({"from": actor[0], "to": case_id, "type": "association", "label": ""})
    if len(case_ids) > 1:
        edges.append({"from": case_ids[0], "to": case_ids[1], "type": "include", "label": "include"})
    spec["nodes"] = node_list
    spec["edges"] = edges
    spec["groups"] = [
        {"id": "system", "label": "系统功能边界", "nodes": case_ids}
    ]
    spec["notes"] = ["参与者置于系统边界之外；include 表示公共行为复用。"]
    return spec


def _er_spec(prompt: str, lower: str, theme: str) -> dict[str, Any]:
    if any(word in prompt for word in ("图书", "借阅", "图书馆")):
        entities = [
            ("Reader", "读者", ["reader_id PK", "name", "phone"]),
            ("Book", "图书", ["isbn PK", "title", "status"]),
            ("Loan", "借阅记录", ["loan_id PK", "reader_id FK", "isbn FK", "due_date"]),
        ]
        relations = [("Reader", "Loan", "1:N", "发起"), ("Book", "Loan", "1:N", "被借阅")]
    elif any(word in prompt for word in ("课程", "学生", "学校", "选课")):
        entities = [
            ("Student", "学生", ["student_id PK", "name", "major"]),
            ("Course", "课程", ["course_id PK", "title", "credits"]),
            ("Enrollment", "选课记录", ["student_id FK", "course_id FK", "score"]),
        ]
        relations = [("Student", "Enrollment", "1:N", "选择"), ("Course", "Enrollment", "1:N", "被选择")]
    else:
        entities = [
            ("Customer", "客户", ["customer_id PK", "name", "contact"]),
            ("Order", "订单", ["order_id PK", "customer_id FK", "status"]),
            ("OrderItem", "订单项", ["item_id PK", "order_id FK", "product_id FK", "quantity"]),
            ("Product", "商品", ["product_id PK", "name", "price"]),
        ]
        relations = [
            ("Customer", "Order", "1:N", "下单"),
            ("Order", "OrderItem", "1:N", "包含"),
            ("Product", "OrderItem", "1:N", "被购买"),
        ]
    spec = blank_spec(_title_from_prompt(prompt, "业务数据模型"), "er")
    spec["theme"] = theme
    spec["direction"] = "LR"
    spec["subtitle"] = "实体、关键属性与基数关系（离线模板）"
    spec["nodes"] = [
        {"id": entity_id, "label": label, "type": "entity", "attributes": attrs}
        for entity_id, label, attrs in entities
    ]
    spec["edges"] = [
        {"from": source, "to": target, "type": "association", "label": f"{cardinality} · {label}"}
        for source, target, cardinality, label in relations
    ]
    return spec


def _state_spec(prompt: str, lower: str, theme: str) -> dict[str, Any]:
    if any(word in prompt for word in ("订单", "order")):
        states = ["待支付", "已支付", "待发货", "已发货", "已完成", "已取消"]
        transitions = [
            ("待支付", "已支付", "支付成功"), ("待支付", "已取消", "超时/取消"),
            ("已支付", "待发货", "确认订单"), ("待发货", "已发货", "出库"),
            ("已发货", "已完成", "确认收货"), ("已支付", "已取消", "申请退款"),
        ]
    elif any(word in prompt for word in ("审批", "approval")):
        states = ["草稿", "待审批", "审批中", "已通过", "已驳回", "已撤回"]
        transitions = [
            ("草稿", "待审批", "提交"), ("待审批", "审批中", "分配审批人"),
            ("审批中", "已通过", "同意"), ("审批中", "已驳回", "拒绝"),
            ("待审批", "已撤回", "撤回"),
        ]
    else:
        states = ["待处理", "处理中", "待确认", "已完成", "已取消"]
        transitions = [
            ("待处理", "处理中", "开始"), ("处理中", "待确认", "提交结果"),
            ("待确认", "已完成", "确认"), ("待处理", "已取消", "取消"),
            ("处理中", "已取消", "终止"),
        ]
    spec = blank_spec(_title_from_prompt(prompt, "业务状态机"), "state")
    spec["theme"] = theme
    spec["subtitle"] = "状态与受控转换（离线模板）"
    node_list = [{"id": "start", "label": "起点", "type": "start"}]
    for index, state in enumerate(states):
        node_list.append({"id": f"s{index + 1}", "label": state, "type": "state"})
    node_list.append({"id": "end", "label": "终点", "type": "end"})
    state_id = {state: f"s{index + 1}" for index, state in enumerate(states)}
    edges = [{"from": "start", "to": state_id[states[0]], "type": "flow", "label": "创建"}]
    for source, target, label in transitions:
        edges.append({"from": state_id[source], "to": state_id[target], "type": "flow", "label": label})
    for state in ("已完成", "已取消", "已通过", "已驳回"):
        if state in state_id:
            edges.append({"from": state_id[state], "to": "end", "type": "flow", "label": "结束"})
    spec["nodes"] = node_list
    spec["edges"] = edges
    return spec


def _activity_spec(prompt: str, lower: str, theme: str) -> dict[str, Any]:
    if any(word in prompt for word in ("审批", "审核")):
        nodes = [
            ("start", "开始", "start"), ("submit", "提交申请", "process"),
            ("check", "材料完整？", "decision"), ("fix", "补充材料", "process"),
            ("review", "业务审批", "process"), ("decide", "审批通过？", "decision"),
            ("reject", "通知驳回", "process"), ("archive", "归档", "process"), ("end", "结束", "end"),
        ]
        edges = [
            ("start", "submit", "提交"), ("submit", "check", ""),
            ("check", "fix", "否"), ("fix", "submit", "重新提交"),
            ("check", "review", "是"), ("review", "decide", ""),
            ("decide", "archive", "是"), ("decide", "reject", "否"),
            ("archive", "end", ""), ("reject", "end", ""),
        ]
    else:
        nodes = [
            ("start", "开始", "start"), ("input", "接收业务请求", "process"),
            ("validate", "校验通过？", "decision"), ("error", "返回错误提示", "process"),
            ("handle", "执行核心业务", "process"), ("persist", "持久化结果", "process"),
            ("notify", "返回/通知结果", "process"), ("end", "结束", "end"),
        ]
        edges = [
            ("start", "input", ""), ("input", "validate", ""),
            ("validate", "error", "否"), ("error", "end", ""),
            ("validate", "handle", "是"), ("handle", "persist", ""),
            ("persist", "notify", ""), ("notify", "end", ""),
        ]
    spec = blank_spec(_title_from_prompt(prompt, "业务活动流程"), "activity")
    spec["theme"] = theme
    spec["subtitle"] = "活动、判断与正常/异常路径（离线模板）"
    spec["nodes"] = [{"id": a, "label": b, "type": c} for a, b, c in nodes]
    spec["edges"] = [{"from": a, "to": b, "type": "flow", "label": label} for a, b, label in edges]
    return spec


def _component_spec(prompt: str, theme: str, kind: str) -> dict[str, Any]:
    spec = blank_spec(_title_from_prompt(prompt, "系统组件图" if kind == "component" else "系统部署图"), kind)
    spec["theme"] = theme
    spec["direction"] = "LR"
    spec["subtitle"] = "分层结构、依赖方向与基础设施（离线模板）"
    if kind == "component":
        nodes = [
            ("web", "Web 前端", "component", "SPA"), ("gateway", "API 网关", "component", "Edge"),
            ("auth", "认证服务", "service", "Domain Service"), ("biz", "业务服务", "service", "Domain Service"),
            ("db", "业务数据库", "database", "PostgreSQL"), ("cache", "缓存", "database", "Redis"),
            ("mq", "消息队列", "component", "Async"),
        ]
        edges = [
            ("web", "gateway", "flow", "HTTPS"), ("gateway", "auth", "flow", "认证"),
            ("gateway", "biz", "flow", "业务请求"), ("auth", "cache", "flow", "会话"),
            ("auth", "db", "flow", "用户数据"), ("biz", "db", "flow", "读写"),
            ("biz", "mq", "flow", "事件"),
        ]
        groups = [{"id": "core", "label": "应用服务层", "nodes": ["auth", "biz"]}]
    else:
        nodes = [
            ("browser", "用户浏览器", "node", "Client"), ("lb", "负载均衡", "node", "Nginx / LB"),
            ("app1", "应用节点 A", "node", "Docker"), ("app2", "应用节点 B", "node", "Docker"),
            ("db", "数据库主从", "database", "PostgreSQL"), ("cache", "缓存集群", "database", "Redis"),
            ("obs", "日志与监控", "service", "Observability"),
        ]
        edges = [
            ("browser", "lb", "flow", "HTTPS"), ("lb", "app1", "flow", ""),
            ("lb", "app2", "flow", ""), ("app1", "db", "flow", "SQL"),
            ("app2", "db", "flow", "SQL"), ("app1", "cache", "flow", ""),
            ("app2", "cache", "flow", ""), ("app1", "obs", "async", "日志/指标"),
            ("app2", "obs", "async", "日志/指标"),
        ]
        groups = [{"id": "server", "label": "应用服务器集群", "nodes": ["app1", "app2"]}]
    spec["nodes"] = [
        {"id": a, "label": b, "type": c, "stereotype": d}
        for a, b, c, d in nodes
    ]
    spec["edges"] = [{"from": a, "to": b, "type": c, "label": d} for a, b, c, d in edges]
    spec["groups"] = groups
    return spec


def _dfd_spec(prompt: str, theme: str) -> dict[str, Any]:
    spec = blank_spec(_title_from_prompt(prompt, "数据流图"), "dfd")
    spec["theme"] = theme
    spec["subtitle"] = "外部实体、处理过程与数据存储（0 层）"
    nodes = [
        ("user", "用户", "external"), ("process", "业务处理", "process"),
        ("validator", "规则校验", "process"), ("store", "业务数据库", "datastore"),
        ("report", "运营报表", "external"),
    ]
    spec["nodes"] = [{"id": a, "label": b, "type": c} for a, b, c in nodes]
    spec["edges"] = [
        {"from": "user", "to": "process", "type": "data", "label": "业务请求"},
        {"from": "process", "to": "validator", "type": "data", "label": "待校验数据"},
        {"from": "validator", "to": "process", "type": "data", "label": "校验结果"},
        {"from": "process", "to": "store", "type": "data", "label": "业务记录"},
        {"from": "store", "to": "process", "type": "data", "label": "历史数据"},
        {"from": "process", "to": "report", "type": "data", "label": "统计指标"},
    ]
    spec["groups"] = [{"id": "system", "label": "系统处理边界", "nodes": ["process", "validator", "store"]}]
    return spec


def _flow_spec(prompt: str, theme: str) -> dict[str, Any]:
    spec = blank_spec(_title_from_prompt(prompt, "问题解决流程"), "flow")
    spec["theme"] = theme
    spec["subtitle"] = "从题目澄清到交付验证的结构化流程"
    nodes = [
        ("start", "开始", "start"), ("clarify", "澄清目标与约束", "process"),
        ("model", "建立模型/拆解任务", "process"), ("check", "方案可行？", "decision"),
        ("build", "执行与产出", "process"), ("review", "校验与修正", "process"),
        ("end", "完成交付", "end"),
    ]
    edges = [
        ("start", "clarify", ""), ("clarify", "model", ""), ("model", "check", ""),
        ("check", "model", "否 / 补充信息"), ("check", "build", "是"),
        ("build", "review", ""), ("review", "build", "需修改"), ("review", "end", "通过"),
    ]
    spec["nodes"] = [{"id": a, "label": b, "type": c} for a, b, c in nodes]
    spec["edges"] = [{"from": a, "to": b, "type": "flow", "label": label} for a, b, label in edges]
    spec["notes"] = ["离线模式无法可靠理解任何自定义业务结构；配置模型后可生成针对题目的图。"]
    return spec


def _title_from_prompt(prompt: str, fallback: str) -> str:
    one_line = " ".join(prompt.strip().split())
    if not one_line:
        return fallback
    first_sentence = one_line.split("。", 1)[0].split("！", 1)[0].split("？", 1)[0].strip()
    title = first_sentence or one_line
    for prefix in ("请帮我", "请为", "关于", "请", "为"):
        if title.startswith(prefix):
            title = title[len(prefix) :].lstrip("：: ")
            break
    return title[:30] + ("…" if len(title) > 30 else "")
