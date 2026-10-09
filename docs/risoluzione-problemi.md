# Risoluzione dei problemi

[← Torna al README](../README.md)

## Errori durante la configurazione

| Messaggio | Significato e cosa fare |
|---|---|
| **Credenziali non valide** | Il portale ha rifiutato nome utente, password o codice cliente. Prova ad accedere dal sito del portale con gli stessi dati. |
| **Impossibile connettersi ad Axios** | Errore di rete o risposta inattesa del portale. Riprova più tardi, controlla la connessione di Home Assistant e, se serve, aumenta il timeout nelle [opzioni](configurazione.md#opzioni). |
| **Accesso riuscito ma un passaggio di inizializzazione è fallito** | Il login funziona ma una chiamata iniziale del portale ha dato errore. Attiva i [log di debug](#log-di-debug) e cerca `dashboard init call`. |
| **Token di sicurezza non trovato** | L'accesso è riuscito ma la pagina del portale non contiene il token atteso: il portale potrebbe aver cambiato struttura. Apri una segnalazione. |
| **Inserisci un nome studente valido** | Il nome non contiene lettere o numeri utilizzabili per gli ID delle entità. |
| **Account già configurato** | Esiste già una voce con lo stesso codice cliente e lo stesso nome utente. |

## Il pannello non compare nella barra laterale

1. Controlla che nella cartella `custom_components/axios_famiglia/` ci sia la sottocartella `frontend/` con il file `axios-panel.js`.
2. Riavvia Home Assistant e ricarica la pagina senza cache (Ctrl+F5).
3. Cerca nei log la frase `could not register the sidebar panel`: se compare, il pannello non si è registrato ma sensori e calendari funzionano comunque. Allega l'errore a una segnalazione.

## Il pannello è vuoto o mostra "–"

- Controlla in **Strumenti per sviluppatori → Stati** che le entità `sensor.axios_<nome>_*` esistano e non siano `unavailable`.
- Il pannello costruisce i nomi dal prefisso `axios_<nome>_`. Se hai rinominato a mano un'entità, il pannello non la trova più.
- Se il pallino in alto è rosso, almeno una delle entità principali non è disponibile: vedi la sezione successiva.

## Le entità sono "non disponibili" o i dati non si aggiornano

1. Apri il sensore **Ultimo aggiornamento** (`last_update`): se la data è ferma, le letture non vanno a buon fine.
2. Controlla il portale dal browser: potrebbe essere in manutenzione.
3. Se hai cambiato la password sul portale, elimina la voce dello studente e aggiungila di nuovo.
4. Attiva i [log di debug](#log-di-debug) e cerca le righe `Axios login` e gli eventuali errori.

## L'evento delle novità è `unknown`

È normale. L'entità resta `unknown` finché non scatta il primo evento. Alla prima installazione le voci già presenti vengono memorizzate senza notifiche, quindi per vedere un valore serve una novità vera sul portale. Dettagli in [Notifiche e automazioni](notifiche.md).

## Ho ricevuto o non ho ricevuto una notifica che mi aspettavo

- **Notifica per una voce vecchia dopo aver cambiato le opzioni:** l'integrazione le memorizza senza notificarle. Se è comunque arrivata, segnalalo.
- **Nessuna notifica per una voce appena comparsa:** una voce nuova comparsa nel momento esatto in cui salvi le opzioni può non essere notificata.
- **Notifiche doppie:** controlla di non avere due automazioni che si innescano sullo stesso evento.
- **Nessuna notifica per gli argomenti:** è voluto, gli argomenti non generano eventi.

## Dopo un aggiornamento qualcosa non torna

- Riavvia Home Assistant: il solo ricaricamento non rilegge i file Python modificati.
- Ricarica la pagina del browser senza cache (Ctrl+F5).
- Con HACS, se la pagina del repository mostra una descrizione vecchia, usa **⋮ → Aggiorna informazioni**.

## Log di debug

Aggiungi a `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.axios_famiglia: debug
```

Riavvia, riproduci il problema e apri **Impostazioni → Sistema → Registri**. Cerca `axios_famiglia`.

Righe utili:

| Riga | Cosa dice |
|---|---|
| `Axios register: kept X of Y rows` | Quante righe di registro rientrano nella finestra di giorni scelta. |
| `first run, N items stored without notifications` | Prima lettura: le voci presenti sono state memorizzate senza notifiche. |
| `N new item(s)` | Sono state rilevate novità. |
| `reading window changed ... re-seeding without notifications` | Hai cambiato le opzioni: le voci nuove nella finestra sono state memorizzate senza notifiche. |

## Segnalare un problema

Apri una [issue](https://github.com/fede87GitHub/ha-axios-famiglia/issues) indicando:

- la versione dell'integrazione e quella di Home Assistant;
- cosa ti aspettavi e cosa è successo;
- le righe rilevanti del log di debug.

**Prima di incollare qualsiasi cosa, rimuovi:** password, cookie, token, catture di rete (HAR), codice cliente e qualunque dato personale, come nomi dello studente e dei docenti, scuola e testo delle comunicazioni.
