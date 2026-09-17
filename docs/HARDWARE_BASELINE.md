# Hardware — alvo versus evidência

## Notebook alvo informado pelo usuário

Intel Core i7 de 10ª geração, 16 GB RAM, SSD de 256 GB, NVIDIA RTX 2060. Não foram medidos modelo exato do processador, VRAM, espaço livre, driver, temperaturas, potência ou desempenho sustentado.

## Ambiente desta entrega

Os testes foram executados em um container Linux com Python 3.13.5 e NumPy 2.3.5. Esse equipamento **não é o notebook do usuário**. Tempos nos relatórios não servem como estimativa de tempo da RTX 2060.

Não estavam disponíveis para validação o SDK .NET, uma GPU CUDA e um executor Docker real. A tentativa de obter o SDK pela rede falhou. A navegação do Chromium ao serviço de teste foi bloqueada administrativamente; não se tentou contornar a política.

## Capacidade implementada

O runtime principal usa biblioteca padrão/SQLite e não usa GPU. O modelo experimental usa NumPy CPU float64. Adicionar uma RTX não acelera automaticamente esse backend. Não há ajuste automático de VRAM, CUDA, FP16 ou quantização.

## Diagnóstico necessário no notebook

Execute `python -m localauthor diagnose` com `PYTHONPATH=src`. Depois, rode os testes e um treino mínimo com corpus próprio revisado. Registre throughput, RAM, temperatura, espaço e cancelamento. Para energia total, use medição na tomada; consumo da GPU isolado não representa todo o computador.

Limites atuais de configuração: 512 KB por arquivo, 1.500 arquivos por projeto, 32 MB por snapshot, 256 MB de conteúdo lógico armazenado e corpus de treinamento até 8 MB. Não são consumo medido nem quotas físicas globais; históricos e workspaces precisam de política de retenção futura.

O serviço deve permanecer em localhost. Não configure inicialização permanente/24h até validar suspensão, ventilação, disco, backups e recuperação no Windows.
