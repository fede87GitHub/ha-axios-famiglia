# Configurazione e opzioni

[← Torna al README](../README.md)

## Aggiungere uno studente

1. Vai su **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**.
2. Cerca **Axios Famiglia**.
3. Compila i quattro campi:

| Campo | Cosa inserire |
|---|---|
| **Nome dello studente** | Il nome che vuoi vedere in Home Assistant. Diventa il nome del dispositivo e il prefisso delle entità (per esempio `sensor.axios_mario_absences`). Scegli un nome semplice: lo ritroverai in tutte le automazioni. |
| **Codice fiscale della scuola/cliente (CF)** | Il codice che inserisci nel campo "cliente" quando accedi al portale famiglie. |
| **Nome utente** | Il nome utente del portale. |
| **Password** | La password del portale. |

4. Conferma. L'integrazione prova ad accedere al portale: se qualcosa non va, vedi gli errori in [Risoluzione dei problemi](risoluzione-problemi.md).

Alla prima lettura le voci già presenti sul portale (comunicazioni, compiti, ecc.) vengono memorizzate **senza generare notifiche**, per non riceverne decine tutte insieme.

## Più studenti

Ripeti la procedura per ogni studente, con le sue credenziali. Ogni studente ha:

- il proprio dispositivo (`Axios <nome>`);
- le proprie entità, con prefisso `axios_<nome>_`;
- le proprie opzioni;
- una scheda nel selettore in alto del [pannello](pannello.md).

Due voci con lo stesso codice cliente e lo stesso nome utente vengono rifiutate con "Account già configurato". Se due figli usano lo stesso accesso al portale, questa versione non gestisce la scelta dello studente: l'integrazione legge i dati dell'accesso così come li mostra il portale.

## Opzioni

Le opzioni si cambiano quando vuoi, **senza rifare il login**:

1. Vai su **Impostazioni → Dispositivi e servizi → Axios Famiglia**.
2. Sulla voce dello studente clicca **Configura**.
3. Modifica i valori e salva. L'integrazione si ricarica da sola.

| Opzione | Predefinito | Valori | Cosa fa |
|---|---|---|---|
| **Intervallo di aggiornamento** | 30 minuti | da 5 a 1440 | Ogni quanto viene interrogato il portale. Il minimo è 5 minuti, per non sovraccaricarlo. |
| **Giorni di registro da leggere** | 14 | da 1 a 90 | Finestra di giorni del registro di classe usata per compiti, verifiche, annotazioni, note disciplinari e argomenti. |
| **Comunicazioni da mostrare** | 20 | da 1 a 50 | Quante tra le ultime comunicazioni compaiono nell'elenco del sensore, nel calendario e nell'evento delle novità. I contatori delle comunicazioni e delle non lette considerano sempre tutte quelle del portale. |
| **Timeout delle richieste** | 30 secondi | da 10 a 120 | Attesa massima per ogni richiesta al portale. Aumentalo se la tua connessione è lenta. |

Il limite di 50 comunicazioni esiste perché l'elenco è un attributo del sensore, e Home Assistant non salva nello storico attributi più grandi di circa 16 KB.

### Cosa succede alle notifiche quando cambi le opzioni

Se **aumenti** i giorni di registro o il numero di comunicazioni, le voci più vecchie che entrano nella finestra non sono novità. L'integrazione le memorizza **senza notificarle**, quindi non riceverai una raffica di messaggi.

Il rovescio è che una voce davvero nuova comparsa nel momento esatto in cui salvi le opzioni può non essere notificata.

## Credenziali e password

- Le credenziali sono salvate nella configurazione locale di Home Assistant.
- Questa versione non ha una procedura per aggiornare la password. Se la cambi sul portale, elimina la voce dello studente e aggiungila di nuovo, usando lo stesso nome studente.

## Ogni quanto si aggiorna

L'intervallo predefinito è di 30 minuti. Il sensore **Ultimo aggiornamento** (`last_update`) mostra l'ora dell'ultima lettura riuscita, e il pallino in alto nel [pannello](pannello.md) diventa arancione se i dati sono fermi da più di 6 ore.
