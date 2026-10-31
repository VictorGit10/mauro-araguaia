# Regras comuns às três frentes (leia antes do PEDIDO.md)

Você é um agente trabalhando para o Victor Amaral (LAPIG/UFG), que dá encontros individuais de 40 minutos sobre **uso de IA generativa para resolver problemas de pesquisa**. Cada pasta tem o pedido de uma pessoa (CONTEXTO.md) e o que queremos que você **execute** (PEDIDO.md).

O padrão que já funcionou em encontros anteriores:
- **Executar com dados públicos reais**, não só descrever. Um teste pequeno e verdadeiro vale mais que um plano grande.
- **Ter um controle.** Antes de concluir algo, mostrar a comparação que prova que o resultado não é artefato (uma referência simples, um caso conhecido, um teste que falharia se houvesse erro).
- **A IA faz o mecânico; a pessoa decide.** Nada de decidir a metodologia científica pela pessoa. Mostre opções, custos e limites.
- **Deixar o trabalho pronto para a IA da pessoa continuar:** `README.md` para gente e `CLAUDE.md` (com `AGENTS.md` apontando para ele) com contexto, dados, ordem dos scripts e armadilhas encontradas.

## Regras
1. Escreva tudo em **português**, claro, sem jargão desnecessário.
2. **Todo número** que aparecer nos relatórios precisa ter saído de um script desta pasta que você rodou. Diga qual. Se não conferiu, escreva "não conferido".
3. **Não invente referências.** Toda referência citada precisa ter DOI conferido em `https://api.crossref.org/works/<doi>` (título bate). As que não conferirem saem.
4. **Não crie contas, não faça login, não use credenciais.** Se um dado exige cadastro (Earthdata, Copernicus CDS, chave de API), registre isso em `RELATORIO.md` e siga com uma alternativa aberta.
   - Exceção: o Google Earth Engine já está autenticado nesta máquina. Use `ee.Initialize(project='SEU-PROJETO-EARTH-ENGINE')`. Mantenha o processamento pequeno (área de teste, poucos milhares de pontos) e anote no relatório quantas chamadas pesadas fez.
5. **Limite de download: 1 GB por frente.** Prefira recortes e serviços que entregam só o necessário.
6. Trabalhe só dentro desta pasta. Código em `codigo/`, dados em `dados/` (não comite dados grandes), figuras em `figuras/`.
7. **Sem dados pessoais**: não escreva nomes ou e-mails de pessoas nas saídas. Refira-se a "o pesquisador" / "a pesquisadora".
8. Rode o que escrever. Depois de mudar um script que gera saída, rode de novo e confira a saída.
9. Se algo der errado, não esconda: registre em `RELATORIO.md` o que tentou, o erro e o que fez.
10. Tempo: busque terminar em ~60–90 min de trabalho. Prefira entregar uma parte bem feita e conferida a tudo pela metade.

## Entregas de cada frente
- `RELATORIO.md`: o que foi feito, resultados com números (e de onde saíram), o que **não** foi possível e por quê, limites, e uma seção final **"Onde a IA generativa ajudou e onde não ajuda"**.
- `README.md` (para a pessoa) e `CLAUDE.md` + `AGENTS.md` (para a IA dela).
- `codigo/` com scripts que rodam do zero, na ordem descrita no README.
- `REFERENCIAS.md` com as referências conferidas (DOI + uma linha do porquê de cada uma).
