# 项目 README

简体中文说明，覆盖快速上手与开发常用命令。

## 项目简介

blockchain-ai-quantificat 是一个基于 Python 的小型项目，结合区块链与 AI/数据处理相关功能（项目具体实现请查看代码文件）。用于演示使用
blockchain-analyse 开发量化分析或相关服务的原型。

## AI分析代码仓库 + 测试接口文档（blockchain-analyse）

- blockchain-analyse Github仓库：https://github.com/dunea/blockchain-analyse
- AI分析测试接口文档：https://blockchain-analyse.nuoyea.com/docs

## 主要特性

- [x] 使用 AI 分析信号、止损
- [x] 永续合约多币种量化
- [x] 自定义保证金、杠杆、逐仓/全仓 ...
- [x] 快速止损 + 阶梯止盈
- [x] 可在容器或本地环境运行

更多功能敬请期待...

## 环境要求

- Python 3.13.5
- virtualenv（项目使用 virtualenv 管理环境）
- 已安装的包示例：pip, requests

## 快速开始（本地）

1. 克隆仓库
2. 创建并激活 virtualenv：

```shell script
python3.13 -m virtualenv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)
```

3. 安装依赖：

```shell script
pip install -r requirements.txt
```

4. 配置环境变量：
    - 复制示例文件并按需修改：

```shell script
cp .env.example .env
```

- 在 `.env` 中填写所需的密钥、端点等配置（参见 .env.example）

5. 运行项目：

```shell script
python main.py
```

## 使用 Docker（推荐，开箱即用）

1. 构建镜像：

```shell script
docker build -t blockchain-ai-quantificat .
```

2. 运行容器：

```shell script
docker run --env-file .env -it --rm blockchain-ai-quantificat
```

## 配置与日志

- 全局配置入口：settings.py
- 日志实现示例：logger.py
- 环境变量通过 `.env`

## 开发

- 使用 virtualenv 隔离开发环境
- 代码风格与测试请根据团队惯例添加
- 修改完成后请在本地运行并验证功能

## 贡献

欢迎提交 issue 或 pull request。请在变更中包含清晰的描述与复现步骤。

## 许可

请在仓库中查看 LICENSE 文件（如无则联系项目维护者确认许可条款）。

如果你想让我把这个 README 写入项目中的 README.md 文件，请告诉我，我可以生成对应的文件修改片段。