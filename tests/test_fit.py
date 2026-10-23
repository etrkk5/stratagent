import copy
import io
import json
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch

from stratagent.cli import main
from stratagent.common import StratagentError
from stratagent.experience import begin, guide, render
from stratagent.fit import review
from stratagent.mcp import RPCError, Server
from stratagent.orchestration import Orchestrator
from stratagent.service import Stratagent
from test_architect import FakeRegistry
from test_runtime_research import PROMPT, model_plan
from test_stratagent import FakeGitHub, file_state


class FitTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.service = Stratagent(self.root, github=FakeGitHub(), registry=FakeRegistry())
        self.driver = Orchestrator(self.service)
        self.prompt = 'Build a Python API with tests. No payments.'

    def start(self, targets=None):
        return self.driver.start(self.prompt, targets or ['codex'])

    def assessment(self, result, outcome='keep'):
        request = result['model_request']['fit_request']
        return {'schema_version': 1, 'context_digest': request['context_digest'], 'environment_digest': request['environment_digest'],
                'outcome': outcome, 'reason': 'Use the existing coding host to implement and test the small API without new extensions.',
                'needs': [{'need': 'Implement and test the API', 'quote': 'Python API with tests',
                           'status': 'host' if outcome == 'keep' else 'gap',
                           'reason': 'The host can perform the requested implementation; no extension is justified.' if outcome == 'keep' else 'Research the requested testing capability before choosing an extension.',
                           'evidence_refs': ['request'], 'existing': []}],
                'alternatives': ['Research an additional testing skill only if current coverage proves insufficient.']}

    def propose(self, result, assessment=None):
        return self.driver.submit(result['session']['id'], result['model_request']['request_id'],
                                  {'action': 'assess', 'assessment': assessment or self.assessment(result)})

    def skill(self):
        path = self.root / '.agents/skills/testing/SKILL.md'
        path.parent.mkdir(parents=True)
        path.write_text('---\nname: testing\ndescription: Python API tests and regression review.\n---\nUser-owned test guidance.\n')
        return path

    def test_initial_model_can_assess_without_requiring_network_or_installation(self):
        started = self.start()
        self.assertIn('assess', started['model_request']['allowed_actions'])
        before = file_state(self.root)
        card = guide(self.service)
        self.assertEqual(card['phase'], 'assess')
        self.assertEqual(before, file_state(self.root))
        self.assertFalse(self.service.github.calls or self.service.registry.calls)
        self.assertFalse(self.service.lock()['installations'])

    def test_keep_review_accept_cli_and_repeat_preserve_original_environment(self):
        self.skill()
        original = (self.root / '.agents/skills/testing/SKILL.md').read_bytes()
        started = self.start()
        with patch('urllib.request.urlopen', side_effect=AssertionError('network')):
            proposed = self.propose(started)
            card = guide(self.service)
            self.assertEqual(card['phase'], 'fit-review')
            self.assertEqual(proposed['fit_review']['environment_changes'], [])
            self.assertNotIn(proposed['fit_review']['approval'], render(card))
            self.assertIn('Needs and coverage:', render(card))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(card['next_action']['argv'][3:]), 0)
            self.assertEqual(guide(self.service)['phase'], 'kept')
            before = file_state(self.root)
            self.driver.accept_fit(started['session']['id'], proposed['fit_review']['approval'])
            self.assertEqual(before, file_state(self.root))
        state = self.driver.status(started['session']['id'])['session']
        self.assertEqual(state['usage'], {'model_turns': 1, 'search_rounds': 0, 'network_reserved': 0})
        self.assertFalse(self.service.lock()['installations'])
        self.assertEqual((self.root / '.agents/skills/testing/SKILL.md').read_bytes(), original)
        self.assertEqual(begin(self.service, self.prompt, ['codex'])['phase'], 'kept')
        self.assertFalse(self.service.github.calls or self.service.registry.calls)

    def test_existing_coverage_cites_current_native_definition_without_adopting_it(self):
        self.skill()
        started = self.start()
        assessment = self.assessment(started)
        reference = started['model_request']['fit_request']['environment']['files'][0]['evidence_id']
        assessment['needs'][0].update(status='existing', existing=[reference], evidence_refs=['request', reference])
        result = Server(self.root, orchestration=started['session']['id']).call_tool('stratagent_session_submit', {
            'request_id': started['model_request']['request_id'], 'response': {'action': 'assess', 'assessment': assessment}})
        self.assertFalse(result['isError'])
        proposal = json.loads(result['content'][0]['text'])
        self.driver.accept_fit(started['session']['id'], proposal['fit_review']['approval'])
        self.assertEqual(self.service.environment()['files'][0]['ownership'], 'user-owned')
        self.assertFalse(self.service.lock()['installations'])

    def test_research_assessment_explains_gaps_and_survives_to_review_apply(self):
        self.prompt = PROMPT
        started = self.start(['generic'])
        assessment = self.assessment(started, 'research')
        assessment['needs'][0]['quote'] = PROMPT[:20]
        researched = self.propose(started, assessment)
        self.assertEqual(researched['session']['state'], 'research-needed')
        self.assertNotIn('assess', researched['model_request']['allowed_actions'])
        self.assertEqual(researched['model_request']['assessment'], assessment)
        session = started['session']['id']
        planned = self.driver.submit(session, researched['model_request']['request_id'], {'action': 'research', 'plan': model_plan(self.service, github=False)})
        compared = self.driver.search(session, planned['search_review']['approval'])
        self.assertEqual(compared['model_request']['assessment'], assessment)
        decision = copy.deepcopy(compared['model_request']['decision_request']['suggested_decision'])
        for binding in decision['bindings']:
            binding['skills'], binding['mcps'] = [], []
        self.driver.submit(session, compared['model_request']['request_id'], {'action': 'decide', 'decision': decision})
        card = guide(self.service)
        self.assertEqual(card['review']['assessed_needs'], assessment['needs'])
        self.assertIn('Assessed needs:', render(card))
        stage = self.service.stage('blueprint', **self.driver.review(session))
        self.service.apply_stage(stage['stage_id'], stage['plan']['approval'])
        self.assertEqual(guide(self.service)['phase'], 'ready')
        self.assertTrue(self.service.verify()['ok'])

    def test_unknown_missing_mismatched_or_unquoted_evidence_is_rejected(self):
        self.skill()
        started = self.start()
        base = self.assessment(started)
        for modify in (lambda a: a['needs'][0].update(quote='Invented request'),
                       lambda a: a['needs'][0].update(evidence_refs=['not-observed']),
                       lambda a: a['needs'][0].update(status='existing', existing=['not-observed']),
                       lambda a: a['needs'].append(copy.deepcopy(a['needs'][0]))):
            value = copy.deepcopy(base)
            modify(value)
            with self.assertRaises(StratagentError):
                review(self.service, value, started['session']['id'])
        self.assertEqual(self.driver.status(started['session']['id'])['session']['usage']['model_turns'], 0)

    def test_no_change_with_gaps_and_research_without_gaps_are_rejected(self):
        started = self.start()
        for outcome, status in [('keep', 'gap'), ('keep', 'unknown'), ('research', 'host')]:
            value = self.assessment(started)
            value['outcome'], value['needs'][0]['status'] = outcome, status
            with self.assertRaises(StratagentError):
                review(self.service, value, started['session']['id'])

    def test_partial_inventory_cannot_be_relabelled_sufficient(self):
        path = self.root / 'AGENTS.md'
        path.write_bytes(b'x' * (256 * 1024 + 1))
        started = self.start()
        with self.assertRaisesRegex(StratagentError, 'Incomplete'):
            self.propose(started)
        self.assertEqual(self.driver.status(started['session']['id'])['session']['usage']['model_turns'], 1)
        self.assertFalse(self.service.lock()['installations'])
        from stratagent.fit import request as fit_request
        (self.root / '.stratagent/lock.json').write_bytes(b'[' * 10000)
        with self.assertRaisesRegex(StratagentError, 'Ownership metadata'):
            fit_request(self.service)

    def test_cross_host_coverage_is_not_inferred_from_matching_names(self):
        self.skill()
        started = self.start(['claude'])
        value = self.assessment(started)
        reference = started['model_request']['fit_request']['environment']['files'][0]['evidence_id']
        value['needs'][0].update(status='existing', existing=[reference], evidence_refs=['request', reference])
        with self.assertRaisesRegex(StratagentError, 'every selected host'):
            self.propose(started, value)

    def test_model_bridge_can_propose_but_cannot_accept_or_inject_authority(self):
        started = self.start()
        server = Server(self.root, orchestration=started['session']['id'])
        self.assertEqual(len(server.tools), 2)
        for name in ('stratagent_session_accept_fit', 'stratagent_accept_fit'):
            with self.assertRaises(RPCError):
                server.call_tool(name, {})
        assessment = self.assessment(started)
        assessment['approve'] = True
        with self.assertRaises(StratagentError):
            self.propose(started, assessment)
        self.assertEqual(self.driver.status(started['session']['id'])['session']['state'], 'research-needed')
        self.assertFalse(self.service.lock()['installations'])

    def test_approval_binds_session_and_wrong_approval_cannot_record_completion(self):
        started = self.start()
        proposed = self.propose(started)
        before = file_state(self.root)
        with self.assertRaises(StratagentError):
            self.driver.accept_fit(started['session']['id'], 'yes')
        self.assertEqual(before, file_state(self.root))
        second = self.start()
        second_proposal = self.propose(second)
        self.assertNotEqual(proposed['fit_review']['approval'], second_proposal['fit_review']['approval'])
        with self.assertRaises(StratagentError):
            self.driver.accept_fit(second['session']['id'], proposed['fit_review']['approval'])

    def test_changed_local_setup_invalidates_review_and_completed_keep(self):
        path = self.skill()
        started = self.start()
        proposed = self.propose(started)
        self.driver.accept_fit(started['session']['id'], proposed['fit_review']['approval'])
        path.write_text(path.read_text() + 'User change.\n')
        before = file_state(self.root)
        self.assertEqual(guide(self.service)['phase'], 'context-changed')
        with self.assertRaises(StratagentError):
            self.driver.accept_fit(started['session']['id'], proposed['fit_review']['approval'])
        self.assertEqual(before, file_state(self.root))

    def test_managed_ownership_record_changes_invalidate_keep_even_with_same_definition_counts(self):
        started = self.start()
        proposed = self.propose(started)
        path = self.root / '.stratagent/lock.json'
        path.write_bytes(path.read_bytes() + b'\n')
        self.assertEqual(guide(self.service)['phase'], 'context-changed')
        with self.assertRaises(StratagentError):
            self.driver.accept_fit(started['session']['id'], proposed['fit_review']['approval'])

    def test_expired_cancelled_and_resumed_fit_preserve_budgets(self):
        started = self.start()
        proposed = self.propose(started)
        session = started['session']['id']
        with patch('stratagent.orchestration.time.time', return_value=started['session']['deadline_at']):
            with self.assertRaisesRegex(StratagentError, 'expired'):
                self.driver.accept_fit(session, proposed['fit_review']['approval'])
            self.assertEqual(guide(self.service)['phase'], 'paused')
        self.driver.cancel(session)
        with self.assertRaises(StratagentError):
            self.driver.accept_fit(session, proposed['fit_review']['approval'])
        resumed = self.driver.resume(session)
        self.assertIn('assess', resumed['model_request']['allowed_actions'])
        self.assertEqual(resumed['session']['usage']['model_turns'], 1)
        self.assertFalse(resumed['session'].get('fit'))

    def test_keep_is_not_a_blueprint_or_installation_authority(self):
        started = self.start()
        proposed = self.propose(started)
        self.driver.accept_fit(started['session']['id'], proposed['fit_review']['approval'])
        with self.assertRaises(StratagentError):
            self.driver.review(started['session']['id'])
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertNotEqual(main(['stage', 'blueprint', '--session', started['session']['id'], '--workspace', str(self.root)]), 0)
        self.assertFalse(self.service.lock()['installations'])

    def test_scan_opt_out_still_allows_host_assessment_without_reading_definitions(self):
        self.service.init(self.prompt, ['codex'], scan_project=False)
        with patch('stratagent.service.inspect_environment', side_effect=AssertionError('scan')):
            started = self.start()
            self.assertIsNone(started['model_request']['fit_request']['environment'])
            proposed = self.propose(started)
            self.driver.accept_fit(started['session']['id'], proposed['fit_review']['approval'])
            self.assertEqual(guide(self.service)['phase'], 'kept')

    def test_changing_fit_text_or_using_stale_model_request_is_rejected(self):
        started = self.start()
        proposed = self.propose(started)
        before = file_state(self.root)
        changed = self.assessment(started)
        changed['reason'] = 'Different justification.'
        with self.assertRaises(StratagentError):
            self.propose(started, changed)
        self.assertEqual(before, file_state(self.root))
        self.assertEqual(self.driver.status(started['session']['id'])['session']['state'], 'fit-review-required')

    def test_keep_acceptance_cannot_hide_drift_in_an_owned_nondefinition(self):
        self.service.init(self.prompt, ['codex'])
        prepared = self.service.prepare(self.prompt, offline=True)
        self.service.blueprint(approval=prepared['blueprint']['approval'], apply=True, run_id=prepared['research_run']['id'])
        started = self.start()
        proposed = self.propose(started)
        output = self.root / '.stratagent/task-plan.json'
        output.write_bytes(output.read_bytes() + b'\nUser change\n')
        before = file_state(self.root)
        with self.assertRaisesRegex(StratagentError, 'drift'):
            self.driver.accept_fit(started['session']['id'], proposed['fit_review']['approval'])
        self.assertEqual(before, file_state(self.root))
        self.assertEqual(guide(self.service)['phase'], 'drift')

    def test_turkish_need_and_reason_preserve_the_actual_request(self):
        self.prompt = 'Python API ve testler geliştir. Ödeme olmasın.'
        started = self.start()
        assessment = self.assessment(started)
        assessment['reason'] = 'Mevcut ajan bu küçük API için yeterli; ek araç gerekli değil.'
        assessment['needs'][0].update(need='API ve testleri geliştir', quote='Python API ve testler',
                                      reason='Uygulama ve test işi mevcut kodlama ajanıyla yapılabilir.')
        proposed = self.propose(started, assessment)
        self.assertIn(assessment['reason'], render(guide(self.service)))
        self.driver.accept_fit(started['session']['id'], proposed['fit_review']['approval'])
        self.assertEqual(self.service.manifest()['analysis']['prompt'], self.prompt)
        self.assertEqual(guide(self.service)['phase'], 'kept')
