"""CLI: python -m plugins.dashboard <run_dir> [-o out.html]"""
import argparse

from .generate import generate_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentFit Dashboard 生成器")
    parser.add_argument("run_dir", help="RunStore 目录（训练产物）")
    parser.add_argument("-o", "--output", default=None, help="输出 HTML 路径（默认 <run_dir>/dashboard.html）")
    args = parser.parse_args()
    out = generate_dashboard(args.run_dir, args.output)
    print(f"dashboard: {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
