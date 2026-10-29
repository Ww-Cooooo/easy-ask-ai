from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/emit_routing.py'
SOURCE = Path(__file__).resolve().parents[1] / 'assets/agents-snippet.md'


class ReminderContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='eaa routing 中文 ')
        self.root = Path(self.temp.name) / 'get-clear'
        (self.root / 'assets').mkdir(parents=True)
        (self.root / 'SKILL.md').write_text('---\nname: get-clear\n---\n', encoding='utf-8')
        (self.root / 'assets/agents-snippet.md').write_bytes(SOURCE.read_bytes())

    def tearDown(self):
        owned = Path(self.temp.name).resolve()
        self.assertEqual(owned.parent, Path(tempfile.gettempdir()).resolve())
        self.assertTrue(self.root.resolve().is_relative_to(owned))
        self.temp.cleanup()

    def invoke(self, fmt, envelope=None):
        return subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), '--format', fmt,
            '--skill-dir', str(self.root)], input='' if envelope is None else json.dumps(envelope),
            text=True, encoding='utf-8', capture_output=True, check=False)

    def test_real_protocol_and_private_prompt_is_not_emitted(self):
        result = self.invoke('claude-submit', {'hook_event_name': 'UserPromptSubmit',
            'prompt': 'PRIVATE_SENTINEL_DO_NOT_ECHO', 'transcript_path': 'PRIVATE_OTHER_LOCATION'})
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)['hookSpecificOutput']
        self.assertEqual(payload['hookEventName'], 'UserPromptSubmit')
        self.assertIn((self.root / 'SKILL.md').as_posix(), payload['additionalContext'])
        self.assertIn('访谈回合的产物是用户现在能回答的一问', payload['additionalContext'])
        self.assertNotIn('PRIVATE_', result.stdout + result.stderr)

    def test_text_and_hook_carry_the_same_live_packaged_rule(self):
        text = self.invoke('text')
        hook = self.invoke('claude-submit', {'hook_event_name': 'UserPromptSubmit'})
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertEqual(text.stdout.rstrip('\n'), json.loads(hook.stdout)['hookSpecificOutput']['additionalContext'])
        self.assertNotIn('<!-- easy-ask-ai:', text.stdout)

    def test_wrong_event_has_no_context_and_does_not_echo_payload(self):
        result = self.invoke('claude-submit', {'hook_event_name': 'PreToolUse', 'prompt': 'PRIVATE_SECRET'})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertNotIn('PRIVATE_SECRET', result.stderr)

    def test_ambiguous_owned_template_is_rejected(self):
        template = self.root / 'assets/agents-snippet.md'
        template.write_text(template.read_text(encoding='utf-8') + '\n<!-- easy-ask-ai:get-clear:start -->', encoding='utf-8')
        result = self.invoke('text')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
