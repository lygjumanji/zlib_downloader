# Z-Library Book Downloader

## 1. 项目概述

### 1.1 项目名称
Z-Library Book Downloader (Zlib Downloader)

### 1.2 项目版本
v1.0.0

### 1.3 项目简介
基于 PySide6 开发的桌面应用程序，用于从 Z-Library 下载电子书籍。参考olib,采用单体架构，直接调用 Z-Library eapi 接口，无需后端服务器。

### 1.4 技术栈
| 技术 | 版本 | 用途 |
|---|---|---|
| Python | 3.x | 主要开发语言 |
| PySide6 | >=6.5.0 | Qt6 GUI 框架 |
| requests | >=2.28.0 | HTTP 请求 |
| SQLAlchemy | >=2.0.0 | ORM 数据库访问 |
| loguru | >=0.6.0 | 日志记录 |
| psutil | >=5.9.0 | 获取设备信息 |
| PyInstaller | - | 打包工具 |

---

## 2. 系统架构

### 2.1 架构图
```
main.py → app/views/ → app/tools/ → app/api/ → Z-Library eapi
                                      ↑
                               app/db/account_pool.py (SQLite3)
```

### 2.2 目录结构
```
zlib_downloader/
├── main.py                          # 程序入口
├── requirements.txt                 # 依赖清单
├── accounts.json                    # 账户种子数据
├── accounts.db                      # SQLite3 数据库
├── config/
│   └── config.json                  # 用户配置文件
├── app/
│   ├── api/                         # API 调用层
│   │   ├── host.py                  # 域名解析
│   │   ├── search.py                # 搜索接口
│   │   └── download.py              # 下载接口
│   ├── views/                       # GUI 页面
│   │   ├── main_window.py           # 主窗口
│   │   ├── search_page.py           # 搜索页
│   │   ├── download_page.py         # 下载页
│   │   ├── setting_page.py          # 设置页
│   │   ├── account_page.py          # 账户页
│   │   ├── book_detail_dialog.py    # 书籍详情对话框
│   │   └── template_dialog.py       # 模板选择对话框
│   ├── tools/                       # 工作线程
│   │   ├── searcher.py              # 搜索线程
│   │   └── downloader.py            # 下载线程
│   ├── db/                          # 数据库层
│   │   └── account_pool.py          # 账户池管理
│   ├── common/                      # 公共配置
│   │   └── config.py                # 配置管理
│   └── utils/                       # 工具函数
│       ├── log.py                   # 日志配置
│       └── uuid.py                  # 设备指纹
└── dist/                            # 打包输出
```

---

## 3. 功能模块分析

### 3.1 API 调用模块 (`app/api/`)

#### 3.1.1 域名解析 (`host.py`)
- **功能**: 将短域名解析为真实域名
- **实现**: HTTP HEAD 请求跟随重定向
- **缓存**: 内存缓存已解析域名

#### 3.1.2 搜索接口 (`search.py`)
- **接口**: `POST https://{host}/eapi/book/search`
- **参数**: 书名、语言、格式、排序、分页等
- **认证**: 无需登录
- **返回**: 书籍列表 + 分页信息

#### 3.1.3 下载接口 (`download.py`)
- **获取下载URL**: `GET https://{host}/eapi/book/{id}/{hash}/file`
- **获取用户信息**: `GET https://{host}/eapi/user/profile`
- **认证**: Cookie (remix_userid + remix_userkey)

### 3.2 GUI 页面模块 (`app/views/`)

#### 3.2.1 主窗口 (`main_window.py`)
- QTabWidget 管理 4 个标签页
- 信号连接各页面
- 优雅退出机制

#### 3.2.2 搜索页 (`search_page.py`)
- 搜索框 + 筛选条件
- 结果表格展示
- 右键菜单操作
- 分页导航

#### 3.2.3 下载页 (`download_page.py`)
- 任务列表管理
- 实时进度/速度显示
- 暂停/恢复/删除操作
- 并发控制

