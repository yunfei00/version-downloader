# version-downloader

基于 **PySide6** 的“版本下载工具”，用于从 HTTP 目录递归扫描文件并完整下载到本地，自动保留服务器目录结构。

支持目录索引类型：
- nginx autoindex
- Apache directory listing
- `python -m http.server`

## 功能特性

- 图形界面输入根目录 URL 与本地保存目录
- 递归扫描 HTTP 目录并展示文件列表
- 支持“一键下载”：未扫描时点击“开始下载”会自动扫描并自动下载
- 自动忽略 `../`、`?C=N`、`?C=M`、`?C=S`、`?C=D` 等排序链接
- 正确处理中文文件名、空格与 URL 编码
- 列表字段：序号、相对路径、大小、状态、进度
- 按顺序下载文件，保持目录结构
- 使用 `.part` 临时文件，下载完成自动重命名
- 若本地文件已存在且大小一致，自动跳过
- 支持取消扫描、取消下载
- 统计面板实时显示：文件总数、总大小、已下载大小、当前速度、已用时间、预计剩余时间、当前阶段
- 扫描/下载日志实时输出
- 扫描与下载均在 `QThread Worker` 中执行，避免 UI 卡死

## 本地运行

### 1) 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 2) 启动程序

```bash
python main.py
```

## 简单自测（本地 HTTP 目录）

1. 准备一个测试目录，例如：
   - `test-data/a.txt`
   - `test-data/sub/b.txt`
2. 启动本地 HTTP 服务：

```bash
cd test-data
python -m http.server 8000
```

3. 启动本工具后输入：
   - 根目录 URL：`http://127.0.0.1:8000/`
   - 保存目录：任意本地目录
4. 可直接点击“开始下载”（无需先扫描）：程序会自动执行扫描->统计->下载。
5. 观察统计区域：总大小（含未知文件提示）、已下载大小、速度、预计剩余时间实时变化。
6. 下载完成后确认目录结构和文件内容已下载到本地。

## GitHub Actions 自动打包与发布说明

仓库包含工作流：`.github/workflows/build-windows.yml`。

工作流触发条件：

- 推送符合 `v*` 的 tag（例如：`v0.1.0`）
- 手动触发 `workflow_dispatch`

工作流会在 `windows-latest` 上执行以下步骤：

1. 使用 Python 3.11
2. 安装 `requirements.txt` 依赖
3. 运行 PyInstaller 打包：
   - 输出文件名：`VersionDownloader.exe`
   - 产物路径：`dist/VersionDownloader.exe`
4. 自动创建 GitHub Release：
   - Release 名称：`Version Downloader <tag>`
   - Release body：`Auto build release`
5. 自动上传 Release Asset：
   - 文件名：`VersionDownloader.exe`

## 如何创建 tag 发布版本

```bash
git tag v0.1.0
git push origin v0.1.0
```

执行后会自动触发工作流，并在 GitHub **Releases** 页面创建对应版本并上传 `VersionDownloader.exe`。


如果出现 `Resource not accessible by integration`，需要在 workflow 顶部增加：

```yaml
permissions:
  contents: write
```

## 如何下载 exe

1. 打开 GitHub 仓库页面的 **Releases**。
2. 进入对应 tag 的 Release（例如 `v0.1.0`）。
3. 在 **Assets** 区域下载 `VersionDownloader.exe`。
