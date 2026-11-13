# VORTHYX

**Dal codice nativo di Nuitka a Python leggibile. Un progetto aperto, di DimaReverse.**

VORTHYX continua il lavoro di [HEXPYRION](https://github.com/DimaReverse/hexpyrion) e [REVENANT](https://github.com/DimaReverse/nuitka-revenant). Integra il motore NDX, il recupero statico di metadati e sorgenti, l'esportazione del bytecode incorporato e l'estrazione onefile per i formati riconosciuti.

È una versione di ricerca: il recupero può essere parziale e un file Python sintatticamente valido non dimostra l'equivalenza con l'originale. Consulta i report e le [limitazioni](LIMITATIONS.md).

## Avvio rapido

Clona la repository, crea e attiva un ambiente virtuale Python 3.11, quindi esegui:

```sh
python -m pip install -r requirements.txt
python nuitka_decompiler.py --ndx --help
python nuitka_decompiler.py --ndx ./your_app.exe -o ./recovered --dev-only
```

Usa il programma soltanto su software tuo o che sei autorizzato ad analizzare. I percorsi statici non avviano il target; le modalità runtime presenti nel codice sono separate ed esplicite. Per input sconosciuti usa un ambiente isolato.

## Un grazie personale

Grazie a tutte le persone che si sono interessate alla mia storia, mi hanno scritto e mi hanno fatto sentire il loro sostegno. Questa parte conta per me quanto il lavoro tecnico.

Grazie a chi ha proposto una funzione, segnalato un bug, provato un fix, aperto una issue o creato un fork. Anche un dettaglio apparentemente piccolo può diventare la chiave per migliorare il progetto. VORTHYX porta avanti anche il vostro incoraggiamento.

I fork e i contributi sono benvenuti. Per aggiungere un riconoscimento preciso, proponi una modifica ad [ACKNOWLEDGMENTS.md](../ACKNOWLEDGMENTS.md) con un collegamento pubblico al contributo. Voglio dare credito in modo corretto, senza dimenticare il lavoro altrui o attribuirlo a persone sbagliate.

— **DimaReverse**

Leggi il [README principale](../README.md), la [guida d'uso](USAGE.md) e le [istruzioni per contribuire](../CONTRIBUTING.md). Licenza [MIT](../LICENSE).
