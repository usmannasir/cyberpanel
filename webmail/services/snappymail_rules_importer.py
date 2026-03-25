from typing import Optional, Tuple

from .sieve_client import SieveClient


class SnappymailRulesImporter:
    """
    Import RainLoop/SnappyMail sieve filters from ManageSieve into CyberPanel Webmail.

    SnappyMail/RainLoop uses ManageSieve scripts; the filter storage is typically:
      - rainloop.user  (see RainLoop Providers\\Filters\\SieveStorage.php)

    We import as a RAW script so rules keep working even if parsing differs from CyberPanel's
    own structured rule format.
    """

    RAINLOOP_DEFAULT_SCRIPT = 'rainloop.user'

    def __init__(self, siege_script_name: str = None):
        self.script_name = siege_script_name or self.RAINLOOP_DEFAULT_SCRIPT

    def fetch_raw_script(self, sieve: SieveClient) -> Tuple[str, str]:
        """
        Returns:
            (script_name_used, raw_script_body)
        """
        # Try the standard RainLoop script name first.
        scripts = sieve.list_scripts() or []
        script_names = [name for (name, _) in scripts]

        chosen = self.script_name if self.script_name in script_names else None

        if not chosen:
            # Fallback: choose first active script if available.
            for (name, is_active) in scripts:
                if is_active:
                    chosen = name
                    break
        if not chosen and script_names:
            chosen = script_names[0]

        if not chosen:
            return '', ''

        raw = sieve.get_script(chosen) or ''
        return chosen, raw

