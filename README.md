# Scambio sul Posto — Stima GSE per Home Assistant

Integrazione locale configurabile dall'interfaccia, pensata per HACS. Calcola uno
**scenario annuale stimato** del contributo SSP e dell'eccedenza economica. Non
accede al conto GSE e non recupera pagamenti o conguagli ufficiali.

## Cosa calcola

Per il modello domestico semplificato con un CUSf di riferimento:

```text
ES = min(kWh prelevati, kWh immessi)
OE = kWh prelevati × PUN medio ponderato sui prelievi
CEI = kWh immessi × prezzo zonale medio ponderato sulle immissioni
CS stimato = min(OE, CEI) + CUSf × ES
Eccedenza economica stimata = max(CEI − OE, 0)
```

I tre prezzi vanno inseriti in **EUR/kWh**, non EUR/MWh né centesimi/kWh.
PUN e prezzo zonale sono medie ponderate distinte, riferite allo stesso periodo
dei contatori. La tariffa pagata al fornitore, comprensiva di imposte e oneri,
non è il PUN. Il CUSf non è semplicemente la somma delle componenti della bolletta.

La zona, selezionabile, è un'informazione di riferimento: non effettua download
automatici dei prezzi. L'Emilia-Romagna appartiene alla zona NORD.

### Limiti del modello

- Versione iniziale per stime domestiche; non implementa tutti i driver, scaglioni
  e dettagli mensili previsti dalle regole tecniche GSE.
- Il confronto e il minimo sono annuali: non sommare dodici contributi calcolati
  indipendentemente mese per mese.
- Le medie ponderate corrette permettono di ricostruire OE e CEI, ma una media
  aritmetica o un prezzo spot attuale applicato a tutto l'anno resta uno scenario.
- Il risultato esclude costi amministrativi, fiscalità del beneficiario,
  crediti degli anni precedenti e scelta di liquidare le eccedenze.
- L'eccedenza è economica (EUR), non la differenza fra kWh immessi e prelevati.
  Non è una seconda remunerazione da aggiungere due volte a CEI.
- Il GSE usa misure validate dal distributore; i contatori di un inverter possono
  differire. Un periodo iniziato durante l'anno viene segnalato come parziale.
- La prima versione non ricostruisce il passato e non modifica contatori o
  configurazione Energia. Gli importi sono indisponibili senza parametri e fonte.
- I parametri devono essere riconfermati per il nuovo anno. Non c'è scraping
  fiscale o recupero automatico del CUSf, né una tariffa GSE fissa incorporata.

## Installazione

Repository prevista: `lorenzing/homeassistant-ssp-estimator`.
L'inclusione nel catalogo HACS richiede una richiesta e una verifica separate.

1. In HACS aggiungere l'URL della repository come repository personalizzata,
   categoria **Integration**, e scaricarla. Per l'inclusione nel catalogo pubblico
   HACS serve una procedura separata e l'accettazione dei manutentori.
2. In alternativa copiare soltanto `custom_components/ssp_estimator` nella
   cartella `custom_components` dell'installazione Home Assistant.
3. Riavviare Home Assistant. Versione minima: **2026.11.0**.
4. Creare due aiutanti **Utility Meter**, ciclo **annuale**, nessuna fascia,
   da due contatori cumulativi distinti di prelievo e immissione (Wh/kWh/MWh).
   Per contatori di rete cumulativi non periodicamente azzerati, disattivare
   l'opzione "Periodicamente azzerato". Creare entrambi nello stesso momento.
5. Aggiungere l'integrazione **Scambio sul Posto — Stima GSE** e scegliere i due
   nuovi contatori annuali. Non selezionare i totali vita dell'inverter.
6. Impostare anno, zona, medie PUN/prezzo zonale e CUSf, con la fonte e il periodo
   nel campo riferimento. Lasciare i valori economici non compilati se sconosciuti.
7. Aggiornare le ipotesi da **Configura** nell'integrazione.

Gli aiutanti annuali devono esporre `last_reset` nell'anno corrente e `next_reset`
il 1° gennaio successivo. Contatori giornalieri/mensili o periodi disallineati sono
rifiutati. L'integrazione non aggiunge ID o credenziali ai contatori sorgente.

## Entità

- Energia scambiata nel periodo
- OE e CEI stimati
- Quota energia e quota servizi stimate
- Contributo SSP stimato
- Eccedenza economica stimata
- Stato della stima, con fonte, anno, zona e copertura nelle proprietà

Tutte le entità hanno ID univoci per configurazione e si aggiornano al cambio dei
contatori. Gli importi non hanno `state_class: total_increasing`: aggiornare una
media rivede l'intero scenario, non genera un nuovo pagamento. Non usarli come
sensori di rimborso cumulativo nel pannello Energia.

## Verifiche e sviluppo

```sh
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

I test del calcolo non richiedono Home Assistant. La suite di adattamento dei
sensori usa piccoli sostituti delle API per verificare periodi, disponibilità e
unità; non sostituisce una prova completa dentro Home Assistant. La pubblicazione
iniziale resta prerelease fino alla verifica reale dell'integrazione installata.

La repository non deve contenere esportazioni dell'impianto, token, POD,
indirizzi di rete o credenziali. Gli esempi sono sintetici.

## Fonti ufficiali

- [Calcolo SSP — GSE](https://assistenza.clienti.gse.it/csm/it/calcolo-contributo-in-conto-scambio-scambio-sul-posto?id=faq&sys_id=02e6c047db85c81052669532ca961966)
- [Valore dell'energia immessa — GSE](https://assistenza.clienti.gse.it/csm/it/calcolo-valore-in-euro-energia-immessa-in-rete-scambio-sul-posto?id=faq&sys_id=38702e2fdbe888107a27e347489619ec)
- [Regole tecniche GSE](https://www.gse.it/documenti_site/Documenti%20GSE/Servizi%20per%20te/SCAMBIO%20SUL%20POSTO/Regole%20e%20procedure/Regole%20Tecniche%20Scambio%20sul%20Posto_2019.pdf)
- [Requisiti HACS](https://hacs.dev/docs/publish/integration/)

Progetto della comunità, senza affiliazione a GSE, ARERA, GME o Home Assistant.
