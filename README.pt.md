# AutoBackup

[English](README.md) | **Português**

O AutoBackup vigia silenciosamente a pasta onde trabalha e guarda cópias de segurança datadas quando guarda um ficheiro. Se o Photoshop, Word ou outro programa sobrescrever o mesmo ficheiro repetidamente, as últimas versões são mantidas numa pasta separada.

## Transferir

[![Transferir aqui!](https://img.shields.io/badge/Transferir-aqui!-2ea44f?style=for-the-badge)](https://github.com/drLemis/AutoBackup/releases/latest)

**[Transferir aqui!](https://github.com/drLemis/AutoBackup/releases/latest)**

1. Clique no link acima (ou no botão verde).
2. Escolha o ficheiro para o seu sistema (Windows `.exe`, Linux binary ou macOS `.zip`).
3. Execute. Não precisa de instalar.

[![License: NWSL](https://img.shields.io/badge/license-NWSL-orange)](LICENSE)

---

## Requisitos

- Windows 10+, Linux (ambiente gráfico) ou macOS
- Uma **pasta de trabalho** (os seus projetos)
- Uma **pasta de backup** num local diferente - não dentro da pasta de trabalho (por exemplo, um disco externo ou `D:\Backups`)

---

## Início rápido

1. Abra o AutoBackup.
2. Clique em **Procurar...** ao lado de **Pasta de trabalho** e escolha a sua pasta.
3. Clique em **Procurar...** ao lado de **Pasta de backup** e escolha o destino.
4. Clique em **INICIAR** e deixe a janela aberta.
5. Para ver as suas cópias, clique em **Abrir backups**.

A linha por baixo dos botões indica o que se passa: parado, a vigiar ou a copiar um ficheiro.

**Cores do botão**

| Cor | Significado |
|-----|-------------|
| Cinzento | Parado |
| Verde | A vigiar - backups automáticos |
| Laranja | A copiar um ficheiro |

---

## O que acontece ao guardar

- Quando carrega em **INICIAR**, o AutoBackup regista quais ficheiros já existem. **Apenas os ficheiros que alterar depois** são copiados - não toda a pasta de uma vez.
- Depois de guardar um ficheiro, o AutoBackup espera um momento e guarda uma cópia com data e hora no nome, ex.: `MyDrawing_20260526_143022.psd`
- As subpastas dentro da pasta de trabalho são replicadas da mesma forma na pasta de backup.
- Se guardar o mesmo ficheiro novamente sem alterações reais, o AutoBackup não cria outra cópia.
- Ficheiros temporários, caches (`.git`, `node_modules`, `__pycache__`) e lixo do sistema (Thumbs.db, etc.) são excluídos automaticamente.
- Defina quantas cópias manter por ficheiro com o seletor **Manter cópias** (1–100).

---

## Pausa e continuação

- Clique em **PAUSA** para parar a vigilância temporariamente - a lista de ficheiros fica em memória, sem necessidade de nova verificação ao continuar.
- Clique em **CONTINUAR** para retomar instantaneamente.
- Use a pausa quando estiver a fazer várias guardações que ainda não quer copiar.

---

## Recuperar uma versão antiga

O AutoBackup nunca altera os seus ficheiros de trabalho por si só.

- Clique em **Restaurar...** para navegar por todas as versões de backup com pesquisa, datas e tamanhos.
- Selecione um ficheiro e clique em **Restaurar para...** para o guardar na sua pasta de trabalho (ou onde preferir).
- Ou clique em **Abrir** para pré-visualizar um backup sem o restaurar.

---

## Informações úteis

- Mantenha o AutoBackup aberto enquanto trabalha - fechá-lo interrompe a proteção.
- A pasta de backup **não** pode estar dentro da pasta de trabalho.
- A aplicação deteta automaticamente o idioma do Windows (árabe, hebraico, russo) ou pode mudar a qualquer momento no menu de idiomas (canto inferior direito).
- Marque **Iniciar com o Windows** para o AutoBackup abrir automaticamente ao iniciar sessão.
- Marque **Som** para ouvir um som subtil quando um backup for concluído (desligado por predefinição).
- O tamanho da pasta de backup é mostrado junto ao seletor de cópias.
- É uma ajuda para os seus ficheiros de projeto. Não substitui cópias de segurança completas do PC, armazenamento na nuvem ou software de backup profissional.

---

## Licença

**Nuclear Waste Software License v1.0 (NWSL)** - [ler licença](LICENSE)

Copyright (c) 2026 drLemis.

---


