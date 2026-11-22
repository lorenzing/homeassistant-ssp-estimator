# Scambio sul Posto — Stima GSE per Home Assistant

Integrazione configurabile dall'interfaccia, pensata per HACS. Calcola uno
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

Nel setup si sceglie la **provincia dell'impianto** da un menu a tendina con
110 territori provinciali, comprese le nuove province sarde. Ogni voce mostra
la zona corrispondente, per esempio **Ferrara · NORD**, **Firenze · CNOR** e
**Napoli · CSUD**. La zona viene ricavata automaticamente anche modificando
la provincia da Configura. Le configurazioni precedenti conservano la zona;
al primo salvataggio delle opzioni occorre selezionare la provincia.

## Prezzi reali GME

L'integrazione scarica gli archivi pubblici MGP del GME per oggi e domani,
senza account, e crea quattro entità in **EUR/kWh**:

- **PUN puntuale**: prezzo del quarto d'ora corrente.
- **Prezzo zonale puntuale**: prezzo del quarto d'ora per la zona della provincia.
- **PUN medio giornaliero**: media aritmetica dei prezzi del giorno.
- **Prezzo zonale medio giornaliero**: media aritmetica nella zona selezionata.

Il download avviene ogni ora; il prezzo puntuale cambia localmente a ogni
quarto d'ora. Gli attributi espongono fonte, zona, data di mercato, intervallo
di validità e ultimo download. I giorni di cambio dell'ora hanno 92 o 100
quarti d'ora. Mancanze e errori non vengono sostituiti da prezzi inventati o
da quelli del giorno precedente; le medie richiedono il giorno completo.

Questi prezzi **non sostituiscono automaticamente le medie ponderate annuali**:
per calcolare OE e CEI del periodo occorre ponderarli sui rispettivi flussi.
Il CUSf resta un parametro distinto da inserire con fonte e anno coerenti;
non è un prezzo di borsa e non viene ricavato dal PUN. Il calcolo annuale
rimane disponibile con i parametri inseriti anche se il download GME fallisce.

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

## Installazione e aggiornamenti dal Marketplace

Repository: `lorenzing/homeassistant-ssp-estimator`.
Su Home Assistant 2026.11 e successivi HACS è integrato nel **Marketplace**,
raggiungibile da **Impostazioni → Marketplace**. Non installare il vecchio
componente HACS su queste versioni. La repository deve essere pubblica.

1. Nel Marketplace aggiungere `https://github.com/lorenzing/homeassistant-ssp-estimator`
   alle repository personalizzate, categoria **Integration**, e installarla.
   La presenza fra le repository personalizzate non equivale all'inclusione
   nel catalogo pubblico, che richiede una procedura e una revisione separate.
2. In alternativa copiare soltanto `custom_components/ssp_estimator` nella
   cartella `custom_components` dell'installazione Home Assistant.
3. Riavviare Home Assistant. Versione minima: **2026.11.0**.
4. Creare due aiutanti **Utility Meter**, ciclo **annuale**, nessuna fascia,
   da due contatori cumulativi distinti di prelievo e immissione (Wh/kWh/MWh).
   Per contatori di rete cumulativi non periodicamente azzerati, disattivare
   l'opzione "Periodicamente azzerato". Creare entrambi nello stesso momento.
5. Aggiungere l'integrazione **Scambio sul Posto — Stima GSE** e scegliere i due
   nuovi contatori annuali. Non selezionare i totali vita dell'inverter.
6. Scegliere la provincia; impostare anno, medie PUN/prezzo zonale e CUSf, con fonte e periodo
   nel campo riferimento. Lasciare i valori economici non compilati se sconosciuti.
7. Aggiornare le ipotesi da **Configura** nell'integrazione.

Per una precedente installazione manuale della stessa integrazione, installare
la repository dal Marketplace e riavviare, conservando la voce SSP già
configurata. Non rimuoverla e non ricreare i contatori: gli ID univoci e lo
storico dipendono dalla configurazione esistente. Gli aiutanti template di
una vecchia implementazione separata vanno sostituiti nella dashboard con
le entità dell'integrazione; i due contatori annuali restano le fonti.

Le modifiche vengono pubblicate prima su GitHub e verificate dalla CI.
Installare poi l'aggiornamento dal Marketplace o dalla relativa entità
**Update**, riavviare quando richiesto e aggiornare infine la dashboard.
In assenza di release, selezionare il branch `main`: gli aggiornamenti sono
identificati dal commit. Non sovrascrivere manualmente i file gestiti dal Marketplace.

Una vista essenziale è disponibile in [examples/ssp-dashboard.yaml](examples/ssp-dashboard.yaml).
L'esempio presuppone una configurazione chiamata **SSP**; verificare gli ID
reali, specialmente se erano già presenti aiutanti con lo stesso nome.

