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
| **Lo studente scelto non è stato trovato sul portale** | Il nome scelto non è più nell'elenco dell'accesso. Riprova dall'inizio; se succede a una voce già creata, vedi sotto. |
| **Il portale non ha confermato il cambio di studente** | L'integrazione ha chiesto il cambio di studente ma il portale non lo ha confermato. Attiva i [log di debug](#log-di-debug) e apri una segnalazione. |
| **Esiste già uno studente con questo nome** | Scegli un nome diverso: il nome dello studente è il prefisso delle entità e deve essere unico. |
| **Tutti gli studenti di questo accesso sono già configurati** | Non c'è nessun altro studente da aggiungere con questo accesso. |

## Il pannello non compare nella barra laterale

1. Controlla che nella cartella `custom_components/axios_famiglia/` ci sia la sottocartella `frontend/` con il file `axios-panel.js`.
2. Riavvia Home Assistant e ricarica la pagina senza cache (Ctrl+F5).
3. Cerca nei log la frase `could not register the sidebar panel`: se compare, il pannello non si è registrato ma sensori e calendari funzionano comunque. Allega l'errore a una segnalazione.

## Il pannello è vuoto o mostra "–"

- Controlla in **Strumenti per sviluppatori → Stati** che le entità `sensor.axios_<nome>_*` esistano e non siano `unavailable`.
- Il pannello costruisce i nomi dal prefisso `axios_<nome>_`. Se hai rinominato a mano un'entità, il pannello non la trova più.
- Se il pallino in alto è rosso, almeno una delle entità principali non è disponibile: vedi la sezione successiva.

## Gli allegati non si aprono

| Sintomo | Cosa controllare |
|---|---|
| Compare "Questa comunicazione non ha allegati" ma l'allegato c'è | Apri la stessa comunicazione dal portale. Se l'allegato è un link nel testo e non un file allegato, il pannello non lo vede. Apri una segnalazione. |
| Compare "Impossibile aprire l'allegato" | Attiva i [log di debug](#log-di-debug) e cerca `could not prepare the attachment`: indica quale delle chiamate al portale ha dato errore. |
| Si apre una scheda vuota che subito si chiude | La comunicazione non ha allegati o il portale non ha risposto. Compare comunque un avviso. |
| Il PDF si scarica invece di aprirsi | Vedi [Il PDF si scarica invece di aprirsi](pannello.md#il-pdf-si-scarica-invece-di-aprirsi). |
| Non succede nulla toccando una comunicazione | Ricarica la pagina senza cache (Ctrl+F5). Le comunicazioni senza un identificativo numerico non sono cliccabili. |
| Nell'app per telefono non si apre la scheda | Alcune app non permettono nuove finestre: compare l'avviso con il link, da toccare per aprire il PDF nel browser del telefono. |

## La comunicazione resta "non letta" dopo averla segnata come letta o dopo aver aperto l'allegato

1. Se hai usato il pulsante con il segno di spunta, verifica che il pannello mostri la conferma **Comunicazione segnata come letta**. Il pulsante non apre né scarica l'allegato.
2. Se hai aperto un allegato, apri le impostazioni del pannello e controlla che **Segna come letta all'apertura** sia acceso. È una scelta per dispositivo: se l'hai spenta su quel telefono o browser, l'apertura non registra la lettura.
3. Se la voce è grigia ("Non disponibile…"), la registrazione è disattivata per tutti in `api.py` (`MARK_AS_READ = False`).
4. L'allegato può aprirsi anche quando la registrazione della lettura non riesce. Controlla nei log:

| Riga | Cosa dice |
|---|---|
| `the communication could not be marked as read (...)` | Il portale ha rifiutato la registrazione della lettura. Il motivo è tra parentesi. L'allegato si è aperto comunque. |
| `the page has no post reference, the communication is not marked as read` | (solo con i log di debug) La pagina della comunicazione non conteneva il riferimento necessario alla registrazione. |
| `the communication was marked as read` | (solo con i log di debug) Il portale ha confermato la lettura. |

Se la lettura risulta registrata sul portale ma il pannello mostra ancora "non letta", ricarica il pannello e controlla che sia in uso la versione aggiornata di `axios-panel.js`. Dopo la conferma del portale, il pannello aggiorna subito lo stato locale; il coordinator richiede inoltre un aggiornamento per riallineare le entità Home Assistant. Se il portale continua a restituire temporaneamente il vecchio stato, il riallineamento definitivo avviene al successivo aggiornamento riuscito.

Con i log di debug attivi trovi anche:

| Riga | Cosa dice |
|---|---|
| `Axios communication N: no attachments found in the page` | Il portale ha risposto, ma nella pagina non c'è nessun pulsante di allegato. |
| `Axios attachment: temporary link obtained (host ...)` | Il portale ha consegnato il link. Il link completo non viene mai scritto nei log. |

Quando apri una segnalazione sugli allegati **non incollare** link, nomi dei file, codice cliente né il contenuto delle risposte del portale senza averli prima sostituiti con segnaposto.

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
- **Nessuna notifica per un argomento già presente:** alla prima lettura e quando cambia la finestra del registro, gli argomenti già presenti vengono memorizzati senza notifiche retroattive.

## Dopo un aggiornamento qualcosa non torna

- Riavvia Home Assistant: il solo ricaricamento non rilegge i file Python modificati.
- Ricarica la pagina del browser senza cache (Ctrl+F5).
- Con HACS, se la pagina del repository mostra una descrizione vecchia, usa **⋮ → Aggiorna informazioni**.

## Ho più studenti e vedo i dati di quello sbagliato, o di nessuno

Con un accesso a più studenti, ogni voce deve essere legata a uno studente.

1. Apri **Impostazioni → Dispositivi e servizi → Axios Famiglia** e controlla che ci sia **una voce per ogni studente**, con nomi diversi.
2. Una voce creata prima della versione 1.5.0 non è legata a nessuno studente e legge quello che il portale mostra dopo l'accesso. **Eliminala e riaggiungila**, scegliendo lo studente nel secondo passaggio.
3. Se una voce non si aggiorna, nei log compare uno di questi messaggi:

| Riga | Cosa dice |
|---|---|
| `The student of this entry is not among the N students of the account` | Lo studente a cui la voce è legata non c'è più nell'elenco del portale. Elimina la voce e riaggiungila. |
| `The portal did not confirm the change of student` | Il portale non ha confermato il cambio. |
| `the answer does not allow to confirm it` | Il portale ha risposto al cambio ma in un formato che non permette di verificarlo: l'integrazione prosegue, ma controlla che i dati siano quelli giusti. |
| `the portal did not list the students of the account` | Il portale non ha elencato gli studenti: la voce usa lo studente che il portale mostra. |

Con i log di debug attivi trovi anche `switching to the student in position N of M` e `the wanted student ... is already the active one`. Per riservatezza i log riportano solo la posizione dello studente, mai il suo nome.

## Le voci si disconnettono a vicenda

Ogni voce fa un proprio accesso al portale. Se il portale terminasse la sessione precedente quando se ne apre una nuova per lo stesso utente, le voci si disconnetterebbero a vicenda: nei log di debug vedresti `Axios login: starting fresh login` a ogni aggiornamento, per entrambe. L'integrazione si riprende da sola, ma fa più richieste del necessario. Se lo vedi, apri una segnalazione e indica quante voci hai.

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
