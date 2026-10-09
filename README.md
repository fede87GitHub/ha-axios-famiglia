# Axios Famiglia per Home Assistant

<p align="center">
  <img src="custom_components/axios_famiglia/brand/icon@2x.png" alt="Axios Famiglia" width="128">
</p>

Integrazione **non ufficiale** per [Home Assistant](https://www.home-assistant.io/) che legge i dati del registro elettronico **Axios Famiglia** (portale `registrofamiglie.axioscloud.it`) e li espone come sensori, calendari ed eventi per le notifiche: comunicazioni, assenze, ritardi, compiti e verifiche, annotazioni, note disciplinari e argomenti svolti.

[![Validate](https://github.com/fede87GitHub/ha-axios-famiglia/actions/workflows/validate.yml/badge.svg)](https://github.com/fede87GitHub/ha-axios-famiglia/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

> **Avviso.** Questo progetto non è affiliato, approvato né supportato da Axios Italia. Usa le pagine web del portale e non un'API pubblica documentata: se Axios cambia il portale, l'integrazione può smettere di funzionare fino a un aggiornamento. Usala a tuo rischio.

## Funzionalità

- Accesso con le stesse credenziali del portale famiglie.
- Una voce di configurazione **per ogni studente**, ciascuna con il proprio dispositivo e le proprie entità.
- Aggiornamento automatico, di default ogni **30 minuti**.
- **Opzioni modificabili** in qualsiasi momento, senza rifare il login (intervallo, giorni di registro, comunicazioni, timeout).
- **Sensori** con i conteggi e gli elenchi principali.
- **Cinque calendari** separati: assenze e uscite, compiti e verifiche, annotazioni e note, comunicazioni, argomenti svolti.
- **Entità evento** che scatta a ogni novità, pronta per le notifiche.
- Interfaccia e nomi delle entità in **italiano** e **inglese**.

## Entità

Per ogni studente vengono create queste entità. Il prefisso è `<dominio>.axios_<nome_studente>_`.

### Sensori

| Entità (suffisso) | Valore | Attributi principali |
|---|---|---|
| `communications` | Totale comunicazioni | `non_lette`, `ultima`, `elenco` (le ultime N, vedi Opzioni) |
| `communications_unread` | Comunicazioni non lette | – |
| `absences` | Assenze totali | `ultimo_evento`, `eventi` |
| `late_entries` | Ritardi totali | – |
| `early_exits` | Uscite anticipate totali | – |
| `absence_percentage` | Percentuale assenze (%) | – |
| `homework` | Giorni con compiti o verifiche | `giorni_considerati`, `elenco` |
| `annotations` | Giorni con annotazioni | `elenco` |
| `disciplinary_notes` | Giorni con note disciplinari | `elenco` |
| `last_topics` | Data dell'ultimo giorno con argomenti | `argomenti`, `data_iso` |
| `last_update` | Data e ora dell'ultimo aggiornamento | – |

Compiti, annotazioni, note disciplinari e argomenti si riferiscono agli **ultimi giorni** del registro di classe (14 di default, vedi Opzioni), non a tutto l'anno scolastico.

Gli elenchi dei sensori non contengono gli argomenti svolti, perché sono testi lunghi e farebbero superare il limite di dimensione degli attributi salvati da Home Assistant. Gli argomenti si leggono nel calendario **Argomenti** e nel sensore **Ultimi argomenti**.

`last_topics` mostra l'ultimo giorno del registro che ha argomenti, che non coincide necessariamente con oggi (nei weekend e nei giorni festivi non ce ne sono). Lo stato è la data come la scrive il portale, mentre gli argomenti sono nell'attributo `argomenti`.

### Calendari

Le voci compaiono come eventi di un'intera giornata.

| Entità | Contenuto | Giorno dell'evento |
|---|---|---|
| `calendar.axios_<nome>_absences` | Assenze, ritardi e uscite anticipate | data della voce in Assenze |
| `calendar.axios_<nome>_homework` | Compiti e verifiche | giorno della riga di registro |
| `calendar.axios_<nome>_annotations` | Annotazioni e note disciplinari | giorno della riga di registro |
| `calendar.axios_<nome>_communications` | Comunicazioni (le ultime N) | data di pubblicazione |
| `calendar.axios_<nome>_topics` | Argomenti svolti (ultimi giorni di registro) | giorno della riga di registro |

Nel calendario **Argomenti** il titolo mostra l'inizio del testo e la descrizione dell'evento contiene tutti gli argomenti del giorno. I giorni senza argomenti non hanno eventi.

I compiti compaiono nel giorno della riga di registro in cui sono inseriti, non nella data di scadenza.

### Evento per le notifiche

`event.axios_<nome_studente>_news` scatta quando compare una novità. Tipi di evento:

| `event_type` | Quando scatta |
|---|---|
| `new_communication` | Nuova comunicazione |
| `new_absence_event` | Nuova voce in Assenze (assenza, ritardo, uscita) |
| `new_homework` | Nuovi compiti |
| `new_test` | Nuova verifica |
| `new_annotation` | Nuova annotazione |
| `new_disciplinary_note` | Nuova nota disciplinare |

Gli argomenti svolti **non** generano eventi, perché cambiano ogni giorno.

Gli attributi dell'evento includono `student`, `date`, i dettagli della voce (`title`, `author`, `description`, `text`, a seconda del tipo) e `message`, un testo già pronto per la notifica, in italiano o inglese secondo la lingua di Home Assistant.

Dettagli sul funzionamento:

- L'entità mostra **`unknown` finché non scatta il primo evento**: è normale. Dopo il primo evento ricorda l'ultimo anche dopo i riavvii.
- Alla **prima installazione** le voci già presenti vengono memorizzate **senza notifiche**, per non ricevere decine di avvisi insieme.
- Le voci già viste sono salvate su disco: dopo un riavvio di Home Assistant vengono notificate solo le novità vere.
- Se una voce viene modificata sul portale (ad esempio il testo di un compito), viene notificata come nuova.

Esempio di automazione:

```yaml
alias: Axios - notifica novità
description: ""
mode: queued
triggers:
  - trigger: state
    entity_id: event.axios_mario_news
conditions:
  - condition: template
    value_template: >
      {{ trigger.from_state is not none
         and trigger.from_state.state not in ['unknown', 'unavailable']
         and trigger.to_state.state not in ['unknown', 'unavailable'] }}
actions:
  - action: notify.notify
    data:
      title: "Axios {{ trigger.to_state.attributes.student }}"
      message: "{{ trigger.to_state.attributes.message }}"
```

Per filtrare un solo tipo di novità aggiungi una condizione, ad esempio `{{ trigger.to_state.attributes.event_type == 'new_test' }}`.

## Installazione

### Con HACS (consigliato)

1. In Home Assistant apri **HACS**.
2. Menu **⋮** in alto a destra → **Repository personalizzati**.
3. Inserisci `https://github.com/fede87GitHub/ha-axios-famiglia` e scegli la categoria **Integrazione**.
4. Cerca **Axios Famiglia**, scaricala e **riavvia Home Assistant**.

### Manuale

1. Scarica l'ultima release da [GitHub](https://github.com/fede87GitHub/ha-axios-famiglia/releases).
2. Copia la cartella `custom_components/axios_famiglia` nella cartella `custom_components` della tua configurazione di Home Assistant.
3. Riavvia Home Assistant.

## Configurazione

1. Vai su **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**.
2. Cerca **Axios Famiglia**.
3. Inserisci:
   - **Nome dello studente**: viene usato per il nome del dispositivo e come prefisso delle entità.
   - **Codice fiscale della scuola/cliente (CF)**: il codice che inserisci nel campo cliente del portale famiglie.
   - **Nome utente** e **Password** del portale.
4. Per aggiungere un altro studente ripeti la procedura con le sue credenziali.

Le credenziali vengono salvate nella configurazione locale di Home Assistant e inviate solo ad Axios per l'accesso al portale.

## Opzioni

Le opzioni si cambiano quando vuoi, senza rifare il login: **Impostazioni → Dispositivi e servizi → Axios Famiglia**, poi **Configura** sulla voce dello studente. Ogni studente ha le proprie opzioni. Quando salvi, l'integrazione si ricarica da sola.

| Opzione | Predefinito | Valori | Cosa fa |
|---|---|---|---|
| Intervallo di aggiornamento | 30 minuti | da 5 a 1440 | Ogni quanto viene interrogato il portale. Il minimo è 5 minuti per non sovraccaricarlo. |
| Giorni di registro da leggere | 14 | da 1 a 90 | Finestra usata per compiti, verifiche, annotazioni, note disciplinari e argomenti. |
| Comunicazioni da mostrare | 20 | da 1 a 50 | Quante tra le ultime comunicazioni compaiono nell'elenco del sensore, nel calendario e nell'evento novità. Il contatore delle comunicazioni e quello delle non lette considerano sempre tutte. |
| Timeout delle richieste | 30 secondi | da 10 a 120 | Attesa massima per ogni richiesta al portale. Aumentalo se la tua connessione è lenta. |

Il limite di 50 comunicazioni esiste perché l'elenco è un attributo del sensore: Home Assistant non salva nello storico attributi più grandi di circa 16 KB.

Se **aumenti** i giorni di registro o il numero di comunicazioni, le voci più vecchie che entrano nella finestra vengono memorizzate **senza notifiche**, perché non sono novità. Per lo stesso motivo, una voce davvero nuova comparsa nel momento esatto del salvataggio può non essere notificata.

## Risoluzione dei problemi

| Messaggio | Significato |
|---|---|
| *Credenziali non valide* | Il portale ha rifiutato utente, password o codice cliente. |
| *Impossibile connettersi ad Axios* | Errore di rete o risposta inattesa del portale. |
| *Accesso riuscito ma un passaggio di inizializzazione è fallito* | Il login funziona ma una chiamata iniziale del portale ha dato errore. Controlla i log. |
| *Token di sicurezza non trovato* | Il portale potrebbe aver cambiato struttura. Apri una issue. |

Per abilitare i log di debug aggiungi a `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.axios_famiglia: debug
```

Quando apri una issue **non incollare mai** password, cookie, token o catture di rete (HAR) senza averli prima rimossi.

## Limiti noti

- I dati arrivano dall'analisi delle pagine web, quindi dipendono dalla loro struttura.
- Sono lette solo le sezioni Comunicazioni, Assenze e Registro di classe.
- Ogni voce di configurazione gestisce un solo accesso al portale.
- Del registro di classe sono considerati solo gli ultimi giorni scelti nelle opzioni (al massimo 90).

## Contribuire

Issue e pull request sono benvenute. Per segnalare un problema indica la versione dell'integrazione, la versione di Home Assistant e le righe rilevanti del log, con i dati personali rimossi.

## Licenza

Distribuito con licenza [MIT](LICENSE).
