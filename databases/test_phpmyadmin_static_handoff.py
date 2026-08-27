from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class PhpMyAdminStaticHandoffTests(TestCase):
    def test_source_and_collected_assets_submit_token_by_post(self):
        collected_asset = ROOT / 'static' / 'databases' / 'databases.js'
        if not collected_asset.exists():
            collected_asset = (
                ROOT / 'public' / 'static' / 'databases' / 'databases.js'
            )
        assets = (
            ROOT / 'databases' / 'static' / 'databases' / 'databases.js',
            collected_asset,
        )

        for asset in assets:
            with self.subTest(asset=asset):
                source = asset.read_text()
                controller = source[source.index("app.controller('phpMyAdmin'"):]
                next_controller = controller.find(
                    'app.controller(', len("app.controller('phpMyAdmin'")
                )
                if next_controller != -1:
                    controller = controller[:next_controller]
                self.assertIn("form.method = 'post'", controller)
                self.assertIn(
                    "form.action = '/phpmyadmin/phpmyadminsignin.php'",
                    controller,
                )
                self.assertIn("tokenInput.name = 'token'", controller)
                self.assertNotIn('phpmyadminsignin.php?username=', controller)