Gli aiutanti annuali devono esporre `last_reset` nell'anno corrente e `next_reset`
il 1° gennaio successivo. Contatori giornalieri/mensili o periodi disallineati sono
rifiutati. La verifica avviene già nel modulo iniziale e viene ripetuta durante
il funzionamento. Sono rifiutati anche i contatori con fasce o consumo netto,
le date senza fuso orario, gli inizi futuri e i reset diversi dalla mezzanotte
del 1° gennaio. Un contatore in pausa rende indisponibile la stima finché riprende
la raccolta. L'integrazione non aggiunge ID o credenziali ai contatori sorgente.

## Entità

- Energia scambiata nel periodo
- OE e CEI stimati
- Quota energia e quota servizi stimate
- Contributo SSP stimato
- Eccedenza economica stimata
- Stato della stima, con fonte, anno, provincia, zona e copertura nelle proprietà
- Quattro sensori dei prezzi reali GME, indipendenti dalle ipotesi annuali

Tutte le entità hanno ID univoci per configurazione e si aggiornano al cambio dei
contatori. Gli importi non hanno `state_class: total_increasing`: aggiornare una
media rivede l'intero scenario, non genera un nuovo pagamento. Non usarli come
sensori di rimborso cumulativo nel pannello Energia.

## Confrontare un prospetto GSE

Il dettaglio GSE è un consuntivo storico, da tenere separato dalle ipotesi
dell'anno corrente. Prima del confronto controllare anno, periodo e misure:

- Il **CUS** può essere espresso in **cEuro/kWh**: per esempio 7,25 cEuro/kWh
  corrispondono a 0,0725 EUR/kWh.
- Per **OE**, sommare i valori mensili calcolati dalle misure per fascia;
  il nome di una colonna non basta a stabilire l'unità, che va verificata
  anche sulla formula numerica e sull'importo risultante.
- Per **CEI**, il GSE può applicare un coefficiente alle immissioni nette.
  Con contatori netti, la media effettiva per ricostruire CEI è
  `CEI / kWh immessi netti`, comprensiva dell'eventuale coefficiente.
  Applicarlo nuovamente a questa media conterebbe due volte la correzione.
- L'eccedenza del solo anno è `max(CEI − OE, 0)`. Il credito accumulato può
  includere importi di anni precedenti; la sua liquidabilità è distinta.
- Il modello corrente non gestisce il recupero di crediti pregressi quando
  OE supera CEI, né i movimenti di acconto, storno e costo amministrativo.

Non trasferire automaticamente il CUS o le medie di un anno al successivo.
I CSV GSE possono contenere POD e dati personali: non caricarli nella repository.

## Verifiche e sviluppo

```sh
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

I test del calcolo non richiedono Home Assistant. La suite di adattamento dei
sensori usa piccoli sostituti delle API per verificare periodi, disponibilità e
unità. La CI esegue inoltre due prove del modulo di configurazione con i
selettori reali di Home Assistant 2026.11.2 (`tests_ha`), installato su Python
3.14. Queste prove controllano apertura del setup e precisione dei prezzi.

La versione 0.2.0 è stata anche installata e configurata su Home Assistant
2026.11.2: verificati setup e opzioni per provincia, download GME e disponibilità
dei quattro sensori di mercato. Resta prerelease: non è stata completata la
validazione HACS/Hassfest né una verifica annuale con i conguagli GSE.

La repository non deve contenere esportazioni dell'impianto, token, POD,
indirizzi di rete o credenziali. Gli esempi sono sintetici.

## Fonti ufficiali

- [Calcolo SSP — GSE](https://assistenza.clienti.gse.it/csm/it/calcolo-contributo-in-conto-scambio-scambio-sul-posto?id=faq&sys_id=02e6c047db85c81052669532ca961966)
- [Valore dell'energia immessa — GSE](https://assistenza.clienti.gse.it/csm/it/calcolo-valore-in-euro-energia-immessa-in-rete-scambio-sul-posto?id=faq&sys_id=38702e2fdbe888107a27e347489619ec)
- [Regole tecniche GSE](https://www.gse.it/documenti_site/Documenti%20GSE/Servizi%20per%20te/SCAMBIO%20SUL%20POSTO/Regole%20e%20procedure/Regole%20Tecniche%20Scambio%20sul%20Posto_2019.pdf)
- [Requisiti HACS](https://hacs.dev/docs/publish/integration/)
- [Download prezzi MGP — GME](https://gme.mercatoelettrico.org/en-us/Home/Results/Electricity/MGP/Download?valore=Prezzi)
- [Zone di mercato — ARERA](https://www.arera.it/fileadmin/allegati/eventi/230222Autoconsumo.pdf)
- [Province e riordino della Sardegna — ISTAT](https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/)
- [HACS e il Marketplace](https://www.hacs.xyz/docs/marketplace/)

Progetto della comunità, senza affiliazione a GSE, ARERA, GME o Home Assistant.
