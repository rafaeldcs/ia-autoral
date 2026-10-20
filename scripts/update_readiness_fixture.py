"""Exercise the exact native restart scripts in a real chat renderer."""
import re
from pathlib import Path
from playwright.sync_api import expect


def native_scripts():
    source=(Path(__file__).resolve().parents[1]/'dotnet/LocalAuthor.Client/UpdateReadiness.cs').read_text(encoding='utf-8')
    return {name:re.search(r'const string '+name+r' = """\n(.*?)\n\s*""";',source,re.S)[1]
            for name in ('TrackScript','CanRestartScript')}


def check_readiness(page,check,scripts):
    ready=lambda:page.evaluate(scripts['CanRestartScript'])
    page.wait_for_function('() => ('+scripts['CanRestartScript']+')')
    page.locator('#message-input').fill('Vou apagar este texto')
    check('Native updater preserves a typed chat draft',not ready())
    page.locator('#message-input').fill('')
    page.wait_for_function('() => ('+scripts['CanRestartScript']+')')
    check('Deleting the entire chat draft releases native update readiness',ready())
    page.locator('#conversation-filter').select_option('all')
    check('Conversation filters do not become unsaved forms',ready())
    page.evaluate("""() => {
      const form=document.createElement('form');form.id='update-test-form';
      form.style.cssText='position:fixed;top:80px;right:20px;z-index:10000;background:white;padding:20px';
      form.innerHTML='<input id="update-test-text" value="original"><input id="update-test-check" type="checkbox"><select id="update-test-select"><option>a</option><option>b</option></select><input type="radio" name="update-test-group" id="update-test-a" checked><input type="radio" name="update-test-group" id="update-test-b">';
      document.body.append(form);
    }""")
    page.locator('#update-test-text').fill('alterado')
    check('Unsaved form changes block restart even with an empty chat',not ready())
    page.locator('#update-test-text').fill('original')
    check('Reverting a form edit clears the current dirty state',ready())
    page.locator('#update-test-check').check()
    check('Unsaved checkbox changes block restart',not ready())
    page.locator('#update-test-select').select_option('b')
    page.locator('#update-test-b').check()
    page.locator('#update-test-check').uncheck()
    check('Other unsaved fields still block after reverting one field',not ready())
    page.evaluate("document.getElementById('update-test-form').reset()")
    check('Resetting text, checkbox, radio group and selection releases restart',ready())
    page.locator('#update-test-text').fill('primeiro envio')
    page.evaluate("window.acknowledgeUpdateForm=window.LocalAuthorUpdateReadiness.checkpoint(document.getElementById('update-test-form'))")
    page.locator('#update-test-text').fill('digitado durante o envio')
    page.evaluate("window.acknowledgeUpdateForm()")
    check('Successful save still preserves changes typed during the request',not ready())
    page.locator('#update-test-text').fill('primeiro envio')
    check('Only the successfully saved snapshot is considered clean',ready())
    page.evaluate("document.getElementById('update-test-form').remove();document.getElementById('tools-dialog').showModal()")
    check('An open modal still prevents restart',not ready())
    page.evaluate("document.getElementById('tools-dialog').close();state.requestBusy=true")
    check('An active request still prevents restart',not ready())
    page.evaluate("state.requestBusy=false;state.jobId='explicit-pending-job-fixture'")
    check('An accepted job still prevents restart',not ready())
    page.evaluate("state.jobId=null;window.savedRecovery=window.LocalAuthorRecovery;window.LocalAuthorRecovery={pending:{request_id:'explicit-fixture'},ready:true}")
    check('A recovery checkpoint prevents restarting before request reconciliation',not ready())
    page.evaluate("window.LocalAuthorRecovery=window.savedRecovery;delete window.savedRecovery")
    expect(page.locator('#message-input')).to_have_value('')
    check('All blockers cleared restores readiness without reloading',ready())
    page.locator('#show-rules').click()
    expect(page.locator('#rules-dialog')).to_be_visible()
    page.locator('#done').fill('Acceptance criteria for the update readiness fixture')
    page.locator('#rules-form').evaluate('(form) => form.requestSubmit()')
    expect(page.locator('#rules-dialog')).not_to_be_visible()
    check('A successful preferences API save releases its form without reconnecting',ready())
