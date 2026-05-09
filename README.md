# version-downloader

基于 **PySide6** 的“版本下载工具”，用于从 HTTP 目录递归扫描文件并完整下载到本地，自动保留服务器目录结构。

支持目录索引类型：
- nginx autoindex
- Apache directory listing
- `python -m http.server`

## 功能特性

- 图形界面输入根目录 URL 与本地保存目录
- 递归扫描 HTTP 目录并展示文件列表
- 列表字段：序号、相对路径、大小、状态、进度
- 按顺序下载文件，保持目录结构
- 使用 `.part` 临时文件，下载完成自动重命名
- 已存在文件自动跳过
- 支持取消扫描、取消下载
- 实时日志输出
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

## GitHub Actions 自动打包说明

仓库包含工作流：`.github/workflows/build-windows.yml`。

工作流会在 `windows-latest` 上执行以下步骤：

1. 使用 Python 3.11
2. 安装 `requirements.txt` 依赖
3. 运行 PyInstaller 打包：
   - 输出文件名：`VersionDownloader.exe`
4. 上传构建产物：
   - Artifact 名称：`VersionDownloader-windows`

## 如何下载 exe

1. 打开 GitHub 仓库页面的 **Actions**。
2. 进入一次成功的 `Build Windows Executable` 工作流运行记录。
3. 在页面底部 **Artifacts** 区域下载 `VersionDownloader-windows`。
4. 解压后获得 `VersionDownloader.exe`。
