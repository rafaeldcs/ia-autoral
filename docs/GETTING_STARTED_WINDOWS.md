# Inicialização no notebook de Rafael

Atualização de 17/09/2026: o notebook foi medido e os fluxos centrais foram testados.
Veja [PROGRESS_WINDOWS.md](PROGRESS_WINDOWS.md) para resultados, limitações e o comando
`scripts/validate-windows.ps1`. As seções abaixo preservam o fluxo de operação inicial.

## 1. Preparar sem mexer nos projetos reais

Extraia o ZIP em uma pasta curta, por exemplo `C:\Projetos\ia-local-autoral`. Verifique Python 3.11+ com `py -3 --version`. A versão efetivamente testada nesta entrega foi 3.13.5 no Linux; execute a bateria no Windows antes de uso real.

Defina opcionalmente o diretório de dados **antes** do primeiro comando:

```powershell
$env:LOCALAI_HOME = "C:\LocalAuthorData"
.\scripts\start.ps1
```

Esse diretório não pode ser a raiz de um projeto cadastrado nem ficar dentro dela. Não coloque corpus, bancos ou pesos em `src/`, `docs/` ou `reports/`.

O script não instala software, não baixa modelos e não habilita internet. Ele imprime o token local. Abra `http://127.0.0.1:8765`; o token fica em memória na página, não em URL/localStorage.

## 2. Primeira consulta

Na interface, entre com o token. Importe uma nota curta, por exemplo uma regra escrita por você. Consulte um termo presente. O resultado deve mostrar a fonte e o trecho. Isso é recuperação, não conversa generativa.

Cadastre o caminho absoluto de `examples/laboratory`, indexe e consulte `Product`. A lista de símbolos é lexical; não há análise semântica Roslyn implementada.

## 3. Primeira proposta

Crie uma tarefa no projeto de laboratório, abra `Product.cs` no snapshot e copie o hash exibido. Envie no editor uma proposta no formato:

```json
{
  "changes": [
    {
      "path": "Product.cs",
      "before_sha256": "HASH_REAL_MOSTRADO_NA_INTERFACE",
      "content": "CONTEUDO_COMPLETO_REVISADO_DO_ARQUIVO"
    }
  ]
}
```

A interface já fornece o formato e exibe diferenças. Não substitua o exemplo acima literalmente: use o conteúdo real. Nesta versão, o operador prepara a alteração; o modelo não gera esse patch.

Confira caminhos, código, escopo e limitações dos testes. O runner fica bloqueado sem imagem Docker confiável configurada. Existe aceite explícito de aplicar sem testes, pensado para laboratório: isso não significa que o software validou a alteração. Aplicação exige que o original não tenha mudado desde o snapshot.

## 4. Diagnosticar hardware

No mesmo diretório, sem precisar GPU para abrir a plataforma:

```powershell
$env:PYTHONPATH = "$PWD\src"
py -3 -m localauthor diagnose
```

O relatório é salvo no diretório de dados. Ele tenta usar `nvidia-smi` quando disponível, sem exigir sua existência. Não publica o relatório. Confirme espaço livre, driver, VRAM e carga sustentada no notebook; nenhum benchmark desta entrega mede sua RTX 2060.

## 5. Dependências do laboratório e testes

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\scripts\test.ps1
```

NumPy é opcional para o runtime principal, mas necessário para a bateria completa e o treinamento. Instalação de dependências pode exigir internet; ambiente sem rede precisa de wheels previamente obtidos para sua versão de Python/Windows.

Para usar BPE ou treinamento, siga `DATASET.md`. Não copie código empresarial ou dados de clientes para corpus sem autorização.

## 6. Habilitar pesquisa conscientemente

Encerre o servidor e edite `settings.json` no diretório de dados. Altere `offline` para `false` e especifique `allowed_domains` exatos. Reinicie. A UI recebe URLs diretas; ela não chama Google/Bing ou uma API de busca.

Somente então solicite a coleta. O cache pode reutilizar a cópia sem rede enquanto estiver válido. Fontes sem suporte aos requisitos de coleta podem ser rejeitadas. Volte `offline` para `true` quando terminar. Coleta de internet real não foi validada neste ambiente; os testes usam transportes simulados.

## 7. Backup e recuperação

Pare o servidor com Ctrl+C. Nunca remova `server.lock` sem confirmar que nenhuma instância está ativa.

```powershell
$env:PYTHONPATH = "$PWD\src"
py -3 -m localauthor backup D:\Backups\localauthor.zip
py -3 -m localauthor restore D:\Backups\localauthor.zip C:\LocalAuthorRestaurado
```

A restauração requer destino vazio, não inicia o servidor e cria outro token. Confirme os caminhos dos projetos antes de apontar `LOCALAI_HOME` para a cópia restaurada. O backup pode conter código privado: proteja-o. Backup e restauração agora usam streaming, com limite de 512 MB de conteúdo; não há backup incremental ou criptografado. A restauração valida conteúdo, banco e configurações em pasta temporária antes de publicar o destino.

## 8. Host .NET opcional

Siga `dotnet/README.md` após iniciar Python. Ele disponibiliza a mesma UI em `http://127.0.0.1:5080` e depende do backend local. O host foi compilado e exercitado na continuação Windows. A migração integral para C# continua pendente.

## 9. Publicação privada

Consulte `GITHUB_PUBLICATION.md`. Não envie seu token do GitHub ou o token local da aplicação por chat. Após publicar, verifique a visibilidade privada e os resultados reais dos workflows; o fato de existir um YAML não significa CI aprovado.
