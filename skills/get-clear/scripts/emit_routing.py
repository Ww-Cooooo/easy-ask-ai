"""Render the packaged, owned Get Clear routing block for a verified host seam.

Does not inspect or retain the prompt; validates only the host event envelope.
No transcript/configuration reads, file writes or network requests.
This is a reminder renderer, not an authorization classifier or write guard.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


START = '<!-- easy-ask-ai:get-clear:start -->'
END = '<!-- easy-ask-ai:get-clear:end -->'
LOCATOR = '先按当前技能列表定位并读取 get-clear/SKILL.md'


def routing_text(skill_dir: Path) -> str:
    skill_dir = skill_dir.resolve(strict=True)
    entry = skill_dir / 'SKILL.md'
    if not entry.is_file():
        raise ValueError('Selected Skill entry is absent')
    template = (skill_dir / 'assets' / 'agents-snippet.md').read_text(encoding='utf-8-sig')
    if template.count(START) != 1 or template.count(END) != 1:
        raise ValueError('Routing ownership markers are missing or duplicated')
    start = template.index(START) + len(START)
    end = template.index(END)
    if end < start:
        raise ValueError('Routing ownership markers are reversed')
    block = template[start:end].strip()
    if block.count(LOCATOR) != 1:
        raise ValueError('Packaged routing locator is missing or duplicated')
    block = block.replace(LOCATOR, f'先读取 `{entry.as_posix()}`（选定入口，引用相对此目录解析）', 1)
    return '宿主当前回合的持久路由提醒；它不构成用户对本次制作的新委托。\n\n' + block


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format', choices=('text', 'claude-submit'), required=True)
    parser.add_argument('--skill-dir', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        if args.format == 'claude-submit':
            # Consume only this event envelope. Never echo or persist its prompt.
            envelope = json.load(sys.stdin)
            if not isinstance(envelope, dict) or envelope.get('hook_event_name') != 'UserPromptSubmit':
                raise ValueError('Expected UserPromptSubmit event envelope')
        text = routing_text(args.skill_dir)
        if args.format == 'text':
            print(text)
        else:
            print(json.dumps({'hookSpecificOutput': {
                'hookEventName': 'UserPromptSubmit', 'additionalContext': text
            }}, ensure_ascii=False))
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        # No event values, transcript paths or credential material in diagnostics.
        print(f'Get Clear routing reminder unavailable: {type(exc).__name__}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
