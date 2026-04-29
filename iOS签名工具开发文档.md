# iOS签名工具开发文档

## 项目概述

本项目旨在开发一款Windows电脑平台上的iOS应用签名工具，具备可视化界面，支持iOS应用的重签名、动态库注入以及时间锁控制功能。该工具将帮助开发者和测试人员方便地对iOS应用进行签名和功能限制管理。

## 功能需求

### 1. 核心签名功能
- 支持IPA文件的签名与重签名
- 支持修改应用的Bundle ID、版本号、应用名称等信息
- 支持自定义entitlements权限配置
- 支持批量签名处理

### 2. 证书管理功能
- 导入、导出和管理开发者证书(.p12)
- 导入、导出和管理描述文件(.mobileprovision)
- 显示证书详细信息(有效期、权限等)
- 支持多证书配置文件的保存与切换

### 3. 动态库注入功能
- 支持向IPA文件注入自定义动态库(.dylib)
- 支持注入时间锁控制动态库
- 支持修改动态库配置参数
- 可视化展示注入状态和结果

### 4. 时间锁控制功能
- 设置应用有效使用时间
- 设置应用试用期限
- 设置应用使用次数限制
- 远程控制时间锁开关(与现有网页后台对接)

### 5. 其他功能
- 操作日志记录与导出
- 签名历史记录查询
- 软件自动更新
- 用户权限管理

## 技术架构

### 1. 开发框架选择

Python  


### 2. 系统架构设计

采用**前后端分离**的架构设计：

- **工具链**：集成第三方签名和注入工具

### 3. 核心模块设计

#### 3.1 签名引擎模块
- 集成开源签名工具(如zsign)
- 封装签名API接口
- 实现签名流程控制
- 处理签名结果验证


#### 3.2 证书管理模块
- 证书导入导出
- 证书信息解析
- 证书有效性验证
- 证书存储安全管理

#### 3.3 动态库注入模块
- 实现Mach-O文件解析
- 动态库注入点定位
- 注入代码实现
- 注入结果验证

```javascript
// 动态库注入模块示例代码
class DylibInjector {
  constructor(options) {
    this.toolPath = options.toolPath;
  }

  async inject(ipaPath, dylibPath, options) {
    // 实现动态库注入逻辑
  }
}
```

#### 3.4 时间锁控制模块
- 时间锁参数配置
- 时间锁动态库生成
- 远程控制接口对接
- 时间锁状态验证

#### 3.5 UI界面模块
- 主界面布局
- 组件交互逻辑
- 主题样式管理
- 多语言支持

## 界面设计

### 1. 主界面布局

主界面采用现代化设计风格，分为以下几个区域：

- **左侧导航栏**：功能模块切换
- **主工作区**：当前功能的操作界面
- **右侧信息栏**：显示详细信息和帮助
- **底部状态栏**：显示操作状态和进度

### 2. 功能页面设计

#### 2.1 签名页面
- 拖放区域(上传IPA文件)
- 证书选择下拉框
- 描述文件选择下拉框
- 应用信息编辑区域
- 签名选项配置区域
- 签名按钮和进度条

#### 2.2 证书管理页面
- 证书列表展示
- 证书导入/导出按钮
- 证书详细信息显示
- 证书有效期提醒

#### 2.3 动态库注入页面
- IPA文件选择区域
- 动态库文件选择区域
- 注入配置选项
- 注入按钮和进度条

#### 2.4 时间锁控制页面
- 时间锁参数设置表单
- 预设模板选择
- 远程控制开关
- 时间锁状态显示

#### 2.5 设置页面
- 工具路径配置
- 临时文件目录配置
- 界面主题设置
- 语言设置

### 3. 界面流程设计

用户操作流程设计为简洁直观的步骤式流程：

1. 选择/上传IPA文件
2. 选择证书和描述文件
3. 配置签名选项和应用信息
4. 配置动态库注入选项(可选)
5. 配置时间锁参数(可选)
6. 执行签名操作
7. 查看结果并下载签名后的IPA

## 技术实现方案

### 1. iOS签名实现

iOS应用签名需要实现以下核心功能：

#### 1.1 IPA解包与重打包
```javascript
async function unpackIPA(ipaPath, outputDir) {
  // 使用unzip工具解包IPA
  await exec(`unzip -o "${ipaPath}" -d "${outputDir}"`);
}

async function repackIPA(inputDir, outputPath) {
  // 重新打包为IPA文件
  await exec(`cd "${inputDir}" && zip -r "${outputPath}" *`);
}
```

#### 1.2 Info.plist修改
```javascript
async function modifyInfoPlist(plistPath, modifications) {
  // 读取plist文件
  const plistData = await fs.readFile(plistPath, 'utf8');
  // 解析plist内容
  const plist = plist.parse(plistData);
  
  // 应用修改
  Object.keys(modifications).forEach(key => {
    plist[key] = modifications[key];
  });
  
  // 写回plist文件
  await fs.writeFile(plistPath, plist.build(plist));
}
```

