# Specifica comportamentale

Specifica corrente con versione nominale **0.8.3** e menu sociali **Unreleased**. Il tag e l'allegato v0.8.3 conservano il pacchetto pubblicato, senza le modifiche successive; anche la release storica 0.8.2 conserva il contenuto pubblicato.

`ruang_irama.en-US.source` è l'input del compilatore globale, equivalente al
riferimento `tests/fixtures/semantic_reference.txt`. I contratti e i test
comportamentali si applicano a questi input.

La grammatica nativa del Workshop, gli identificatori, i nomi delle regole,
i commenti e tutti i testi personalizzati dell'interfaccia sono in inglese.
Non esistono un selettore della lingua o cataloghi tradotti. I nomi propri,
compreso il profilo `งูแรร์`, conservano i caratteri originali.

Le regole per-player nella specifica vengono trasformate in controller atomici,
timer e registrazioni di eventi eseguiti dallo scheduler globale. Non copiare
questa specifica nel gioco: usa [il clipboard generato](../workshop/ruang_irama.en-US.workshop).

La specifica conserva identificatori di regola stabili per compilatore e test.
Nel clipboard generato i titoli delle 136 regole vengono numerati consecutivamente
da 0 a 135 nell'ordine del file, senza duplicati o suffissi alfabetici. La
numerazione dei titoli non modifica il comportamento o i nomi delle subroutine.

```text
python tools/build_global_runtime.py
python tools/build_global_runtime.py --check
python tools/validate_workshop.py
```

`ResetMenuPage` ripristina la sola pagina personale tramite Crouch + Ultimate sulle voci abilitate. Le icone native seguono la posizione live del proprietario entro 5 m tridimensionali, conservando l’identità catturata; i nomi interni `ObjectiveIconPosition` e `UpdateSocialObjectiveIcons` restano stabili per compilatore e test.

Le nuove pagine Presence 17, Fates 18, Whispers 19 e Moonlit Aura 20 condividono un renderer e l'array personale `NocturneState`. Il renderer cattura la sola pagina dell'HUD per evitare il passaggio a Moonlit Aura tornando al principale con Reload; scelte e preferenze restano dinamiche. Presence usa il roster esistente; Fates mostra il risultato in un HUD privato sotto Arcade, con una riga vuota prima del testo e durata di 3–4 secondi, mentre il menu mostra READY/RESTING. `ShowFateResult` e `CleanupFateResults` gestiscono snapshot e ownership del risultato. Whispers raggiunge un umano pubblico a qualsiasi distanza, mantenendo mira entro 12°, linea di vista e ricezione ON. Fates e Whispers conservano i cooldown durante il reset; le aure hanno un solo effetto per umano, registri di ownership e filtro di visibilità personale. Comandi e default sono nel [README](../README.md#menu-personali); la [matrice nel client](../docs/TEST.md#presence-fates-whispers-e-moonlit-aura) distingue queste modifiche dal pacchetto pubblicato.

Applicare o alternare Ghost aggiorna soltanto la collisione ambientale e conserva l'inerzia; le transizioni Fly mantengono il proprio applicatore fisico. La correzione Ghost è successiva al riscontro qualitativo «funziona tutto» ricevuto il 28 ottobre dopo la PR #114 e richiede una nuova verifica nel client.

La generazione e i gate del runtime non provano l'assenza di crash nel motore
Overwatch. [Architettura](../docs/PROGETTO.md) · [Validazione](../docs/VALIDAZIONE.md)
