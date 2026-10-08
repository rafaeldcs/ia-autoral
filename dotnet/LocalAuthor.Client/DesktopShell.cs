namespace LocalAuthor.Client;

// Only the pinned top-level server page may open the local administration menu.
// No file paths, credentials or arbitrary commands cross this bridge.
internal static class DesktopShell
{
    internal static bool Accepts(string source, Uri origin, string command) =>
        command == "desktop-settings" && Uri.TryCreate(source, UriKind.Absolute, out var uri) &&
        uri.Scheme == origin.Scheme && uri.Host == origin.Host && uri.Port == origin.Port &&
        uri.UserInfo.Length == 0;

    internal const string MountScript = """
        (() => {
          if (document.getElementById('desktop-settings')) return;
          const button = document.createElement('button');
          button.id = 'desktop-settings';
          button.type = 'button';
          button.textContent = 'Conexão e atualizações deste aplicativo';
          button.onclick = () => window.chrome.webview.postMessage('desktop-settings');
          document.addEventListener('keydown', event => {
            if (event.ctrlKey && !event.altKey && event.key === ',') {
              event.preventDefault();
              window.chrome.webview.postMessage('desktop-settings');
            }
          });
          const tools = document.getElementById('tools-dialog');
          if (tools) {
            const section = document.createElement('section');
            section.className = 'desktop-settings';
            const heading = document.createElement('h3');
            heading.textContent = 'Este computador';
            const description = document.createElement('p');
            description.textContent = 'O servidor é localizado e as atualizações são verificadas automaticamente. Aqui você pode consultar a conexão ou publicar uma versão.';
            section.append(heading, description, button);
            tools.append(section);
          } else {
            button.style.cssText = 'position:fixed;bottom:12px;right:12px;z-index:1000';
            button.textContent = 'Configurações do aplicativo';
            document.body.append(button);
          }
        })()
        """;
}
