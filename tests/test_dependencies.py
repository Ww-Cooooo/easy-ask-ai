import hashlib
import importlib.util
import io
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location("dependencies", Path(__file__).resolve().parents[1] / "scripts/dependencies.py")
dep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dep)


def fixture(extra=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("repo-commit/skills/example/SKILL.md", "---\nname: example\n---\nExample")
        archive.writestr("repo-commit/LICENSE", "MIT fixture")
        archive.writestr("repo-commit/skills/unrelated/SKILL.md", "Do not install")
        if extra:
            for name, value in extra:
                archive.writestr(name, value)
    data = output.getvalue()
    return data, {"archive_sha256": hashlib.sha256(data).hexdigest(), "archive_root": "repo-commit",
                  "skill_path": "skills/example", "license_path": "LICENSE", "required_files": ["SKILL.md"]}


class DependenciesTest(unittest.TestCase):
    def test_selects_complete_target_and_license_only(self):
        data, spec = fixture([("repo-commit/skills/example/references/guide.md", "guide")])
        self.assertEqual(set(dep.selected_files(data, spec)), {"SKILL.md", "LICENSE", "references/guide.md"})

    def test_digest_rejects_tampered_bytes(self):
        data, spec = fixture()
        with self.assertRaisesRegex(ValueError, "digest"):
            dep.selected_files(data + b"changed", spec)

    def test_rejects_path_escape_and_platform_aliases(self):
        for name in ["../escape", "/absolute", "C:/escape", "a/../b", "CON.txt", "file."]:
            with self.subTest(name=name):
                data, spec = fixture([("repo-commit/skills/example/" + name, "bad")])
                with self.assertRaises(ValueError):
                    dep.selected_files(data, spec)
        # Windows zipfile normalizes backslashes while constructing ZIP entries.
        # Check the raw path validator directly instead of a normalized fixture.
        with self.assertRaises(ValueError):
            dep.safe_relative("a\\b")

    def test_rejects_links_and_case_collisions(self):
        link = zipfile.ZipInfo("repo-commit/skills/example/link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        for extra in [[(link, "../elsewhere")], [("repo-commit/skills/example/skill.md", "collision")]]:
            data, spec = fixture(extra)
            with self.assertRaises(ValueError):
                dep.selected_files(data, spec)

    def test_install_preserves_existing_customizations(self):
        data, spec = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "source.zip"
            archive.write_bytes(data)
            target = root / "skills" / "example"
            target.mkdir(parents=True)
            original = target / "SKILL.md"
            original.write_text("customized", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                dep.install("example", spec, archive, target.parent)
            self.assertEqual(original.read_text(encoding="utf-8"), "customized")

    def test_fresh_install_supports_unicode_spaces_and_is_idempotent_by_refusal(self):
        data, spec = fixture()
        with tempfile.TemporaryDirectory(prefix="技能 空格 ") as temporary:
            root = Path(temporary)
            archive = root / "source.zip"
            archive.write_bytes(data)
            result = dep.install("example", spec, archive, root / "skills")
            self.assertEqual(result["state"], "installed_files")
            self.assertEqual(result["host_loaded"], "not_checked")
            self.assertEqual((root / "skills/example/LICENSE").read_bytes(), b"MIT fixture")
            with self.assertRaises(FileExistsError):
                dep.install("example", spec, archive, root / "skills")

    def test_read_only_check_reports_incomplete_and_missing_without_creating_directories(self):
        _, spec = fixture()
        spec["required_files"].append("references/guide.md")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "example"
            candidate.mkdir()
            (candidate / "SKILL.md").write_text("custom", encoding="utf-8")
            result = dep.check([root, root / "absent"], {"example": spec, "other": spec})
            self.assertEqual([r["state"] for r in result], ["incomplete", "missing"])
            self.assertFalse((root / "absent").exists())

    def test_partial_write_preserves_evidence_without_installing_entrypoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "example"
            actual_open = Path.open

            def failing_open(path, *args, **kwargs):
                if path.name == "broken.md":
                    raise OSError("simulated disk error")
                return actual_open(path, *args, **kwargs)

            with patch.object(Path, "open", failing_open):
                with self.assertRaisesRegex(RuntimeError, "Incomplete copy preserved"):
                    dep.write_new_directory(target, {"a.md": b"evidence", "broken.md": b"bad", "SKILL.md": b"entry"})
            self.assertEqual((target / "a.md").read_bytes(), b"evidence")
            self.assertFalse((target / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
