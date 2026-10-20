namespace LocalAuthor.Client;

// Track current edits, rather than remembering forever that an input event occurred.
// This script runs before page scripts, including on subsequent navigations.
internal static class UpdateReadiness
{
    internal const string TrackScript = """
        (() => {
          const fields = new Map();
          const edited = new Set();
          const ignored = '#message-input,#local-token,#response-mode,#input-format,#identity-name,#identity-username,#identity-password,#identity-confirm,#conversation-filter,[data-appearance]';
          const editable = 'input:not([type=hidden]),textarea,select,[contenteditable=true]';
          const value = field => field.matches('[type=checkbox],[type=radio]') ? field.checked :
            field.matches('select') ? JSON.stringify([...field.selectedOptions].map(option => option.value)) :
            field.isContentEditable ? field.textContent : field.value;
          const remember = field => {
            if (field.matches(editable) && !field.matches(ignored) && !fields.has(field)) fields.set(field, value(field));
          };
          const scan = root => {
            if (root instanceof Element) remember(root);
            root.querySelectorAll?.(editable).forEach(remember);
          };
          const hasChanges = () => {
            const changed = [...edited].some(field => value(field) !== fields.get(field));
            window.__localAuthorUpdateDirty = changed;
            return changed;
          };
          // Capture dynamic forms before the first keystroke. Never treat a submit
          // as proof that saving succeeded; reverted/reset fields become clean.
          document.addEventListener('focusin', event => {
            remember(event.target);
            if (fields.has(event.target) && !edited.has(event.target)) fields.set(event.target, value(event.target));
          }, true);
          document.addEventListener('beforeinput', event => remember(event.target), true);
          const changed = event => {
            if (fields.has(event.target)) {
              edited.add(event.target);
              if (event.target.matches('[type=radio]')) for (const field of fields.keys()) {
                if (field.matches('[type=radio]') && field.name === event.target.name && field.form === event.target.form) edited.add(field);
              }
            }
            hasChanges();
          };
          document.addEventListener('input', changed, true);
          document.addEventListener('change', changed, true);
          document.addEventListener('reset', () => queueMicrotask(hasChanges), true);
          new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(scan)))
            .observe(document, {childList:true, subtree:true});
          document.addEventListener('DOMContentLoaded', () => scan(document), {once:true});
          window.__localAuthorUpdateDirty = false;
          const checkpoint = form => {
            scan(form);
            const submitted = [...fields.keys()].filter(field => form.contains(field)).map(field => [field,value(field)]);
            // Acknowledge only after a successful save. Changes typed while the
            // request was in flight still differ from this submitted snapshot.
            return () => {for (const [field,original] of submitted) fields.set(field,original);hasChanges();};
          };
          window.LocalAuthorUpdateReadiness = {hasChanges,checkpoint};
        })()
        """;

    internal const string CanRestartScript = """
        Boolean(document.getElementById('studio') && !document.getElementById('studio').hidden &&
          !document.body.classList.contains('identity-locked') && !document.querySelector('dialog[open]') &&
          typeof state !== 'undefined' && !state.busy && !state.requestBusy && !state.jobId &&
          document.getElementById('message-input')?.value === '' &&
          typeof recovery !== 'undefined' && recovery.ready && !recovery.pending &&
          (!recovery.current || document.getElementById('chat-recovery')?.dataset.saved === 'true') &&
          window.LocalAuthorUpdateReadiness && !window.LocalAuthorUpdateReadiness.hasChanges())
        """;
}
