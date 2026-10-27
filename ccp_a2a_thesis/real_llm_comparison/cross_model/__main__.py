"""CLI: all operations are offline except the explicit run subcommand."""
import argparse
import json
from pathlib import Path
import sys

from .core import DEFAULT_MATERIALS, load_materials, read_json, schedule
from .runner import execute, prepare
from .review import agreement, analyze, export_review, import_ratings, publish


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('plan', 'freeze', 'simulate'):
        p = sub.add_parser(command)
        p.add_argument('--materials', type=Path, default=DEFAULT_MATERIALS)
        p.add_argument('--config', type=Path, default=DEFAULT_MATERIALS / 'providers.example.json')
        p.add_argument('--repetitions', type=int, default=3)
        p.add_argument('--seed', type=int, default=42)
        if command != 'plan':
            p.add_argument('--run-dir', type=Path, required=True)
        if command == 'freeze':
            p.add_argument('--approve-materials', action='store_true')
    p = sub.add_parser('run')
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--max-calls', type=int, default=40)
    p.add_argument('--batch', type=int, help='Run only this numbered task/repetition block, in order.')
    p.add_argument('--confirm-free-tier', action='store_true')
    p.add_argument('--retry-errors', action='store_true')
    p.add_argument('--abandon-pending', action='store_true')
    p = sub.add_parser('review')
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('score')
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--packet-dir', type=Path, required=True)
    p.add_argument('--ratings', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('agreement')
    p.add_argument('--left', type=Path, required=True)
    p.add_argument('--right', type=Path, required=True)
    p = sub.add_parser('analyze')
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--scores', type=Path)
    p = sub.add_parser('publish')
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--scores', type=Path)
    p.add_argument('--reviewed', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command in ('plan', 'freeze', 'simulate'):
            config = read_json(args.config)
            tasks, _ = load_materials(args.materials)
            jobs = schedule(tasks['tasks'], config, args.repetitions, args.seed)
            if args.command == 'plan':
                result = {'tasks': len(tasks['tasks']), 'routes': len(config['routes']),
                          'conditions': 4, 'runs': len(jobs), 'workflow_calls': len(jobs) * 4,
                          'api_calls_made': 0, 'materials_status': tasks.get('status'),
                          'warning': 'Free-tier availability and model IDs require account verification; no paid fallback.'}
            else:
                result = prepare(args.run_dir, args.materials, config, args.repetitions, args.seed,
                                 simulation=args.command == 'simulate',
                                 approve_materials=getattr(args, 'approve_materials', False))
                if args.command == 'simulate':
                    result['execution'] = execute(args.run_dir, max_calls=len(jobs) * 4)
        elif args.command == 'run':
            result = execute(args.run_dir, max_calls=args.max_calls,
                             confirm_free_tier=args.confirm_free_tier,
                             retry_errors=args.retry_errors, abandon_pending=args.abandon_pending,
                             batch=args.batch,
                             progress=lambda event: print(json.dumps(event), file=sys.stderr, flush=True))
        elif args.command == 'review':
            result = export_review(args.run_dir, args.output)
        elif args.command == 'score':
            result = import_ratings(args.run_dir, args.packet_dir, args.ratings, args.output)
        elif args.command == 'analyze':
            result = analyze(args.run_dir, args.scores)
        elif args.command == 'agreement':
            result = agreement(args.left, args.right)
        else:
            result = publish(args.run_dir, args.destination, args.scores, args.reviewed)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get('reason') == 'provider_error':
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
