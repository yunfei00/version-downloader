# version-downloader

基于 **PySide6** 的“版本下载工具”，用于从 HTTP 目录递归扫描文件并完整下载到本地，自动保留服务器目录结构。

支持目录索引类型：
- nginx autoindex
- Apache directory listing
- `python -m http.server`

## 功能特性

- 图形界面输入根目录 URL 与本地保存目录
- 递归扫描 HTTP 目录并展示文件列表
- 自动忽略 `../`、`?C=N`、`?C=M`、`?C=S`、`?C=D` 等排序链接
- 正确处理中文文件名、空格与 URL 编码
- 列表字段：序号、相对路径、大小、状态、进度
- 按顺序下载文件，保持目录结构
- 使用 `.part` 临时文件，下载完成自动重命名
- 若本地文件已存在且大小一致，自动跳过
- 支持取消扫描、取消下载
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
4. 点击“扫描目录”，确认出现递归文件列表。
5. 点击“开始下载”，确认目录结构和文件内容已下载到本地。

## GitHub Actions 自动打包说明

仓库包含工作流：`.github/workflows/build-windows.yml`。

工作流会在 `windows-latest` 上执行以下步骤：

1. 使用 Python 3.11
2. 安装 `requirements.txt` 依赖
3. 运行 PyInstaller 打包：
   - 输出文件名：`VersionDownloader.exe`
4. 上传构建产物：
   - Artifact 名称：`VersionDownloader-windows`
   - 包含文件：`dist/VersionDownloader.exe`

## 如何下载 exe

1. 打开 GitHub 仓库页面的 **Actions**。
2. 进入一次成功的 `Build Windows Executable` 工作流运行记录。
3. 在页面底部 **Artifacts** 区域下载 `VersionDownloader-windows`。
4. 解压后获得 `VersionDownloader.exe`。
