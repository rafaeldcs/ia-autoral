"""Actual name selection for disposable browser-test profiles."""


def launch_browser(chromium, **options):
    import sys
    if sys.platform=='win32':
        options.pop('executable_path',None)
        options['channel']='msedge'  # Existing Windows browser; no automatic download.
    return chromium.launch(**options)


def launch_persistent_browser(chromium, directory, **options):
    import sys
    if sys.platform=='win32':options['channel']='msedge'
    return chromium.launch_persistent_context(str(directory),**options)


def enter_profile(page):
    try:
        # On mobile the account control is inside the collapsed sidebar. Its
        # presence still proves profile initialization; visibility does not.
        page.locator('#identity-gate[open], #identity-menu').first.wait_for(state='attached')
    except Exception as exc:
        state=page.evaluate("({path:location.pathname,navigation:performance.getEntriesByType('navigation')[0]?.type,identityLoaded:!!window.LocalAuthorIdentity,locked:document.body.classList.contains('identity-locked'),connectBound:!!document.querySelector('#connect-form')?.onsubmit,transportInputLength:document.querySelector('#local-token')?.value.length,notice:document.querySelector('#notification')?.textContent})")
        raise RuntimeError('Profile chooser did not open: '+str(state)) from exc
    if page.evaluate('Boolean(window.LocalAuthorIdentity.user)'):
        return
    gate=page.locator('#identity-gate')
    page.locator('#identity-name').fill('Browser laboratory')
    page.locator('#identity-submit').click()
    gate.wait_for(state='hidden')


def existing_folder(page):
    if page.locator('#project-existing').count():
        page.locator('#project-existing').check()
