#!/usr/bin/env python3
"""AgentWorld Async — single entry point. World-agnostic.

  python main.py                         # multi-agent concurrent test (60s)
  python main.py --runtime 180 --validate  # 3min + validation
  python main.py --demo                  # single-agent demo
  python main.py --output trace.json     # save trace data
  python main.py --eval-report trace.json # evaluation report
"""
import sys, os, asyncio, argparse

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, "src"))


def parse_args():
    parser = argparse.ArgumentParser(description="AgentWorld Async")
    parser.add_argument("--demo", action="store_true",
                        help="Run single-agent demo")
    parser.add_argument("--runtime", type=int, default=60,
                        help="Test runtime in seconds (default: 60)")
    parser.add_argument("--validate", action="store_true",
                        help="Run validation checks after test")
    parser.add_argument("--output", type=str, default="",
                        help="Save trace JSON to file")
    parser.add_argument("--persist", type=str, default="",
                        help="SQLite database path for persistence")
    parser.add_argument("--validate-config", action="store_true",
                        help="Validate world.yaml + prompts.yaml without running")
    parser.add_argument("--world", type=str, default="",
                        help="Path to world YAML (default: config/world.yaml)")
    parser.add_argument("--eval-report", type=str, default="",
                        help="Run evaluation report from existing trace JSON")
    parser.add_argument("--api-port", type=int, default=0,
                        help="Start Gateway API on given port (0=disabled)")
    parser.add_argument("--dashboard", type=int, default=0,
                        help="Start Live Dashboard on given port (0=disabled)", dest="dashboard_port")
    return parser.parse_args()


async def main():
    args = parse_args()
    if args.eval_report:
        from eval import run_eval
        report = run_eval(args.eval_report)
        print(report.to_table())
        if args.output:
            report.save(args.output)
            print(f"\n  Saved: {args.output}")
        return
    if args.validate_config:
        from cli.commands import cmd_validate_config
        cmd_validate_config(args)
        return
    if args.demo:
        from cli.commands import cmd_demo
        await cmd_demo(args)
    else:
        from cli.commands import cmd_test
        await cmd_test(args)


if __name__ == "__main__":
    asyncio.run(main())
