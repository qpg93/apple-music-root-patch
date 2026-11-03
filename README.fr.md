# Apple-Music-for-Rooted-Devices

[English](README.md) | [日本語](README.ja.md) | **Français** | [简体中文](README.zh-CN.md)

Notes d'ingénierie et outillage de compilation pour désactiver la **détection de
root** d'Apple Music pour Android — **aucun binaire APK n'est hébergé ici**. Tout
ce dépôt contient des scripts, une technique de patch et de la documentation ;
vous téléchargez vous-même l'application officielle et appliquez le patch en local.

Ce projet est né comme fork du [dépôt d'arabaizzet](https://github.com/arabaizzet/Apple-Music-for-Rooted-Devices)
(qui distribuait une version modifiée d'Apple Music 4.8.1). Ce dépôt n'étant plus
mis à jour, ce fork est devenu un *guide pratique* : la même technique, documentée
et automatisée, confirmée sans changement sur Apple Music **5.2.1, 6.5.3 et 7.0.0**.

## Pourquoi

Depuis la v4.7 (mars 2024), Apple Music pour Android refuse de démarrer lorsqu'il
croit l'appareil rooté. Cela pénalise :

- les appareils réellement rootés où `su` se trouve dans l'un des chemins vérifiés ;
- les appareils d'origine qui produisent un **faux positif** — par exemple
  certaines **TV Xiaomi**, où l'application officielle se ferme au démarrage.

## Comment fonctionne la détection de root

Les détails du reverse engineering (dumps smali, noms de classes par version) sont
dans [`docs/root-detection-analysis.md`](docs/root-detection-analysis.md). En bref,
la classe `Application` de l'app exécute un contrôle équivalent à :

```java
boolean isDeviceRooted() {
    return helperCheck()                     // ("test-keys", /system/app/Superuser.apk, /system/xbin/su)
        || new File("/system/bin/su").exists();
}
```

La chaîne d'aide passe sur les systèmes d'origine ; sur les appareils bloqués,
le test décisif est `new File("/system/bin/su").exists()`.

### Le patch

Remplacer la chaîne de 14 octets `/system/bin/su` dans le pool de constantes du
dex par un chemin inexistant de **même longueur** :

```
/system/bin/su   →   /system/b1n/su        ("bin" → "b1n")
```

Comme le remplacement a la même longueur et que le dex est uniquement patché au
niveau binaire (sans recompilation smali), l'APK obtenu est identique octet pour
octet à l'officiel, à l'exception de ces 14 octets — plus le zipalign et la
re-signature (les APK split doivent aussi être re-signés, une re-signature
complète est donc inévitable de toute façon).

Le mod 4.8.1 d'origine utilisait la même idée avec la chaîne
`/system/bin/applemusicwizzeyeren` (ce qui nécessitait une recompilation smali,
cette chaîne étant plus longue).

**Ce qui n'est pas modifié :** pas de modification DRM, pas de contournement
d'abonnement, rien d'autre. Vous avez toujours besoin d'un vrai identifiant Apple
avec un abonnement Apple Music actif pour utiliser l'application.

## Compiler votre propre APK patché

### Prérequis

- JDK 17+ (seul `java` est nécessaire ; aucune compilation de sources Java)
- [APKEditor 1.4.x](https://github.com/REAndroid/APKEditor/releases) — fusionne
  l'APK de base et les splits de configuration du bundle `.apkm` officiel en un
  APK universel
- [uber-apk-signer 1.3.x](https://github.com/patrickfav/uber-apk-signer/releases) —
  zipalign + signature v1/v2/v3 avec une clé de débogage générée
- (facultatif, pour la vérification) Python 3 avec `uv` ou `pip install androguard`

Le script de compilation télécharge automatiquement les deux JAR s'ils manquent.
Lancez `./tools/doctor.sh` d'abord si vous n'êtes pas sûr de votre environnement.

### 1. Obtenir le bundle officiel

```bash
python3 tools/fetch_official.py --version 5.2.1
```

Télécharge automatiquement le `.apkm` officiel depuis APKMirror (chaîne de
téléchargement gérant les cookies et le Referer) et vérifie le SHA-256 du tableau
ci-dessous avant l'enregistrement. Description complète de la chaîne et méthode
manuelle : [`docs/downloading-official.md`](docs/downloading-official.md).

| Version | versionCode | Android requis | Page de release APKMirror | SHA-256 du `.apkm` |
|---|---|---|---|---|
| 5.2.1 | 1545 | 10.0 (API 29) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-5-2-1-release/) | `1d74cea9d0d6a7c77bf4d004197be52e9e14110414255caa3825142fc19b7962` |
| 6.5.3 | 1599 | 11.0 (API 30) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-6-5-3-release/) | `a0494d1aac72f9d7901683b9da7df0afe46fae56ac5ad4070c7e265567eabd89` |
| 7.0.0 | 1614 | 11.0 (API 30) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-7-0-0-release/) | `08219d7f9ab143e4ca5858964c630e8b197881eff0e8dff0742cdc7510bf4b1c` |

*(Sur la page de téléchargement, choisissez la variante **universal / BUNDLE**.
Vérifiez le SHA-256 après le téléchargement.)*

### 2. Lancer la compilation

```bash
./tools/build_patched_apk.sh AppleMusic-5.2.1.apkm
# → AppleMusic-5.2.1-patched.apk
```

Le script : fusionne le bundle → patche binairement chaque `/system/bin/su` dans
les dex → indique le nombre de patchs → zipaligne et signe le résultat. Il échoue
explicitement si le nombre de patchs n'est pas exactement 1. Si l'entrée est déjà
un APK unique, la fusion est ignorée automatiquement.

### 3. Vérifier (facultatif mais recommandé)

```bash
uv run --with androguard python tools/verify_patched_apk.py AppleMusic-5.2.1-patched.apk
```

Vérifie le paquet/les versions, l'absence de l'ancienne chaîne et la présence du
remplacement, ainsi que la signature v1+v2+v3.

### 4. Installer

Si une copie de l'application est déjà installée avec une autre signature,
désinstallez-la d'abord (un mot de passe peut être demandé à la reconnexion) :

```bash
adb uninstall com.apple.android.music
adb install AppleMusic-5.2.1-patched.apk
```

Ou copiez l'APK sur l'appareil et installez-le depuis un gestionnaire de fichiers
(autorisez d'abord « Installer des applications inconnues » pour ce gestionnaire).

## Structure du dépôt

```
tools/fetch_official.py          télécharge le .apkm officiel depuis APKMirror + vérif SHA-256
tools/doctor.sh                  vérification de l'environnement avant compilation
tools/build_patched_apk.sh       pipeline fusion → patch binaire → signature
tools/patch_dex.py               le patch de chaîne lui-même (utilisé par le script ci-dessus)
tools/test_patch_dex.py          auto-tests de la logique de patch (sans code Apple)
tools/verify_patched_apk.py      vérification après compilation (androguard)
tools/locate_root_check.py       scanner dex qui trouve les contrôles de chemin su
tools/check_new_version.py       compare la dernière version APKMirror avec le tableau
docs/root-detection-analysis.md  résultats RE complets, carte classes/méthodes par version
docs/building-android-tv.md      guide de sideload TV + dépannage (exemple Xiaomi)
docs/downloading-official.md     chaîne de téléchargement APKMirror, particularités anti-bot
DISCLAIMER.md                    texte légal / avertissement complet
```

L'intégration continue exécute les auto-tests à chaque push — voir
`.github/workflows/ci.yml`. Un workflow planifié quotidiennement
(`.github/workflows/version-watch.yml`) vérifie les nouvelles versions sur
APKMirror et ouvre une issue avec la checklist de suivi le cas échéant.

Les scripts et la documentation sont sous licence MIT (`LICENSE`) ; les binaires
d'Apple Music ne sont ni inclus ni distribués par ce dépôt.

## Mentions légales

**Lisez [`DISCLAIMER.md`](DISCLAIMER.md) en entier.** Résumé : ce dépôt ne contient
que des scripts et de la documentation — aucun binaire Apple. Il s'agit de
recherches non auditées et non affiliées à Apple, portant sur un patch de 14 octets
d'une chaîne de diagnostic ; il ne touche ni aux DRM, ni aux contrôles
d'abonnement, ni à aucun mécanisme de protection de contenu. La compilation et
l'installation d'un APK patché relèvent de votre décision et de votre
responsabilité, au regard de la loi locale, des conditions d'Apple et de la
garantie de votre appareil. Aucune garantie d'aucune sorte.
