# Hardware — alvo versus evidência

## Medição no notebook em 17/09/2026

Windows 11, Python 3.14.7, 12 CPUs lógicas, aproximadamente 16 GiB de RAM física,
RTX 2060 com 6 GiB de VRAM (driver 517.00), volume de aproximadamente 476 GiB com
225 GiB livres. Valores instantâneos em `reports/hardware-windows.json`.
SDK .NET 10.0.301 compilou o host e o laboratório. Docker CLI existe, mas o daemon
estava indisponível. O backend continua CPU; detectar GPU não é testar CUDA.
Veja [PROGRESS_WINDOWS.md](PROGRESS_WINDOWS.md). As seções seguintes registram a
estimativa original e o ambiente da primeira entrega.

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
