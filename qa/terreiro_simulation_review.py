"""Evidence adapter for the bounded neural scheduler, not a semantic site agent.

The caller provides one fresh, isolated run directory. A plan is never a receipt.
Builds/tests are a batch, as are business HTTP tests; observe completed work only.
"""
from terreiro_qa_policy import FIELDS, STAGES

COMMANDS = {'node-test', 'processor-test', 'dotnet-test', 'next-build', 'dotnet-publish'}
HTTP_STAGES = {'authentication', 'permissions', 'dues', 'treasury', 'stock',
               'administration', 'communication', 'documents'}


def checks_pass(report):
    checks = report.get('checks', [])
    return report.get('success') is True and bool(checks) and all(c.get('passed') is True for c in checks)


def observations(sandbox, builds=None, http=None, followup=None, browser=None, interactions=None):
    state = dict.fromkeys(FIELDS, False)
    state['authorized'] = sandbox.get('syntheticOnly') is True and sandbox.get('origin') == 'http://localhost:3180'
    state['sandbox'] = (state['authorized'] and sandbox.get('verified') is True
                        and sandbox.get('readOnly') is True and sandbox.get('user') == '10001:10001'
                        and 'ALL' in sandbox.get('capDrop', [])
                        and 'no-new-privileges' in sandbox.get('security', []))
    if not state['sandbox']:
        state['authorized'] = False
    if builds is not None:
        rows = builds.get('results', [])
        state['failure'] = any(r.get('passed') is not True or r.get('exitCode') != 0 for r in rows)
        complete = (builds.get('success') is True and builds.get('complete') is True
                    and {r.get('name') for r in rows} >= COMMANDS and not state['failure'])
        state['build'] = state['unit'] = complete
    for report in (http, followup, browser, interactions):
        if report is not None and not checks_pass(report):
            state['failure'] = True
    if http is not None and checks_pass(http):
        seen = {c.get('stage') for c in http['checks']}
        for stage in HTTP_STAGES:
            state[stage] = stage in seen
    state['browser'] = (browser is not None and interactions is not None
                        and checks_pass(browser) and checks_pass(interactions))
    # Evidence requires all functional receipts, including follow-up cases.
    state['evidence'] = (all(state[s] for s in STAGES if s != 'evidence')
                         and followup is not None and checks_pass(followup) and not state['failure'])
    return state


def required_action(state):
    """Independent deterministic review of the proposal; never substitutes for it."""
    if not state['authorized']:
        return 'STOP_SCOPE'
    if state['failure']:
        return 'INVESTIGATE_FAILURE'
    return next(('CHECK_' + s.upper() for s in STAGES if not state[s]), 'REPORT')