#### 1.3 签名执行
```javascript
async function signApp(appDir, certPath, provisionPath, entitlements) {
  // 提取entitlements
  await exec(`codesign -d --entitlements :- "${appDir}" > "${entitlements}"`);
  
  // 签名应用
  await exec(`codesign -f -s "${certPath}" --entitlements "${entitlements}" "${appDir}"`);
}
```

### 2. 动态库注入实现

动态库注入需要修改Mach-O文件结构，添加load commands：

#### 2.1 使用optool进行注入
```javascript
async function injectDylib(binaryPath, dylibPath) {
  // 使用optool注入动态库
  await exec(`optool install -c load -p "@executable_path/Frameworks/${path.basename(dylibPath)}" -t "${binaryPath}"`);
}
```

#### 2.2 复制动态库到应用包
```javascript
async function copyDylibToApp(dylibPath, appDir) {
  const frameworksDir = path.join(appDir, 'Frameworks');
  
  // 创建Frameworks目录(如果不存在)
  if (!fs.existsSync(frameworksDir)) {
    await fs.mkdir(frameworksDir);
  }
  
  // 复制动态库
  await fs.copyFile(dylibPath, path.join(frameworksDir, path.basename(dylibPath)));
}
```

### 3. 时间锁控制实现

时间锁控制需要与已有的iOS动态库时间锁功能对接：

#### 3.1 时间锁配置生成
```javascript
async function generateTimeLockConfig(options) {
  // 生成时间锁配置文件
  const config = {
    expiryDate: options.expiryDate,
    trialPeriod: options.trialPeriod,
    maxUsageCount: options.maxUsageCount,
    remoteControlEnabled: options.remoteControlEnabled,
    remoteControlUrl: options.remoteControlUrl
  };
  
  return JSON.stringify(config);
}
```

#### 3.2 配置文件注入
```javascript
async function injectTimeLockConfig(appDir, config) {
  // 将配置写入应用包中
  const configPath = path.join(appDir, 'TimeLock.config');
  await fs.writeFile(configPath, config);
}
```

## 开发计划

### 1. 开发阶段

#### 阶段一：基础框架搭建(2周)
- 搭建Electron应用框架
- 实现基本UI界面
- 集成必要的第三方库

#### 阶段二：核心功能开发(4周)
- 实现IPA文件解析与重打包
- 实现证书管理功能
- 实现基本签名功能

#### 阶段三：高级功能开发(3周)
- 实现动态库注入功能
- 实现时间锁控制功能
- 实现与网页后台的对接

#### 阶段四：测试与优化(2周)
- 功能测试与bug修复
- 性能优化
- 用户体验改进

### 2. 测试计划

- **单元测试**：测试各个功能模块的正确性
- **集成测试**：测试模块间的交互
- **系统测试**：测试整个应用的功能完整性
- **用户测试**：收集用户反馈并改进

### 3. 部署计划

- **打包方式**：使用electron-builder打包为Windows安装程序
- **更新机制**：实现自动更新功能
- **分发渠道**：官网下载、内部分发

## 技术依赖

### 1. 前端依赖
- Electron: ^15.0.0
- Vue.js/React: ^3.0.0
- Electron-builder: ^22.11.7
- Element UI/Ant Design: 最新版本

### 2. 后端依赖
- Node.js: ^14.0.0
- fs-extra: ^10.0.0
- plist: ^3.0.4
- simple-plist: ^1.3.0
- extract-zip: ^2.0.1

### 3. 工具依赖
- zsign: 最新版本
- libimobiledevice: 最新版本
- optool: 最新版本

## 安全考虑

### 1. 证书安全
- 证书存储加密
- 证书使用权限控制
- 证书操作日志记录

### 2. 应用安全
- 防止未授权使用
- 防止工具被滥用
- 关键操作需要授权

### 3. 数据安全
- 临时文件安全处理
- 敏感信息加密存储
- 定期清理缓存数据

## 维护与支持

### 1. 更新计划
- 定期功能更新
- 安全漏洞修复
- 适配新版iOS系统

### 2. 用户支持
- 在线文档
- 视频教程
- 技术支持渠道

## 附录

### 附录A：界面原型图

(此处可插入界面设计图)

### 附录B：数据流程图

(此处可插入数据流程图)

### 附录C：常见问题解答

1. **问题**：签名失败常见原因？
   **答案**：证书过期、描述文件不匹配、entitlements权限不足等。

2. **问题**：如何处理动态库兼容性问题？
   **答案**：确保动态库架构与目标应用兼容，测试不同iOS版本的兼容性。

3. **问题**：时间锁失效的可能原因？
   **答案**：系统时间被修改、动态库被绕过、注入失败等。 