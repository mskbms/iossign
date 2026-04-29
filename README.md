# iOS签名工具

一款基于Python的Windows平台iOS应用签名工具，具备可视化界面，支持iOS应用的重签名、动态库注入以及时间锁控制功能。目前开源的是单机版本源码2025-4月份

<img width="831" height="1089" alt="ScreenShot_2026-04-29_150321_652" src="https://github.com/user-attachments/assets/6c72c323-a16b-4ed9-b867-59e62eb9afda" />
<img width="830" height="1088" alt="ScreenShot_2026-04-29_150224_525" src="https://github.com/user-attachments/assets/a2546406-47e5-484b-aee9-41229f1cd809" />
<img width="831" height="1088" alt="ScreenShot_2026-04-29_150201_306" src="https://github.com/user-attachments/assets/cc7318c9-209b-49a3-911b-8508941fbdf6" />

2026网络版本， 核心功能

IPA 重签名（单个 / 批量 / 更新）
支持多场景签名流程，包含证书替换、描述文件嵌入、签名校验与输出打包。

证书管理（本地 + 在线）
支持本地证书导入管理与在线证书签名能力，适配不同使用场景。

动态库扫描与展示
自动解析应用内动态库，集中展示 dylib/framework 依赖，便于排查和管理。

动态库删除
支持从应用中移除指定动态库（含引用处理与文件清理流程）

动态库注入（dylib / framework）
支持向应用注入自定义动态库，兼容 dylib 与 framework 两种方式。

应用信息可视化修改
支持修改 Bundle ID、应用显示名、版本号等关键字段，签名前自动同步到 Info.plist。

自动加锁注入
勾选自动加锁后，按设置注入对应资源（Framework 或 dylib），并自动处理默认到期时间。
支持闪退和弹出到期提示文字2种模式

应用信息修改
支持修改 Bundle ID、应用显示名、版本号等信息，签名前自动同步到 Info.plist。


应用后台联动管理
支持网页版本，内置应用列表与更新签名能力，应用信息同步、签名记录管理、状态维护
还有web网站版本也支持在线签名，和win功能一样，额外支持企业签这种模式版本。
<img width="1500" height="1119" alt="ScreenShot_2026-04-29_152920_426" src="https://github.com/user-attachments/assets/387428b2-c763-48d4-ad6e-9658bc50117f" />
<img width="1500" height="1119" alt="ScreenShot_2026-04-29_152911_101" src="https://github.com/user-attachments/assets/78ec31e9-311f-4812-ad2e-60883bbe23eb" />
<img width="1500" height="1118" alt="ScreenShot_2026-04-29_152711_371" src="https://github.com/user-attachments/assets/3a71f93b-fcea-4b49-a96f-7eba0db13dfb" />
<img width="1503" height="1118" alt="44" src="https://github.com/user-attachments/assets/33526fd0-a4ca-4786-83e4-9210e7792e99" />
<img width="1500" height="1119" alt="3" src="https://github.com/user-attachments/assets/b2342806-d8ae-43da-9e40-028197bc3e6e" />
<img width="1500" height="1118" alt="1" src="https://github.com/user-attachments/assets/35927e75-30e4-426b-8b1b-46a11f592d23" />

 


## 功能特点

- **签名与重签名**：支持IPA文件的签名与重签名，修改Bundle ID、版本号等信息
- **证书管理**：导入、导出和管理开发者证书和描述文件
- **动态库注入**：向IPA文件注入自定义动态库
- **时间锁控制**：设置应用有效使用时间、试用期限、使用次数限制等

## 系统要求

- Windows 10/11
- Python 3.8+

## 安装方法

### 方法一：直接运行源码

1. 克隆或下载本仓库
2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```
3. 运行应用：
   ```
   python run.py
   ```

### 方法二：使用打包版本

1. 下载最新的发布版本
2. 解压后直接运行可执行文件

## 使用说明

### 签名功能

1. 在"签名"标签页中选择IPA文件
2. 选择证书和描述文件
3. 根据需要修改应用信息
4. 点击"开始签名"按钮

### 证书管理

1. 在"证书管理"标签页中导入证书(.p12)和描述文件(.mobileprovision)
2. 查看和管理已导入的证书和描述文件

### 动态库注入

1. 在"动态库注入"标签页中选择IPA文件
2. 添加需要注入的动态库(.dylib)
3. 设置注入选项
4. 点击"开始注入"按钮

### 时间锁控制

1. 在"时间锁控制"标签页中选择IPA文件和时间锁动态库
2. 设置时间锁参数或选择预设模板
3. 生成配置并应用到IPA文件

## 构建应用

要构建独立的可执行文件，请运行：

```
python build.py
```

构建完成后，可执行文件将位于`dist`目录中。

## 目录结构

```
.
├── src/                  # 源代码
│   ├── core/             # 核心功能模块
│   ├── ui/               # 用户界面
│   └── utils/            # 工具函数
├── tools/                # 第三方工具
├── resources/            # 资源文件
├── requirements.txt      # 依赖列表
├── run.py               # 启动脚本
└── build.py             # 打包脚本
```

## 第三方工具

本工具依赖以下第三方工具：

- [zsign](https://github.com/zhlynn/zsign)：iOS签名工具
- [optool](https://github.com/alexzielenski/optool)：动态库注入工具

请确保这些工具已正确放置在`tools`目录中。

## 许可证

本项目采用MIT许可证。详情请参阅LICENSE文件。

## 免责声明

本工具仅供开发和测试使用，请勿用于非法用途。使用本工具产生的任何后果由用户自行承担。 
