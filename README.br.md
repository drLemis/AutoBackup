# AutoBackup

[English](README.md) | **Português (BR)**

O AutoBackup monitora silenciosamente a pasta onde você trabalha e salva cópias de backup com data quando você salva um arquivo. Se o Photoshop, Word ou outro programa sobrescrever o mesmo arquivo repetidamente, as últimas versões são mantidas em uma pasta separada.

## Download

[![Baixar aqui!](https://img.shields.io/badge/Baixar-aqui!-2ea44f?style=for-the-badge)](https://github.com/drLemis/AutoBackup/releases/latest)

**[Baixar aqui!](https://github.com/drLemis/AutoBackup/releases/latest)**

1. Clique no link acima (ou no botão verde).
2. Escolha o arquivo para seu sistema (Windows `.exe`, Linux binary ou macOS `.zip`).
3. Execute. Não precisa instalar.

[![License: NWSL](https://img.shields.io/badge/license-NWSL-orange)](LICENSE)

---

## Requisitos

- Windows 10+, Linux (ambiente gráfico) ou macOS
- Uma **pasta de trabalho** (seus projetos)
- Uma **pasta de backup** em um local diferente - não dentro da pasta de trabalho (por exemplo, um disco externo ou `D:\Backups`)

---

## Início rápido

1. Abra o AutoBackup.
2. Clique em **Navegar...** ao lado de **Pasta monitorada** e escolha sua pasta.
3. Clique em **Navegar...** ao lado de **Salvar cópias em** e escolha o destino.
4. Clique em **INICIAR** e deixe a janela aberta.
5. Para ver suas cópias, clique em **Abrir backups**.

A linha abaixo dos botões mostra o que está acontecendo: parado, monitorando ou copiando um arquivo.

**Cores do botão**

| Cor | Significado |
|-----|-------------|
| Cinza | Parado |
| Verde | Monitorando - backups automáticos |
| Laranja | Copiando um arquivo agora |

---

## O que acontece ao salvar

- Quando você pressiona **INICIAR**, o AutoBackup registra quais arquivos já existem. **Apenas os arquivos que você modificar depois** são copiados - não toda a pasta de uma vez.
- Depois de salvar um arquivo, o AutoBackup espera um momento e salva uma cópia com data e hora no nome, ex.: `MyDrawing_20260526_143022.psd`
- As subpastas dentro da sua pasta de trabalho são replicadas da mesma forma na pasta de backup.
- Se você salvar o mesmo arquivo novamente sem alterações reais, o AutoBackup não cria outra cópia.
- Arquivos temporários, caches (`.git`, `node_modules`, `__pycache__`) e lixo do sistema (Thumbs.db, etc.) são excluídos automaticamente.
- Defina quantas cópias manter por arquivo com o seletor **Manter cópias** (1–100).

---

## Pausa e retomada

- Clique em **PAUSAR** para parar o monitoramento temporariamente - a lista de arquivos fica na memória, sem necessidade de nova verificação ao retomar.
- Clique em **RETOMAR** para continuar instantaneamente.
- Use a pausa quando estiver fazendo várias salvaciones que ainda não quer copiar.

---

## Recuperar uma versão antiga

O AutoBackup nunca altera seus arquivos de trabalho por conta própria.

- Clique em **Restaurar...** para navegar por todas as versões de backup com pesquisa, datas e tamanhos.
- Selecione um arquivo e clique em **Restaurar para...** para salvá-lo de volta na sua pasta de trabalho (ou onde você escolher).
- Ou clique em **Abrir** para visualizar um backup sem restaurá-lo.

---

## Informações úteis

- Mantenha o AutoBackup aberto enquanto trabalha - fechá-lo interrompe a proteção.
- A pasta de backup **não** pode estar dentro da pasta de trabalho.
- O aplicativo detecta automaticamente o idioma do Windows (árabe, hebraico, russo) ou você pode trocar a qualquer momento no menu de idiomas (canto inferior direito).
- Marque **Iniciar com Windows** para o AutoBackup abrir automaticamente ao fazer login.
- Marque **Som** para ouvir um som sutil quando um backup for concluído (desligado por padrão).
- O tamanho da pasta de backup é mostrado ao lado do seletor de cópias.
- É um auxiliar para seus arquivos de projeto. Não substitui backups completos do PC, armazenamento em nuvem ou software de backup profissional.

---

## Licença

**Nuclear Waste Software License v1.0 (NWSL)** - [ler licença](LICENSE)

Copyright (c) 2026 drLemis.

---


