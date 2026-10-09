# Notifiche e automazioni

[← Torna al README](../README.md)

L'entità `event.axios_<nome>_news` è un campanello: non contiene un dato da leggere ma segnala che è comparsa una **novità** sul portale. Si usa come innesco (*trigger*) di un'automazione.

## Quando scatta

A ogni aggiornamento l'integrazione confronta le voci lette dal portale con quelle già viste, che sono salvate su disco. Per ogni voce nuova scatta un evento.

| Situazione | Cosa succede |
|---|---|
| Prima installazione | Le voci presenti vengono memorizzate **senza eventi**. |
| Voce nuova sul portale | Scatta un evento entro l'intervallo di aggiornamento. |
| Più novità nello stesso aggiornamento | Scatta un evento per ciascuna, dalla più vecchia alla più recente. |
| Riavvio di Home Assistant | Nessun evento per le voci già viste. Le novità arrivate mentre Home Assistant era spento scattano all'avvio. |
| Voce modificata sul portale (per esempio il testo di un compito) | Conta come nuova e scatta di nuovo. |
| Voce che sparisce e poi ricompare | Non scatta di nuovo. |
| Cambio delle [opzioni](configurazione.md#opzioni) che allarga la finestra | Le voci che entrano nella finestra vengono memorizzate **senza eventi**. |

Gli **argomenti svolti non generano eventi**, perché cambiano ogni giorno.

## Tipi di evento

| `event_type` | Quando scatta | Attributi specifici |
|---|---|---|
| `new_communication` | Nuova comunicazione | `id`, `title`, `author`, `date`, `category` |
| `new_absence_event` | Nuova voce in Assenze (assenza, ritardo, uscita) | `date`, `description`, `counts` |
| `new_homework` | Nuovi compiti | `date`, `text` |
| `new_test` | Nuova verifica | `date`, `text` |
| `new_annotation` | Nuova annotazione | `date`, `text` |
| `new_disciplinary_note` | Nuova nota disciplinare | `date`, `text` |

In tutti i casi sono presenti anche:

- `student`: il nome dello studente;
- `message`: un testo già pronto per la notifica, in italiano o in inglese secondo la lingua di Home Assistant. Per esempio: `Nuova comunicazione: Circolare 12 - Uscita didattica al museo`.

## Lo stato dell'entità

Lo **stato** è la data e l'ora dell'ultimo evento. Finché non ne scatta uno vale `unknown`, ed è normale: dopo la prima installazione non succede nulla fino alla prima novità vera. Dopo il primo evento l'entità ricorda l'ultimo anche dopo i riavvii.

## Esempio: notifica generica

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
         and trigger.from_state.state != 'unavailable'
         and trigger.to_state.state not in ['unknown', 'unavailable'] }}
actions:
  - action: notify.notify
    data:
      title: "Axios {{ trigger.to_state.attributes.student }}"
      message: "{{ trigger.to_state.attributes.message }}"
```

- `mode: queued` serve perché più novità possono arrivare quasi insieme e ognuna deve generare la sua notifica.
- La condizione evita una notifica spuria quando l'entità torna disponibile dopo un riavvio. Lascia invece passare la prima novità in assoluto, perché lì lo stato precedente è `unknown`.
- La sintassi con `triggers:` e `actions:` è quella delle versioni recenti di Home Assistant. Nelle versioni più vecchie al posto di `triggers:` si usa `trigger:` (con `platform: state`).

## Esempio: Telegram

Se hai l'integrazione Telegram bot con entità `notify`, puoi inviare il messaggio con `notify.send_message`. Sostituisci l'entità con la tua:

```yaml
actions:
  - action: notify.send_message
    target:
      entity_id: notify.telegram_bot_<la_tua_entità>
    data:
      message: >
        Axios {{ trigger.to_state.attributes.student }}:
        {{ trigger.to_state.attributes.message }}
```

Se un messaggio non arriva, controlla che non contenga caratteri che Telegram può interpretare come formattazione (per esempio `_`, `*`, il carattere backtick e le parentesi quadre). Nelle descrizioni delle assenze compaiono spesso gli orari tra parentesi quadre, come in `Uscita [12:10]`.

## Esempio: solo alcuni tipi di novità

Aggiungi una condizione sul tipo, per esempio per ricevere avvisi solo per verifiche e note disciplinari:

```yaml
conditions:
  - condition: template
    value_template: >
      {{ trigger.to_state.attributes.event_type in ['new_test', 'new_disciplinary_note'] }}
```

## Esempio: più studenti

Ogni studente ha il suo evento. Puoi creare un'automazione per studente, oppure elencare più entità nello stesso trigger e usare `student` nel titolo:

```yaml
triggers:
  - trigger: state
    entity_id:
      - event.axios_mario_news
      - event.axios_giulia_news
```

## Esempio: Node-RED

Con il nodo **events: state** di Node-RED collegato a Home Assistant puoi costruire la stessa notifica. Lo schema è:

```
[events: state  →  event.axios_<nome>_news]  →  [function]  →  [call service: notify.send_message]
```

Nel nodo *function* conviene scartare gli stati vecchi: dopo un riavvio di Home Assistant l'entità può tornare con l'ultimo valore salvato, e senza filtro riceveresti di nuovo una novità già vista. Una novità vera ha come stato un'ora di pochi secondi fa.

```javascript
// Costruisce il testo della notifica a partire dall'evento Axios Famiglia
const ns = msg.data && msg.data.new_state;
if (!ns) { return null; }
const attrs = ns.attributes || {};

// Scarta gli stati "vecchi": una novità vera ha uno stato di pochi secondi fa
const ts = Date.parse(ns.state);
if (isNaN(ts) || (Date.now() - ts) > 120000) { return null; }
if (!attrs.message) { return null; }

const student = attrs.student ? " " + attrs.student : "";
msg.payload = { data: { message: "Axios" + student + "\n" + attrs.message } };
return msg;
```

Il nodo *call service* usa poi `notify.send_message` con le tue entità `notify` come destinazione e legge il testo da `msg.payload.data`. Nel nodo dello stato, abilita l'uscita dei dati dell'evento in `msg.data`.
