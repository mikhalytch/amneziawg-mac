"""Load the real Darwin script in a temporary filesystem, exercise configuration
and route lifecycle operations, and check CLI integration without changing host
interfaces, routes, DNS, or installed files.
"""

import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import unittest


class DarwinTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="awg-tests-", dir="/private/tmp")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        script = Path(os.environ["AWG_QUICK_SCRIPT"]).read_text()
        script = script.split("# ~~ function override insertion point ~~")[0]
        script = script.replace("/var/run/amneziawg", str(self.root / "amneziawg"))
        script = script.replace("/var/run/wireguard", str(self.root / "wrong-directory"))
        self.library = self.root / "darwin-functions.bash"
        self.library.write_text(script)
        self.bash = os.environ.get("BASH_BIN", shutil.which("bash"))
        self.config = self.root / "awg0.conf"
        self.config.write_text("[Interface]\nAddress = 10.0.0.2/32\n"
                               "ExcludeIPs = 192.168.0.0/24, 2001:db8::/32\n"
                               "SaveConfig = true\n[Peer]\nAllowedIPs = 0.0.0.0/0\n")
        self.config.chmod(0o600)
        self.log = self.root / "routes.log"
        self.log.touch()

    def run_script(self, body):
        env = dict(os.environ, TEST_CONFIG=str(self.config), ROUTE_LOG=str(self.log),
                   TEST_RUNTIME=str(self.root / "amneziawg"))
        # Only OS-level routing is replaced: configuration and routing decisions
        # still execute the production functions.
        setup = 'source "$1"\nroute() { printf "%s\\n" "$*" >> "$ROUTE_LOG"; }\n'
        return subprocess.run([self.bash, "-c", setup + body, "test", str(self.library)],
                              env=env, text=True, capture_output=True)

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_strip_consumes_exclusions_without_changing_allowed_ips(self):
        """Create a config with exclusions; strip quick-only settings; check
        that exclusions disappear and the peer's full-tunnel AllowedIPs survives.
        """
        result = self.run_script('parse_options "$TEST_CONFIG"; cmd_strip')
        self.assert_ok(result)
        self.assertNotIn("ExcludeIPs", result.stdout)
        self.assertNotIn("Address", result.stdout)
        self.assertIn("AllowedIPs = 0.0.0.0/0", result.stdout)

    def test_routes_cover_both_families_and_cleanup(self):
        """Parse IPv4/IPv6 exclusions, add and delete their bypass routes,
        and check the correct address family, subnet, and physical gateway.
        """
        result = self.run_script('parse_options "$TEST_CONFIG"; '
                                 'GATEWAY4=192.0.2.1; GATEWAY6=2001:db8::1; '
                                 'add_excluded_routes; del_excluded_routes')
        self.assert_ok(result)
        self.assertEqual(self.log.read_text().splitlines(), [
            "-q -n add -inet 192.168.0.0/24 -gateway 192.0.2.1",
            "-q -n add -inet6 2001:db8::/32 -gateway 2001:db8::1",
            "-q -n delete -inet 192.168.0.0/24",
            "-q -n delete -inet6 2001:db8::/32",
        ])

    def test_table_off_does_not_add_or_delete_exclusion_routes(self):
        """Create exclusions with Table=off, request route setup and cleanup,
        and check that the script leaves the routing table untouched.
        """
        result = self.run_script('parse_options "$TEST_CONFIG"; TABLE=off; '
                                 'GATEWAY4=192.0.2.1; GATEWAY6=2001:db8::1; '
                                 'add_excluded_routes; del_excluded_routes')
        self.assert_ok(result)
        self.assertEqual(self.log.read_text(), "")

    def test_save_preserves_exclusions(self):
        """Parse an exclusion config, save actual quick configuration using
        controlled interface/UAPI responses, and check exclusions survive reload.
        """
        result = self.run_script('ifconfig() { echo "inet 10.0.0.2 netmask 0xffffffff"; }; '
                                 'awg() { printf "[Interface]\\n[Peer]\\nAllowedIPs = 0.0.0.0/0\\n"; }; '
                                 'parse_options "$TEST_CONFIG"; REAL_INTERFACE=utun99; save_config; '
                                 'EXCLUDED_IPS=(); parse_options "$TEST_CONFIG"; '
                                 'printf "EXCLUSIONS:%s\\n" "${EXCLUDED_IPS[*]}"')
        self.assert_ok(result)
        self.assertIn("EXCLUSIONS:192.168.0.0/24 2001:db8::/32", result.stdout)

    def test_interface_discovery_and_shutdown_use_amnezia_paths(self):
        """Create a name file and Unix control socket, discover the interface
        through awg, then tear down and check both runtime files are removed.
        """
        runtime = self.root / "amneziawg"
        runtime.mkdir()
        (runtime / "awg0.name").write_text("utun99\n")
        control = socket.socket(socket.AF_UNIX)
        self.addCleanup(control.close)
        control.bind(str(runtime / "utun99.sock"))
        result = self.run_script('awg() { :; }; wg() { return 97; }; '
                                 'INTERFACE=awg0; get_real_interface; '
                                 'printf "INTERFACE:%s\\n" "$REAL_INTERFACE"; del_if')
        self.assert_ok(result)
        self.assertIn("INTERFACE:utun99", result.stdout)
        self.assertFalse((runtime / "awg0.name").exists())
        self.assertFalse((runtime / "utun99.sock").exists())

    def test_gateway_change_refreshes_exclusion_routes(self):
        """Set old gateways and parsed exclusions, report new gateways to the
        route monitor, and check bypass routes are recreated with new gateways.
        """
        result = self.run_script('parse_options "$TEST_CONFIG"; '
                                 'GATEWAY4=192.0.2.1; GATEWAY6=2001:db8::1; '
                                 'add_excluded_routes; : > "$ROUTE_LOG"; '
                                 'AUTO_ROUTE4=1; AUTO_ROUTE6=1; ENDPOINTS=(); '
                                 'collect_gateways() { GATEWAY4=192.0.2.2; GATEWAY6=2001:db8::2; }; '
                                 'collect_endpoints() { ENDPOINTS=(); }; '
                                 'set_endpoint_direct_route')
        self.assert_ok(result)
        self.assertEqual(self.log.read_text().splitlines(), [
            "-q -n delete -inet 192.168.0.0/24",
            "-q -n delete -inet6 2001:db8::/32",
            "-q -n add -inet 192.168.0.0/24 -gateway 192.0.2.2",
            "-q -n add -inet6 2001:db8::/32 -gateway 2001:db8::2",
        ])

    def test_repeated_setup_adds_each_exclusion_once(self):
        """Set one bypass route, run setup twice before cleanup, and check
        that the same route is added once and deleted once.
        """
        result = self.run_script('EXCLUDED_IPS=(192.168.0.0/24); '
                                 'GATEWAY4=192.0.2.1; add_excluded_routes; '
                                 'add_excluded_routes; del_excluded_routes')
        self.assert_ok(result)
        self.assertEqual(self.log.read_text().splitlines(), [
            "-q -n add -inet 192.168.0.0/24 -gateway 192.0.2.1",
            "-q -n delete -inet 192.168.0.0/24",
        ])

    def test_failed_route_add_does_not_delete_existing_route(self):
        """Make the OS reject a bypass route addition, run cleanup, and
        check it reports the failure without deleting a route it did not create.
        """
        result = self.run_script('route() { printf "%s\\n" "$*" >> "$ROUTE_LOG"; return 1; }; '
                                 'EXCLUDED_IPS=(192.168.0.0/24); GATEWAY4=192.0.2.1; '
                                 'add_excluded_routes; del_excluded_routes')
        self.assert_ok(result)
        self.assertEqual(self.log.read_text().splitlines(), [
            "-q -n add -inet 192.168.0.0/24 -gateway 192.0.2.1",
        ])
        self.assertIn("192.168.0.0/24", result.stderr)


if __name__ == "__main__":
    unittest.main()
