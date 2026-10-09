# Axios Famiglia per Home Assistant

<p align="center">
  <img src="custom_components/axios_famiglia/brand/icon@2x.png" alt="Axios Famiglia" width="128">
</p>

Integrazione **non ufficiale** per [Home Assistant](https://www.home-assistant.io/) che legge i dati del registro elettronico **Axios Famiglia** (portale `registrofamiglie.axioscloud.it`) e li espone come sensori: comunicazioni, assenze, ritardi, compiti e verifiche, annotazioni e note disciplinari.

[![Validate](https://github.com/fede87GitHub/ha-axios-famiglia/actions/workflows/validate.yml/badge.svg)](https://github.com/fede87GitHub/ha-axios-famiglia/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

> **Avviso.** Questo progetto non è affiliato, approvato né supportato da Axios Italia. Usa le pagine web del portale e non un'API pubblica documentata: se Axios cambia il portale, l'integrazione può smettere di funzionare fino a un aggiornamento. Usala a tuo rischio.

## Funzionalità

- Accesso con le stesse credenziali del portale famiglie.
- Una voce di configurazione **per ogni studente**, ciascuna con il proprio dispositivo e le proprie entità.
- Aggiornamento automatico ogni **30 minuti**.
- Interfaccia e nomi delle entità in **italiano** e **inglese**.

## Sensori

Per ogni studente vengono create queste entità. Il prefisso è `sensor.axios_<nome_studente>_`.

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

Esempio: per uno studente chiamato "Mario" ottieni `sensor.axios_mario_communications_unread`, `sensor.axios_mario_absences`, `sensor.axios_mario_homework` e così via.

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
