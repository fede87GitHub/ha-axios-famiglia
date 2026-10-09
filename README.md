# Axios Famiglia per Home Assistant

<p align="center">
  <img src="https://raw.githubusercontent.com/fede87GitHub/ha-axios-famiglia/main/custom_components/axios_famiglia/brand/icon@2x.png" alt="Axios Famiglia" width="128">
</p>

Integrazione **non ufficiale** per [Home Assistant](https://www.home-assistant.io/) che legge il registro elettronico **Axios Famiglia** (portale `registrofamiglie.axioscloud.it`) e porta in casa le informazioni della scuola: comunicazioni, assenze, ritardi, compiti e verifiche, annotazioni, note disciplinari e argomenti svolti.

[![Validate](https://github.com/fede87GitHub/ha-axios-famiglia/actions/workflows/validate.yml/badge.svg)](https://github.com/fede87GitHub/ha-axios-famiglia/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Licenza MIT](https://img.shields.io/badge/licenza-MIT-blue.svg)](https://github.com/fede87GitHub/ha-axios-famiglia/blob/main/LICENSE)

> **Avviso.** Questo progetto non è affiliato, approvato né supportato da Axios Italia. Non usa un'API pubblica documentata ma le pagine web del portale: se Axios le modifica, l'integrazione può smettere di funzionare fino a un aggiornamento. Usala a tuo rischio.

![Pannello Axios Famiglia, tema scuro](https://raw.githubusercontent.com/fede87GitHub/ha-axios-famiglia/main/docs/images/home-dark.png)

<sub>Le schermate di questa documentazione usano dati di esempio inventati.</sub>

## Cosa offre

| | |
|---|---|
| **Pannello nella barra laterale** | Una plancia dedicata, con tema chiaro e scuro, in italiano e in inglese, che funziona anche da telefono. |
| **Sensori** | Conteggi e elenchi: comunicazioni (anche non lette), assenze, ritardi, uscite anticipate, percentuale di assenze, compiti, annotazioni, note disciplinari, ultimi argomenti. |
| **Calendari** | Cinque calendari: assenze e uscite, compiti e verifiche, annotazioni e note, comunicazioni, argomenti svolti. |
| **Evento per le notifiche** | Un'entità che scatta a ogni novità, con un messaggio già pronto da inviare su Telegram, sul telefono o dove preferisci. |
| **Più studenti** | Una voce di configurazione per ogni studente, ciascuna con il proprio dispositivo e le proprie opzioni. |
| **Opzioni modificabili** | Intervallo di aggiornamento, giorni di registro, numero di comunicazioni e timeout si cambiano senza rifare il login. |

## Avvio rapido

1. In **HACS** aggiungi come repository personalizzato `https://github.com/fede87GitHub/ha-axios-famiglia`, categoria **Integrazione**, poi scarica e **riavvia Home Assistant**.
2. Vai su **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**, cerca **Axios Famiglia** e inserisci nome dello studente, codice cliente, utente e password del portale.
3. Apri **Axios Famiglia** dalla barra laterale.

Tutti i passaggi, con i dettagli, sono nella [guida all'installazione](https://github.com/fede87GitHub/ha-axios-famiglia/blob/main/docs/installazione.md).

## Documentazione

| Pagina | Contenuto |
|---|---|
| [Installazione](https://github.com/fede87GitHub/ha-axios-famiglia/blob/main/docs/installazione.md) | HACS, installazione manuale, aggiornamento e rimozione |
| [Configurazione e opzioni](https://github.com/fede87GitHub/ha-axios-famiglia/blob/main/docs/configurazione.md) | Aggiungere uno o più studenti e regolare le opzioni |
| [Il pannello](https://github.com/fede87GitHub/ha-axios-famiglia/blob/main/docs/pannello.md) | Come si legge e si usa la plancia, con le schermate |
| [Entità](https://github.com/fede87GitHub/ha-axios-famiglia/blob/main/docs/entita.md) | Sensori, calendari ed evento: nomi, valori e attributi |
| [Notifiche e automazioni](https://github.com/fede87GitHub/ha-axios-famiglia/blob/main/docs/notifiche.md) | Come funziona l'evento, esempi per Telegram e per Node-RED |
| [Risoluzione dei problemi](https://github.com/fede87GitHub/ha-axios-famiglia/blob/main/docs/risoluzione-problemi.md) | Messaggi d'errore, log e come segnalare un problema |

## Limiti noti

- I dati arrivano dall'analisi delle pagine web del portale, quindi dipendono dalla loro struttura.
- Sono lette solo le sezioni **Comunicazioni**, **Assenze** e **Registro di classe**. Voti, pagelle e altre sezioni non sono ancora supportati.
- Del registro di classe sono considerati solo gli ultimi giorni scelti nelle opzioni (14 di default, al massimo 90).
- Ogni voce di configurazione gestisce un solo accesso al portale.
- Il pannello trova le entità dal loro ID standard: se rinomini un'entità, il pannello non la legge più.
- Tema e lingua del pannello sono salvati per dispositivo e non si sincronizzano.

## Privacy e sicurezza

- Le credenziali del portale restano nella configurazione locale di Home Assistant e vengono inviate **solo ad Axios**, per l'accesso.
- Per impostazione predefinita il pannello è visibile a **tutti gli utenti** di Home Assistant. Contiene dati scolastici di un minore: se vuoi limitarlo agli amministratori, leggi [Il pannello](https://github.com/fede87GitHub/ha-axios-famiglia/blob/main/docs/pannello.md).
- Quando apri una segnalazione **non incollare mai** password, cookie, token, catture di rete (HAR) né dati personali dello studente o dei docenti.

## Contribuire

Segnalazioni e pull request sono benvenute: apri una [issue](https://github.com/fede87GitHub/ha-axios-famiglia/issues) indicando la versione dell'integrazione, quella di Home Assistant e le righe rilevanti del log, con i dati personali rimossi.

## Licenza

Distribuito con licenza [MIT](https://github.com/fede87GitHub/ha-axios-famiglia/blob/main/LICENSE).
