# Referências

Todos os DOIs foram conferidos em `https://api.crossref.org/works/<doi>` pelo script `codigo/07_referencias.py`; o título devolvido bateu com o esperado nas 9 entradas abaixo (`dados/referencias_conferidas.json`). A conferência é de **metadados**, não de leitura integral: o "por quê" indica onde o trabalho entra no procedimento, não que o artigo tenha sido revisado linha a linha.

Três candidatas foram descartadas na conferência (Seo et al. 2003: DOI não retornou no Crossref; Shamseldin & O'Connor: o DOI consultado devolveu outro artigo; Todini 2008: 404). Ver `RELATORIO.md`, seção 9.

---

1. **Krzysztofowicz, R. (2001).** The case for probabilistic forecasting in hydrology. *Journal of Hydrology*. DOI: [10.1016/S0022-1694(01)00420-6](https://doi.org/10.1016/S0022-1694(01)00420-6)
   *Por quê:* argumenta por que uma previsão pontual não basta e por que se deve tratar a incerteza — é o enquadramento geral de qualquer pós-processamento.

2. **Weerts, A. H.; El Serafy, G. Y. H. (2006).** Particle filtering and ensemble Kalman filtering for state updating with hydrological conceptual rainfall-runoff models. *Water Resources Research*. DOI: [10.1029/2005WR004093](https://doi.org/10.1029/2005WR004093)
   *Por quê:* referência direta para atualização de estado com filtros (EnKF e filtro de partículas); é a base conceitual do método (d) usado aqui.

3. **Liu, Y. et al. (2012).** Advancing data assimilation in operational hydrologic forecasting: progresses, challenges, and emerging opportunities. *Hydrology and Earth System Sciences*. DOI: [10.5194/hess-16-3863-2012](https://doi.org/10.5194/hess-16-3863-2012)
   *Por quê:* revisão de assimilação de dados em previsão operacional; útil para posicionar Kalman/atualização de estado frente a correção de erro.

4. **Bogner, K.; Pappenberger, F. (2011).** Multiscale error analysis, correction, and predictive uncertainty estimation in a flood forecasting system. *Water Resources Research*. DOI: [10.1029/2010WR009137](https://doi.org/10.1029/2010WR009137)
   *Por quê:* mostra como analisar e corrigir erros de previsão de cheia em várias escalas temporais — o problema central deste trabalho.

5. **Montanari, A.; Brath, A. (2004).** A stochastic approach for assessing the uncertainty of rainfall-runoff simulations. *Water Resources Research*. DOI: [10.1029/2003WR002540](https://doi.org/10.1029/2003WR002540)
   *Por quê:* trata a estrutura do erro de simulações hidrológicas (autocorrelação, viés), que é o que os modelos autorregressivos de erro exploram.

6. **Kratzert, F. et al. (2018).** Rainfall–runoff modelling using Long Short-Term Memory (LSTM) networks. *Hydrology and Earth System Sciences*. DOI: [10.5194/hess-22-6005-2018](https://doi.org/10.5194/hess-22-6005-2018)
   *Por quê:* referência de aprendizado de máquina em hidrologia; contexto para o uso de modelos de erro por ML (método e).

7. **Nevo, S. et al. (2022).** Flood forecasting with machine learning models in an operational framework. *Hydrology and Earth System Sciences*. DOI: [10.5194/hess-26-4013-2022](https://doi.org/10.5194/hess-26-4013-2022)
   *Por quê:* descreve um sistema operacional de previsão de cheia com ML; ajuda a separar "modelo de previsão" de "correção de previsão".

8. **Nearing, G. et al. (2024).** Global prediction of extreme floods in ungauged watersheds. *Nature*. DOI: [10.1038/s41586-024-07145-1](https://doi.org/10.1038/s41586-024-07145-1)
   *Por quê:* estado da arte em previsão de cheias com ML em escala global; referência para discutir o que a IA agrega (e o que não agrega) em eventos extremos.

9. **Siqueira, V. A. et al. (2018).** Toward continental hydrologic–hydrodynamic modeling in South America. *Hydrology and Earth System Sciences*. DOI: [10.5194/hess-22-4815-2018](https://doi.org/10.5194/hess-22-4815-2018)
   *Por quê:* contexto de modelagem hidrológica na América do Sul, incluindo a bacia do Araguaia–Tocantins; útil para o modelo do doutorado, não para o método de correção em si.

---

## Fontes de dados (não são artigos)

- **ANA — webservice de telemetria:** `http://telemetriaws1.ana.gov.br/ServiceANA.asmx` (método `DadosHidrometeorologicos`), acesso sem cadastro.
- **Open-Meteo Archive API (ERA5, modelo fixo):** `https://archive-api.open-meteo.com/v1/archive`, acesso sem chave. Usado como substituto aberto do MERGE; o ERA5-Land foi testado e não devolve precipitação nessa API.
- **MERGE/CPTEC:** não baixado nesta frente (ver `RELATORIO.md`, seção 9).
