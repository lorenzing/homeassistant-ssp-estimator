# Changelog

## 0.3.0 — prerelease

- Valorizzazione automatica delle ore registrate con prezzi GME dello stesso periodo.
- Cache locale dei prezzi storici e copertura temporale esplicita negli attributi.
- OE, CEI, quota energia ed eccedenza disponibili anche senza CUSf.
- In manuale, disponibilità indipendente degli importi secondo i parametri richiesti.
- Selezione fra modalità automatica e manuale, con fonte CUSf separata.
- Nessuna sostituzione delle ore mancanti con zeri o prezzi attuali.

## 0.2.1 — prerelease

- Installazione e aggiornamenti documentati tramite Marketplace di Home Assistant.
- Stati della stima tradotti in italiano e inglese.
- Esempio di dashboard collegata alle entità dell'integrazione, senza aiutanti economici legacy.
- Indicazioni per il confronto con un prospetto GSE e per la corretta gestione delle unità.

## 0.2.0 — prerelease

- Prezzi PUN e zonali reali GME del quarto d'ora corrente e medie giornaliere.
- Download automatico orario con date di validità e gestione dei cambi d'ora.
- Menu province con 110 territori e assegnazione automatica della zona di mercato.
- Correzione del modulo iniziale: prezzi con precisione libera compatibili con i selettori Home Assistant.
- Verifica CI del modulo con i selettori reali di Home Assistant 2026.11.2.

- Controlli condivisi fra configurazione iniziale e aggiornamento dei sensori.
- Rifiuto di contatori in pausa, con fasce o consumo netto e periodi non validi.
- Verifica dei fusi orari, degli inizi futuri e dell'ora esatta del reset annuale.
- Copertura parziale riconosciuta anche per reset pochi secondi dopo Capodanno.
- Anni non validi gestiti senza interrompere l'aggiornamento dei sensori.
- Messaggi di errore della configurazione in italiano e inglese.

## 0.1.0 — prerelease in preparazione

- Configurazione e modifica delle ipotesi dall'interfaccia di Home Assistant.
- Stima del contributo SSP e dell'eccedenza economica da contatori annuali.
- Verifica di unità, anno, allineamento dei periodi e disponibilità dei parametri.
- Nessun dato dell'impianto o collegamento al conto GSE incluso.
