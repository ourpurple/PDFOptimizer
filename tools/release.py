"""
自动发布脚本

从 core/version.py 读取版本号，自动创建 git 标签并推送到远程，
触发 GitHub Actions 构建和发布流程。

用法：
    python tools/release.py          # 正常发布
    python tools/release.py --dry-run # 预览模式，不执行实际操作
    python tools/release.py --force   # 跳过未提交更改检查
"""

import subprocess
import sys
import importlib.util
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT_DIR / "core" / "version.py"


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """执行 git 命令并返回结果"""
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        print(f"错误：git {' '.join(args)} 失败")
        print(f"  {result.stderr.strip()}")
        sys.exit(1)
    return result


def get_version() -> str:
    """从 core/version.py 读取版本号"""
    spec = importlib.util.spec_from_file_location("version", VERSION_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__


def get_existing_tags() -> set[str]:
    """获取远程已有的标签列表"""
    result = run_git("tag", "--list")
    return set(result.stdout.strip().splitlines())


def has_uncommitted_changes() -> bool:
    """检查是否有未提交的更改"""
    result = run_git("status", "--porcelain")
    return bool(result.stdout.strip())


def get_remote_url() -> str:
    """获取远程仓库地址"""
    result = run_git("remote", "get-url", "origin")
    return result.stdout.strip()


def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    # 读取版本号
    version = get_version()
    tag = f"v{version}"
    print(f"当前版本：{version}")
    print(f"目标标签：{tag}")
    print(f"远程仓库：{get_remote_url()}")
    print()

    # 检查未提交更改
    if has_uncommitted_changes():
        if force:
            print("警告：存在未提交的更改（已通过 --force 跳过检查）")
        else:
            print("错误：存在未提交的更改，请先提交或暂存")
            print("  使用 --force 跳过此检查")
            run_git("status", "--short")
            sys.exit(1)

    # 检查标签是否已存在
    existing_tags = get_existing_tags()
    if tag in existing_tags:
        print(f"错误：标签 {tag} 已存在")
        print("  如需重新发布，请先删除旧标签：")
        print(f"    git tag -d {tag}")
        print(f"    git push origin :refs/tags/{tag}")
        sys.exit(1)

    # 检查当前分支是否已推送到远程
    result = run_git("status", "--branch", "--porcelain")
    if "ahead" in result.stdout:
        print("警告：本地有未推送的提交")
        if dry_run:
            print("  [预览] 将执行 git push")
        else:
            print("  正在推送本地提交...")
            run_git("push")
            print("  推送完成")
        print()

    # 创建并推送标签
    if dry_run:
        print(f"[预览] 将创建标签：{tag}")
        print(f"[预览] 将推送标签：{tag}")
        print(f"[预览] GitHub Actions 将自动构建并创建 Release")
    else:
        print(f"正在创建标签 {tag}...")
        run_git("tag", tag)

        print(f"正在推送标签 {tag}...")
        run_git("push", "origin", tag)

        print()
        print(f"发布完成！标签 {tag} 已推送到远程")
        print(f"GitHub Actions 将自动构建并创建 Release")
        print(f"查看进度：https://github.com/ourpurple/PDFOptimizer/actions")


if __name__ == "__main__":
    main()
