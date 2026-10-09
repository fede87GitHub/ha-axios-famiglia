# Installazione

[← Torna al README](../README.md)

## Prima di iniziare

Ti servono:

- Home Assistant già in funzione.
- [HACS](https://hacs.xyz), se scegli l'installazione consigliata.
- Le credenziali del **portale famiglie** di Axios: codice cliente (il codice fiscale della scuola/cliente), nome utente e password.

## Con HACS (consigliato)

1. In Home Assistant apri **HACS**.
2. Clicca il menu **⋮** in alto a destra e scegli **Repository personalizzati**.
3. Incolla `https://github.com/fede87GitHub/ha-axios-famiglia`, scegli la categoria **Integrazione** e conferma.
4. Cerca **Axios Famiglia** nell'elenco, aprila e premi **Scarica**.
5. **Riavvia Home Assistant.** Il riavvio completo è necessario: il solo ricaricamento non rilegge i file dell'integrazione.

Poi prosegui con la [configurazione](configurazione.md).

## Installazione manuale

1. Scarica l'ultima release dalla pagina [Releases](https://github.com/fede87GitHub/ha-axios-famiglia/releases).
2. Copia la cartella `custom_components/axios_famiglia` dentro la cartella `custom_components` della tua configurazione di Home Assistant. Se `custom_components` non esiste, creala accanto a `configuration.yaml`.
3. **Riavvia Home Assistant.**

Al termine la struttura deve essere questa:

```
config/
└── custom_components/
    └── axios_famiglia/
        ├── __init__.py
        ├── manifest.json
        ├── frontend/
        │   └── axios-panel.js
        ├── translations/
        │   ├── en.json
        │   └── it.json
        └── ...
```

Se manca la sottocartella `frontend/`, il pannello non compare nella barra laterale.

## Aggiornamento

- **Con HACS:** quando esce una nuova versione, HACS la propone tra gli aggiornamenti. Aggiorna e riavvia Home Assistant.
- **Manuale:** sostituisci la cartella `axios_famiglia` con quella nuova e riavvia.

Dopo un aggiornamento, se il pannello sembra ancora quello vecchio, ricarica la pagina del browser **senza cache** (Ctrl+F5). Il pannello aggiunge al proprio file un numero di versione, quindi di norma basta un normale ricaricamento.

## Rimozione

1. Vai su **Impostazioni → Dispositivi e servizi → Axios Famiglia**.
2. Per ogni studente apri il menu **⋮** e scegli **Elimina**. Quando elimini l'ultimo studente, la voce **Axios Famiglia** sparisce dalla barra laterale.
3. Se hai installato con HACS, rimuovi l'integrazione anche da HACS. Se l'hai copiata a mano, elimina la cartella `custom_components/axios_famiglia`.
4. Riavvia Home Assistant.

Le automazioni che usano entità di Axios Famiglia, come l'evento delle novità, non funzioneranno più: eliminale o modificale.
