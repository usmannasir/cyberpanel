import ast
import pathlib
import unittest


SOURCE = pathlib.Path(__file__).parents[1] / "websiteFunctions" / "website.py"
FORBIDDEN_PAGE_SIDE_EFFECTS = {
    "systemctl enable --now fastapi_ssh_server",
    "systemctl start fastapi_ssh_server",
    "systemctl restart fastapi_ssh_server",
    "fastapi_ssh_server.service",
    "WebTerminalPort",
    "0.0.0.0/0",
}


class WebTerminalPageSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        cls.methods = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def _assert_no_terminal_side_effects(self, method_name):
        source = ast.get_source_segment(
            SOURCE.read_text(encoding="utf-8"), self.methods[method_name]
        )
        for command in FORBIDDEN_PAGE_SIDE_EFFECTS:
            self.assertNotIn(command, source)

    def test_website_management_page_does_not_manage_root_terminal(self):
        self._assert_no_terminal_side_effects("loadDomainHome")

    def test_ssh_access_page_does_not_manage_root_terminal(self):
        self._assert_no_terminal_side_effects("sshAccess")


if __name__ == "__main__":
    unittest.main()
