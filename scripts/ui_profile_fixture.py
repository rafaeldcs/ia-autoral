"""Actual onboarding for disposable browser-test identities, not an auth bypass."""
FIXTURE_PASSPHRASE = 'Disposable browser profile passphrase 123'


def launch_browser(chromium, **options):
    import sys
    if sys.platform=='win32':
        options.pop('executable_path',None)
        options['channel']='msedge'  # Existing Windows browser; no automatic download.
    return chromium.launch(**options)


def enter_profile(page):
    page.locator('#identity-gate[open]:visible, #identity-menu:visible').first.wait_for(state='visible')
    if page.evaluate('Boolean(window.LocalAuthorIdentity.user)'):
        return
    gate=page.locator('#identity-gate')
    if gate.get_attribute('data-setup')=='true':
        page.locator('#identity-name').fill('Browser laboratory')
        page.locator('#identity-confirm').fill(FIXTURE_PASSPHRASE)
    page.locator('#identity-username').fill('browser-lab')
    page.locator('#identity-password').fill(FIXTURE_PASSPHRASE)
    page.locator('#identity-submit').click()
    gate.wait_for(state='hidden')


def existing_folder(page):
    if page.locator('#project-existing').count():
        page.locator('#project-existing').check()
