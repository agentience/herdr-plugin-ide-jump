"""Table tests for the title-matching logic.

This is the half of the plugin that can be tested without a window server, and
the half most likely to break: every platform port so far has needed a new
matching rule, and each one risks making an existing rule fire where it should
not. The rules are ranked, so "does the right one win" matters as much as "does
this one work".

Pure functions only -- nothing here talks to Herdr, AppleScript or user32, so it
runs identically on all three platforms in CI.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from idejump import picker  # noqa: E402

# Built with os.sep so the same test exercises "/repos/paas/master" on POSIX and
# "\repos\paas\master" on Windows. Both satisfy the absolute-path test that
# path_in_title uses to find the path segment.
PAAS = os.sep + os.path.join("repos", "paas", "master")
GESTAO = os.sep + os.path.join("repos", "gestao", "master")


class FindIndex(unittest.TestCase):
    """find_index returns the window for a project, or -1."""

    def test_exact_title(self):
        items = ["formworks", "herdr-plugin-ide-jump", "claude-home"]
        self.assertEqual(picker.find_index(items, "herdr-plugin-ide-jump"), 1)

    def test_head_before_separator(self):
        # "${rootName}${separator}${activeEditorShort}" plus VS Code's own
        # status suffixes. The head is the project.
        for title in ("formworks — Modified",
                      "formworks – 1 problem in this file",
                      "formworks - index.ts"):
            self.assertEqual(picker.find_index([title], "formworks"), 0, title)

    def test_segment_anywhere_in_title(self):
        # VS Code's Windows default puts the root name in the MIDDLE. Before
        # this rule existed the plugin reported no window with the window open.
        items = ["chrome.ts - myproject - Visual Studio Code"]
        self.assertEqual(picker.find_index(items, "myproject"), 0)

    def test_prefix_is_not_a_match(self):
        # The reason segments are compared whole rather than by substring.
        items = ["articles-archive", "articles-archive — Modified",
                 "x.ts - articles-archive - Visual Studio Code"]
        self.assertEqual(picker.find_index(items, "articles"), -1)

    def test_no_match_is_minus_one(self):
        # -1 rather than 0 is load-bearing: `jump` must not raise an arbitrary
        # window when it matched nothing.
        self.assertEqual(picker.find_index(["formworks"], "nothing-here"), -1)

    def test_empty_project_is_no_match(self):
        self.assertEqual(picker.find_index(["formworks"], ""), -1)

    def test_no_items(self):
        self.assertEqual(picker.find_index([], "formworks"), -1)

    def test_head_match_outranks_segment_match(self):
        # Both windows contain "paas" as a segment; only one leads with it.
        items = ["x.ts - paas - Visual Studio Code", "paas — Modified"]
        self.assertEqual(picker.find_index(items, "paas"), 1)


class RootMatching(unittest.TestCase):
    """A path in the title outranks the name, and is inert without one."""

    def test_path_beats_name_on_a_folder_name_collision(self):
        # The case this rule exists for: worktrees laid out as <repo>/<branch>
        # make "master" the folder name of every project on the machine, and
        # the titles are then identical strings that no name rule can separate.
        items = ["a.ts - " + GESTAO + " - Visual Studio Code",
                 "b.ts - " + PAAS + " - Visual Studio Code"]
        self.assertEqual(picker.find_index(items, "master", PAAS), 1)
        self.assertEqual(picker.find_index(items, "master", GESTAO), 0)

    def test_path_match_respects_component_boundaries(self):
        items = ["a.ts - " + PAAS + "-old - Visual Studio Code"]
        self.assertEqual(picker.find_index(items, "nothing", PAAS), -1)

    def test_root_is_inert_when_the_title_has_no_path(self):
        # Every existing macOS user is on "${rootName}" titles. Passing a root
        # must not change what they match.
        items = ["formworks", "claude-home"]
        self.assertEqual(picker.find_index(items, "claude-home", PAAS),
                         picker.find_index(items, "claude-home"))

    def test_bare_path_segment_matches(self):
        # What the README's recommended ${rootPath} format produces.
        self.assertEqual(picker.find_index([PAAS], "irrelevant", PAAS), 0)

    def test_empty_root_is_ignored(self):
        items = ["formworks"]
        self.assertEqual(picker.find_index(items, "formworks", ""), 0)


class Preselect(unittest.TestCase):
    """preselect_index is find_index clamped to a row the picker can open on."""

    def test_falls_back_to_first_row(self):
        self.assertEqual(picker.preselect_index(["a", "b"], "nothing"), 0)

    def test_agrees_with_find_index_on_a_hit(self):
        items = ["a", "b", "c"]
        self.assertEqual(picker.preselect_index(items, "c"), 2)


class Labels(unittest.TestCase):
    """Row text: readable in a 60%-wide popup, and never two identical rows."""

    def test_plain_title_is_unchanged(self):
        self.assertEqual(picker.labels_for(["formworks"]), ["formworks"])

    def test_path_collapses_to_last_two_components(self):
        title = "a.ts - " + PAAS + " - Visual Studio Code"
        self.assertEqual(picker.short_label(title), "paas/master")

    def test_colliding_labels_are_disambiguated(self):
        # Two windows on one project would otherwise render as identical rows
        # with no way to tell which is which.
        items = ["a.ts - " + PAAS + " - Visual Studio Code",
                 "b.ts - " + PAAS + " - Visual Studio Code"]
        labels = picker.labels_for(items)
        self.assertEqual(len(set(labels)), 2, labels)
        self.assertTrue(all(lab.startswith("paas/master") for lab in labels))

    def test_distinct_labels_are_left_alone(self):
        items = ["a.ts - " + PAAS + " - Visual Studio Code",
                 "b.ts - " + GESTAO + " - Visual Studio Code"]
        self.assertEqual(picker.labels_for(items), ["paas/master", "gestao/master"])


class Filter(unittest.TestCase):
    """The picker's type-to-filter, which runs over labels, not titles."""

    def test_subsequence_and_case_insensitive(self):
        self.assertTrue(picker.matches("pms", "paas/master"))
        self.assertTrue(picker.matches("PAAS", "paas/master"))

    def test_empty_query_matches_everything(self):
        self.assertTrue(picker.matches("", "anything"))

    def test_non_subsequence_does_not_match(self):
        self.assertFalse(picker.matches("zzz", "paas/master"))


if __name__ == "__main__":
    unittest.main()
