"""Offline contracts for inactive patches; no provider, API or cluster access."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAGES = ('10-backend-safety.patch', '20-auth-bridge.patch', '30-enable-private-lmtp.patch')
OLD_FILTER = '''  enable_spam_filter = {
    else = "is_empty(authenticated_as)"
    match = [
      {
        if   = "listener == 'edge-lmtp'"
        then = "false"
      },
    ]
  }'''
NEW_FILTER = OLD_FILTER.replace('"is_empty(authenticated_as)"', '"false"').replace('then = "false"', 'then = "true"')


def copy_stack(destination):
    target = destination / 'tofu/stalwart'
    target.mkdir(parents=True)
    for source in (ROOT / 'tofu/stalwart').glob('*.tf'):
        shutil.copy2(source, target / source.name)
    shutil.copy2(ROOT / 'tofu/stalwart/.terraform.lock.hcl', target / '.terraform.lock.hcl')
    return target


def apply_stage(destination, name):
    patch = HERE / 'stages' / name
    allowed = {'tofu/stalwart/filtering.tf', 'tofu/stalwart/filtering-bridge.tf',
               'tofu/stalwart/filtering-bridge.json', 'tofu/stalwart/main.tf'}
    paths = re.findall(r'^\+\+\+ b/(.+)$', patch.read_text(), re.M)
    if not paths or not set(paths) <= allowed:
        raise AssertionError('Unexpected patch destination')
    for arguments in (['--check'], []):
        subprocess.run(['git', 'apply', *arguments, str(patch)], cwd=destination,
                       check=True, capture_output=True, timeout=10)


class FilteringContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='company-filtering-contract-')
        cls.addClassCleanup(cls.directory.cleanup)
        cls.work = Path(cls.directory.name)
        cls.stack = copy_stack(cls.work)
        cls.original = {p.name: p.read_bytes() for p in cls.stack.iterdir()}
        for stage in STAGES[:2]:
            apply_stage(cls.work, stage)
        cls.pre_enable = (cls.stack / 'main.tf').read_bytes()
        apply_stage(cls.work, STAGES[2])
        cls.bridge_tf = (cls.stack / 'filtering-bridge.tf').read_text()
        cls.spec = json.loads((cls.stack / 'filtering-bridge.json').read_text())
        cls.proof = json.loads((HERE / 'qualification.json').read_text())

    def test_inactive_and_only_explicit_data_stage_change(self):
        active = ROOT / 'tofu/stalwart'
        for filename in ('filtering.tf', 'filtering-bridge.tf', 'filtering-bridge.json'):
            self.assertFalse((active / filename).exists(), 'Staged configuration was promoted')
        self.assertEqual(self.pre_enable, self.original['main.tf'])
        original = self.original['main.tf'].decode()
        self.assertEqual(original.count(OLD_FILTER), 1)
        expected = original.replace(OLD_FILTER, NEW_FILTER).replace(
            'resource "stalwart_mta_stage_data" "this" {',
            'resource "stalwart_mta_stage_data" "this" {\n  depends_on = [stalwart_spam_rule_any.auth_na]\n')
        self.assertEqual((self.stack / 'main.tf').read_text(), expected)
        for name, data in self.original.items():
            if name != 'main.tf':
                self.assertEqual((self.stack / name).read_bytes(), data)
        # Includes SenderAuth, SASL requirements, routes, thresholds and LMTP identity.
        before_auth = original.split('resource "stalwart_sender_auth"', 1)[1].split('\n}\n', 1)[0]
        after_auth = (self.stack / 'main.tf').read_text().split('resource "stalwart_sender_auth"', 1)[1].split('\n}\n', 1)[0]
        self.assertEqual(before_auth, after_auth)
        delivery = (self.stack / 'delivery.tf').read_text()
        self.assertRegex(delivery, r'''require\s*=\s*\{\s*match\s*=\s*\[\{\s*if\s*=\s*"listener == 'edge-lmtp'"\s*then\s*=\s*"false"\s*\}\]\s*else\s*=\s*"true"\s*\}''')

    def test_frozen_safety_settings_and_conversion(self):
        expected = {
            'stages/10-backend-safety.patch': '06a2f577562fda4a76935d321123ef6a90097c64cdb8e2b410e7b058a92f82aa',
            'convert-blocked-domain.json': 'a120976117fa52544131475ba9b60a118b9aa278fcec1ebb4774a95dcd17476f',
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((HERE / name).read_bytes()).hexdigest(), digest)
        call = json.loads((HERE / 'convert-blocked-domain.json').read_text())['methodCalls'][0]
        self.assertEqual(call[:2], ['x:SpamTag/set', {'update': {'jdzlxyqedpaa': {
            '@type': 'Score', 'tag': 'BLOCKED_DOMAIN', 'score': 1000}}}])
        safety = (self.stack / 'filtering.tf').read_text()
        self.assertIn('/download/v3.0.1/spam-filter-rules.json.gz', safety)
        self.assertNotIn('releases/latest', safety)
        for key, value in [('score_spam', '5'), ('score_reject', '0'), ('score_discard', '0'),
                           ('trust_contacts', 'true'), ('trust_replies', 'true')]:
            self.assertRegex(safety, rf'\b{key}\s*=\s*{value}\b')

    def test_rules_equal_qualified_native_rules_except_explicit_ip_removal(self):
        self.assertEqual(self.proof['binarySha256'], '02030a8334e3bc62bae1fa4a9139f498df0a7e105bd97ec5beacfdfa1be8b614')
        self.assertEqual(self.proof['inventory'], {'tags': 403, 'rules': 66, 'convertedToScore': ['BLOCKED_DOMAIN']})
        self.assertEqual(len(self.proof['nativeStages']), 21)
        self.assertEqual(len(self.proof['messageResults']), 20)
        self.assertEqual(self.proof['queueEmptyReadback'], {'ids': [], 'total': 0})
        for name in ('nullEnvelopeAuthenticatedBounceNoFalseAuthNa',
                     'queuedForwardingVerdictSurvivesBothNativeRestarts',
                     'nativeVerdictProductionAndJunkPlacementAfterRestart'):
            self.assertEqual(self.proof['nativeStages'][name]['status'], 'PASS')
        self.assertTrue(all(t['status'] == 'PASS' for t in self.proof['nativeStages'].values()))
        native = self.proof['nativeBridgeConfig']['backendRules']
        self.assertEqual(set(self.spec['rules']), {rule['name'].lower() for rule in native})
        self.assertNotRegex(json.dumps(self.spec), r'remote_ip|10\.200\.|is_ip_in_cidr')
        for rule in native:
            actual = self.spec['rules'][rule['name'].lower()]
            self.assertEqual((actual['name'], actual['priority']), (rule['name'], rule['priority']))
            self.assertEqual(len(actual['match']), len(rule['condition']['match']))
            for number, branch in enumerate(actual['match']):
                qualified = rule['condition']['match'][str(number)]
                self.assertEqual(qualified['if'].count("remote_ip == '10.200.0.2' && "), 1)
                self.assertEqual(f"({self.spec['gate']}) && ({branch['if']})",
                                 qualified['if'].replace("remote_ip == '10.200.0.2' && ", '', 1))
                self.assertEqual(branch['then'], qualified['then'])
        self.assertIn('for_each = local.edge_auth_bridge.rules', self.bridge_tf)
        self.assertIn('if   = format("(%s) && (%s)", local.edge_auth_bridge.gate, branch.if)', self.bridge_tf)
        self.assertIn('then = branch.then', self.bridge_tf)
        self.assertIn('enable   = true', self.bridge_tf)

    def tags(self, value, name='x-edge-auth'):
        context = {'name_lower': name, 'value': value, 'value_lower': value.lower(), 'true': True,
                   'contains': lambda text, part: part in text,
                   'matches': lambda pattern, text: re.fullmatch(pattern, text) is not None}
        result = set()
        for rule in self.spec['rules'].values():
            for branch in rule['match']:
                expression = f"({self.spec['gate']}) && ({branch['if']})"
                expression = re.sub(r'!(?!=)', ' not ', expression.replace('&&', ' and ').replace('||', ' or '))
                if eval(expression.strip(), {'__builtins__': {}}, context):
                    result.add(branch['then'].strip("'"))
                    break
        return result

    def test_entire_canonical_header_required_before_any_mapping(self):
        valid = 'spf=pass; dkim=pass; dmarc=pass; policy=none;'
        for malformed in ('garbage', valid.replace('spf=', 'xspf='), valid + ' junk',
                          valid.replace('spf=pass;', 'spf=pass; spf=fail;'),
                          valid.replace('policy=none;', ''), valid.replace('spf=pass', 'spf=bogus'),
                          valid.replace('dkim=pass', 'dkim=softfail'), valid.replace('dmarc=pass', 'dmarc=neutral'),
                          valid.replace('policy=none', 'policy=bogus')):
            with self.subTest(value=malformed):
                self.assertEqual(self.tags(malformed), set())
        self.assertEqual(self.tags(valid, 'authentication-results'), set())
        self.assertEqual(self.tags('spf=fail; dkim=pass; dmarc=pass; policy=reject;'),
                         {'SPF_FAIL', 'DKIM_ALLOW', 'DMARC_POLICY_ALLOW', 'EDGE_DMARC_NA_OFFSET', 'EDGE_AUTH_VALID'})
        self.assertIn('AUTH_NA', self.tags('spf=none; dkim=none; dmarc=none; policy=none;'))
        self.assertIn('AUTH_NA_OR_FAIL', self.tags('spf=none; dkim=permerror; dmarc=none; policy=none;'))

    def test_real_auth_na_override_and_only_two_new_score_tags(self):
        self.assertEqual(set(re.findall(r'^resource "([^"]+)" "([^"]+)"', self.bridge_tf, re.M)), {
            ('stalwart_spam_tag_score', 'edge_auth_valid'),
            ('stalwart_spam_tag_score', 'edge_dmarc_na_offset'),
            ('stalwart_spam_rule_header', 'edge_auth'), ('stalwart_spam_rule_any', 'auth_na')})
        expected = self.proof['nativeBridgeConfig']['backendRuleOverrides'][0]
        self.assertIn('resource "stalwart_spam_rule_any" "auth_na"', self.bridge_tf)
        self.assertIn('name     = "STWT_AUTH_NA"', self.bridge_tf)
        self.assertIn('priority = 1004', self.bridge_tf)
        self.assertIn(expected['condition']['match']['0']['if'], self.bridge_tf)
        self.assertIn('id = "jdzlxyp2ataa"', self.bridge_tf)
        self.assertNotIn('EDGE_AUTH_NA_OFFSET', self.bridge_tf + json.dumps(self.spec))
        tag_bodies = re.findall(r'resource "stalwart_spam_tag_score" "[^"]+" \{(.*?)\n\}', self.bridge_tf, re.S)
        actual = {re.search(r'tag\s*=\s*"([^"]+)"', body)[1]: float(re.search(r'score\s*=\s*(-?[0-9.]+)', body)[1])
                  for body in tag_bodies}
        self.assertEqual(actual, {t['tag']: t['score'] for t in self.proof['nativeBridgeConfig']['backendTags']})
        self.assertEqual(actual, {'EDGE_DMARC_NA_OFFSET': -1, 'EDGE_AUTH_VALID': 0})
        script = self.proof['nativeBridgeConfig']['edgeScript']['contents']
        self.assertIn('deleteheader "Authentication-Results";', script)
        self.assertNotIn('ARC-', script)

    def test_existing_cnp_port24_has_both_identity_labels(self):
        policy = (ROOT / 'apps/stalwart/network-policy.yaml').read_text()
        rules = [rule for rule in re.split(r'(?m)^    - ', policy) if 'port: "24"' in rule]
        self.assertEqual(len(rules), 1)
        self.assertIn('fromEndpoints:', rules[0])
        self.assertIn('k8s:io.kubernetes.pod.namespace: stalwart-edge', rules[0])
        self.assertIn('k8s:app: stalwart-edge', rules[0])
        self.assertNotIn('fromCIDR:', rules[0])
        self.assertNotIn('fromEntities:', rules[0])


if __name__ == '__main__':
    unittest.main()
