"""Import-shape tests: what may be imported where, and what must not be.

These exist because the failures they cover are invisible on the platform you
develop on. A module-scope `import termios` is correct on macOS and fatal on
Windows; a broken ctypes signature in the Windows backend is fatal on Windows
and unreachable everywhere else. Neither shows up in the matching tests, and
neither needs a window server to catch -- which makes them exactly the kind of
thing CI should own.
"""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def in_fresh_interpreter(code):
    """Run `code` in a clean interpreter rooted at the repo. Returns stdout.

    A subprocess rather than an in-process check because the question is what a
    module pulls in on a bare import, and this test process has already
    imported a great deal that would mask the answer.
    """
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("interpreter exited {}:\n{}".format(
            r.returncode, r.stderr.strip()))
    return r.stdout.strip()


class DeferredPlatformImports(unittest.TestCase):
    """The trap that made `picker` unimportable on Windows, and took `jump`
    down with it -- `jump` needs only `find_index`, which never wanted a tty.

    Written as a standing assertion rather than a comment because the natural
    way to write terminal code is a module-scope import, and it is correct on
    the platform most of this gets edited on.
    """

    def test_importing_picker_does_not_import_termios(self):
        out = in_fresh_interpreter(
            "import sys; import idejump.picker;"
            " print('termios' in sys.modules)")
        self.assertEqual(out, "False",
                         "idejump.picker imported termios at module scope; "
                         "that makes the module unusable on Windows and takes "
                         "`jump` down with it. Defer it into _PosixTerm.")

    def test_importing_picker_does_not_import_msvcrt(self):
        out = in_fresh_interpreter(
            "import sys; import idejump.picker;"
            " print('msvcrt' in sys.modules)")
        self.assertEqual(out, "False")

    def test_core_modules_import_on_every_platform(self):
        # Nothing here may reach for a platform module at import time.
        out = in_fresh_interpreter(
            "import idejump.picker, idejump.context, idejump.config,"
            " idejump.backends; print('ok')")
        self.assertEqual(out, "ok")


class BackendSelection(unittest.TestCase):
    """get_backend picks by sys.platform and fails loudly on a port that does
    not exist yet, rather than returning something that silently finds nothing.
    """

    def test_returns_a_backend_for_this_platform(self):
        from idejump import config
        from idejump.backends import BackendUnavailable, get_backend
        app = config.load()
        try:
            backend = get_backend(app)
        except BackendUnavailable:
            # Linux is a supported CI platform and an unsupported runtime one.
            self.assertNotIn(sys.platform, ("darwin", "win32"))
            return
        for method in ("pid", "list_windows", "raise_window"):
            self.assertTrue(callable(getattr(backend, method, None)),
                            "backend is missing {}()".format(method))

    def test_unsupported_platform_raises_rather_than_returning_none(self):
        import unittest.mock
        from idejump import config
        from idejump.backends import BackendUnavailable, get_backend
        with unittest.mock.patch("sys.platform", "atari"):
            with self.assertRaises(BackendUnavailable):
                get_backend(config.load())


@unittest.skipUnless(sys.platform == "win32", "Windows-only module")
class WindowsBackend(unittest.TestCase):
    """The only automated check the Windows backend gets.

    It cannot be imported anywhere else -- `ctypes.WinDLL` does not exist off
    Windows -- so without a Windows runner a syntax error or a bad ctypes
    signature in this module reaches users untouched by any test. Enumeration
    is called because it exercises the EnumWindows callback and the filter; the
    result is not asserted, since a CI runner's desktop may legitimately have
    no editor windows on it. Raising is never called.
    """

    def test_module_imports_and_binds(self):
        from idejump.backends import windows
        self.assertTrue(hasattr(windows, "WindowsBackend"))

    def test_enumeration_runs_without_raising(self):
        from idejump import config
        from idejump.backends import windows
        backend = windows.WindowsBackend(config.load())
        self.assertIsInstance(backend.list_windows(), list)
        self.assertIsInstance(backend.pid(), int)


@unittest.skipUnless(sys.platform == "darwin", "macOS-only module")
class MacOSBackend(unittest.TestCase):
    def test_module_imports(self):
        from idejump.backends import macos
        self.assertTrue(hasattr(macos, "MacOSBackend"))


class Entrypoint(unittest.TestCase):
    """`ide_jump.py` is what the manifest actually runs."""

    def test_unknown_command_exits_2_without_a_traceback(self):
        r = subprocess.run([sys.executable, "ide_jump.py", "no-such-command"],
                           cwd=ROOT, capture_output=True, text=True, timeout=60)
        # 2 on a supported platform; 1 where there is no backend to build.
        self.assertIn(r.returncode, (1, 2), r.stderr)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