#### 3.2.4 设置页 (`setting_page.py`)
- 搜索下载设置
- 文件名模板
- 服务器地址配置
- 关于信息

#### 3.2.5 账户页 (`account_page.py`)
- 账户 CRUD
- 额度刷新
- JSON 导入导出

### 3.3 工作线程模块 (`app/tools/`)

#### 3.3.1 搜索线程 (`searcher.py`)
- 异步执行搜索
- 信号返回结果

#### 3.3.2 下载线程 (`downloader.py`)
- 完整下载流程
- 暂停/恢复/停止支持
- 速度计算
- 错误处理

### 3.4 数据库模块 (`app/db/`)

#### 3.4.1 账户池 (`account_pool.py`)
- SQLAlchemy ORM
- 账户 CRUD
- 额度管理
- 自动迁移

---

## 4. 数据库设计

### 4.1 表结构 (tb_name)

| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| remix_id | INTEGER | PRIMARY KEY | 用户ID |
| remix_key | VARCHAR(50) | - | 用户密钥 |
| num | INTEGER | - | 剩余下载次数 |
| downloads_limit | INTEGER | 默认10 | 每日最大额度 |
| downloads_today | INTEGER | 默认0 | 今日已下载 |

### 4.2 迁移机制
- 启动时检查表结构
- 自动添加缺失列
- 兼容旧版本数据

---

## 5. API 接口规范

### 5.1 请求头伪装
```python
{
    'source': 'android',
    'android-app-version': '1.11.4',
    'user-agent': 'okhttp/3.12.13',
    'content-type': 'application/x-www-form-urlencoded'
}
```

### 5.2 搜索接口
- **URL**: `POST /eapi/book/search`
- **参数**: message, languages[], extensions[], order, limit, page
- **返回**: `{success: 1, books: [...], pagination: {...}}`

### 5.3 下载接口
- **URL**: `GET /eapi/book/{bookid}/{hashid}/file`
- **认证**: Cookie remix_userid + remix_userkey
- **返回**: `{file: {downloadLink: "..."}}`

### 5.4 用户资料接口
- **URL**: `GET /eapi/user/profile`
- **返回**: `{user: {downloads_today: N, downloads_limit: N}}`

---

## 6. 核心功能流程

### 6.1 搜索流程
```
用户输入 → Searcher线程 → search_books() → API调用 → 结果展示
```

### 6.2 下载流程
```
用户选择 → DownloadPage → AccountPool获取账户 → get_download_url()
    → 流式下载 → 进度更新 → 完成/失败
```

### 6.3 账户池机制
1. 随机选取 num > 0 的账户
2. 下载成功后 num - 1
3. num 归零后不再使用
4. 支持手动/API刷新额度

---

## 7. 设计特点

### 7.1 线程安全
- 所有网络 I/O 在 QThread 执行
- QMutex 保护共享状态
- 信号槽机制通信

### 7.2 容错机制
- 连接失败自动打开浏览器
- 不完整文件自动清理
- 重复文件可选跳过

### 7.3 用户体验
- 实时进度/速度显示
- 暂停/恢复支持
- 文件名模板化
- 多语言支持

### 7.4 数据安全
- 本地 SQLite3 存储
- 配置文件 JSON 格式
- 账户信息加密传输

---

## 8. 依赖库清单

```
PySide6>=6.5.0
requests>=2.28.0
loguru>=0.6.0
sqlalchemy>=2.0.0
psutil>=5.9.0
```

---

## 9. 环境配置

### 9.1 安装
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 9.2 运行
```bash
python main.py
```

### 9.3 打包
```bash
pyinstaller -F -w -i zlib.ico --name zlibdown  main.py
```

---

## 10. 开发规范

- 使用 PySide6 (非 PyQt5)
- 标准 PySide6 控件
- SQLAlchemy ORM
- loguru 日志
- UTF-8 编码
- 同步 requests 在 QThread 中执行

---

## 11. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0.0 | 2026-08-03 | 初始版本 |

