import codecs
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "edit_text.py"
MODULE = importlib.util.spec_from_file_location("edit_text", SCRIPT)
editor = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(editor)


class ExactEditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "文案.md"
        self.spec = {"old": "## 导出", "new": "## 导出记录", "expected_matches": 1}

    def test_preserves_line_endings_and_final_bytes(self):
        for ending in (b"", b"\n", b"\r\n", b"\n\n", b"\r\n\r\n"):
            with self.subTest(ending=ending):
                before = "前言\r\n\n## 导出\n正文\r\n尾部".encode() + ending
                self.target.write_bytes(before)
                result = editor.replace_file(self.target, self.spec)
                self.assertTrue(result["applied"])
                self.assertEqual(self.target.read_bytes(), before.replace("## 导出".encode(), "## 导出记录".encode()))

    def test_preserves_bom_and_utf16_byte_order(self):
        for bom, encoding in ((codecs.BOM_UTF8, "utf-8"), (codecs.BOM_UTF16_LE, "utf-16-le"), (codecs.BOM_UTF16_BE, "utf-16-be")):
            with self.subTest(encoding=encoding):
                before = bom + "开始\r\n## 导出\n末尾".encode(encoding)
                self.target.write_bytes(before)
                editor.replace_file(self.target, self.spec)
                self.assertEqual(self.target.read_bytes(), bom + "开始\r\n## 导出记录\n末尾".encode(encoding))

    def test_cli_treats_shell_characters_as_data(self):
        self.target.write_bytes(b"prefix\r\n## title\r\nsuffix")
        spec_path = self.root / "spec.json"
        replacement = '`literal` $() \\path "quoted"'
        spec_path.write_text(json.dumps({"old": "## title", "new": replacement, "expected_matches": 1}), encoding="utf-8-sig")
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.target), "--spec", str(spec_path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["applied"])
        self.assertEqual(self.target.read_bytes(), b"prefix\r\n" + replacement.encode() + b"\r\nsuffix")

    def test_mismatch_or_duplicate_does_not_write(self):
        for text in ("没有该标题\n", "## 导出\n## 导出\n"):
            with self.subTest(text=text):
                original = text.encode()
                self.target.write_bytes(original)
                with self.assertRaises(ValueError):
                    editor.replace_file(self.target, self.spec)
                self.assertEqual(self.target.read_bytes(), original)

    def test_stale_hash_does_not_write(self):
        original = "## 导出\n".encode()
        self.target.write_bytes(original)
        with self.assertRaises(ValueError):
            editor.replace_file(self.target, {**self.spec, "expected_sha256": "0" * 64})
        self.assertEqual(self.target.read_bytes(), original)

    def test_invalid_encoding_does_not_write(self):
        for original in (b"\xffinvalid", codecs.BOM_UTF32_LE + "## 导出".encode("utf-32-le"), b"a\x00b\x00"):
            with self.subTest(data=original):
                self.target.write_bytes(original)
                with self.assertRaises((ValueError, UnicodeError)):
                    editor.replace_file(self.target, self.spec)
                self.assertEqual(self.target.read_bytes(), original)

    def test_noop_does_not_replace_file(self):
        self.target.write_bytes("## 导出\r\n".encode())
        with patch.object(editor.os, "replace", side_effect=AssertionError("no-op must not write")):
            self.assertFalse(editor.replace_file(self.target, {**self.spec, "new": "## 导出"})["applied"])

    def test_concurrent_change_is_preserved(self):
        self.target.write_bytes("## 导出\n".encode())
        original_read = Path.read_bytes
        reads = 0

        def changing_read(path):
            nonlocal reads
            if path == self.target:
                reads += 1
                if reads == 2:
                    path.write_bytes(b"Changed by another writer\n")
            return original_read(path)

        with patch.object(Path, "read_bytes", changing_read):
            with self.assertRaisesRegex(ValueError, "changed while"):
                editor.replace_file(self.target, self.spec)
        self.assertEqual(self.target.read_bytes(), b"Changed by another writer\n")
        self.assertFalse(list(self.root.glob(".get-clear-*")))

    def test_invalid_spec_does_not_write(self):
        original = "## 导出".encode()
        for spec in ({**self.spec, "old": ""}, {**self.spec, "expected_matches": True}, {**self.spec, "extra": 1}):
            self.target.write_bytes(original)
            with self.assertRaises(ValueError):
                editor.replace_file(self.target, spec)
            self.assertEqual(self.target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
