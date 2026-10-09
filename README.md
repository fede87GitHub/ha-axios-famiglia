# Axios Famiglia per Home Assistant

<p align="center">
  <img src="custom_components/axios_famiglia/brand/icon@2x.png" alt="Axios Famiglia" width="128">
</p>

Integrazione **non ufficiale** per [Home Assistant](https://www.home-assistant.io/) che legge i dati del registro elettronico **Axios Famiglia** (portale `registrofamiglie.axioscloud.it`) e li espone come sensori, calendari ed eventi per le notifiche: comunicazioni, assenze, ritardi, compiti e verifiche, annotazioni e note disciplinari.

[![Validate](https://github.com/fede87GitHub/ha-axios-famiglia/actions/workflows/validate.yml/badge.svg)](https://github.com/fede87GitHub/ha-axios-famiglia/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

> **Avviso.** Questo progetto non è affiliato, approvato né supportato da Axios Italia. Usa le pagine web del portale e non un'API pubblica documentata: se Axios cambia il portale, l'integrazione può smettere di funzionare fino a un aggiornamento. Usala a tuo rischio.

## Funzionalità

- Accesso con le stesse credenziali del portale famiglie.
- Una voce di configurazione **per ogni studente**, ciascuna con il proprio dispositivo e le proprie entità.
- Aggiornamento automatico ogni **30 minuti**.
- **Sensori** con i conteggi e gli elenchi principali.
- **Quattro calendari** separati: assenze e uscite, compiti e verifiche, annotazioni e note, comunicazioni.
- **Entità evento** che scatta a ogni novità, pronta per le notifiche.
- Interfaccia e nomi delle entità in **italiano** e **inglese**.

## Entità

Per ogni studente vengono create queste entità. Il prefisso è `<dominio>.axios_<nome_studente>_`.

### Sensori

| Entità (suffisso) | Valore | Attributi principali |
|---|---|---|
| `communications` | Totale comunicazioni | `non_lette`, `ultima`, `elenco` (ultime 20) |
| `communications_unread` | Comunicazioni non lette | – |
| `absences` | Assenze totali | `ultimo_evento`, `eventi` |
| `late_entries` | Ritardi totali | – |
| `early_exits` | Uscite anticipate totali | – |
| `absence_percentage` | Percentuale assenze (%) | – |
| `homework` | Giorni con compiti o verifiche | `giorni_considerati`, `elenco` |
| `annotations` | Giorni con annotazioni | `elenco` |
| `disciplinary_notes` | Giorni con note disciplinari | `elenco` |
| `last_update` | Data e ora dell'ultimo aggiornamento | – |

Compiti, annotazioni e note disciplinari si riferiscono agli **ultimi 14 giorni** del registro di classe, non a tutto l'anno scolastico.

### Calendari

Le voci compaiono come eventi di un'intera giornata.

| Entità | Contenuto | Giorno dell'evento |
|---|---|---|
| `calendar.axios_<nome>_absences` | Assenze, ritardi e uscite anticipate | data della voce in Assenze |
| `calendar.axios_<nome>_homework` | Compiti e verifiche | giorno della riga di registro |
| `calendar.axios_<nome>_annotations` | Annotazioni e note disciplinari | giorno della riga di registro |
| `calendar.axios_<nome>_communications` | Comunicazioni (ultime 20) | data di pubblicazione |

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
triggers:
  - trigger: state
    entity_id: event.axios_mario_news
actions:
  - action: notify.notify
    data:
      title: "Axios {{ trigger.to_state.attributes.student }}"
      message: "{{ trigger.to_state.attributes.message }}"
mode: queued
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

## Contribuire

Issue e pull request sono benvenute. Per segnalare un problema indica la versione dell'integrazione, la versione di Home Assistant e le righe rilevanti del log, con i dati personali rimossi.

## Licenza

Distribuito con licenza [MIT](LICENSE).
