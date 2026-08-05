# 🍏 Yazio AI Tracker (avec n8n & Telegram)

Ce projet permet de transformer un simple bot Telegram en un véritable assistant nutritionnel. Vous prenez une photo de votre repas ou décrivez ce que vous mangez par texte, et le système s'occupe de l'analyser (via l'API de Mammouth AI) et de l'enregistrer automatiquement dans votre journal alimentaire **Yazio**.

Il gère même vos **recettes personnelles Yazio** !

## 🏗 Architecture

Le projet est composé de 3 briques principales :
1. **Telegram** : L'interface utilisateur pour envoyer les textes, les photos et les corrections.
2. **n8n** : Le chef d'orchestre (workflow) qui relie Telegram et l'API Python.
3. **L'API Python (FastAPI)** : Le cœur du système qui contient ce code source. Elle interroge l'API de Mammouth AI (modèle gemini-2.5-flash-lite par défaut) pour estimer les calories/grammes, recherche les produits dans Yazio, et enregistre les repas.

## 🚀 Installation & Lancement

Le projet est conçu pour tourner via Docker.

### 1. Variables d'Environnement
Copiez le fichier `.env.example` et renommez-le en `.env`. Remplissez-le avec vos identifiants :
```bash
cp .env.example .env
```
Assurez-vous d'avoir :
- L'email et le mot de passe de votre compte Yazio (pour que le script s'y connecte de manière invisible).
- Une clé API Mammouth AI.

### 2. Lancement avec Docker
```bash
docker compose build --no-cache
docker compose up -d
```
L'API tournera alors sur le port `8000`.

### 3. Workflow n8n
L'API Python seule ne fait rien sans n8n. Voici comment relier l'ensemble :

1. **Importer le workflow** : Ouvrez n8n, allez dans vos workflows, cliquez sur l'engrenage (ou le menu en haut à droite) et choisissez "Import from File". Sélectionnez le fichier `n8n_workflow.json` fourni dans ce dépôt.
2. **Configurer le bot Telegram** : Dans le workflow importé, double-cliquez sur le nœud "Telegram Trigger". Créez une nouvelle "Credential" et renseignez-y le **Token de votre Bot Telegram** (obtenu via BotFather). N'oubliez pas d'assigner cette même *credential* au nœud "Envoyer Résumé + Bouton" situé à la fin du workflow.
3. **Connecter n8n à l'API** : Le workflow contient des nœuds "HTTP Request" (comme "Analyse Texte", "Analyse Photo" ou "Envoi Yazio"). Double-cliquez sur ces nœuds et vérifiez que l'URL pointe bien vers votre API Python locale (par exemple `http://localhost:8000/analyze/text` ou l'IP de votre serveur local comme `http://192.168.x.x:8000/log`).

Une fois ces étapes validées, activez le workflow en haut à droite de l'écran n8n. Votre bot est prêt !

## 📝 Commandes & Routage Automatique

L'API utilise un système de **routage hybride** (Regex + Fallback sémantique) qui analyse votre message Telegram pour diriger la requête vers le bon extracteur spécialisé :

1. **Repas Standard (Par défaut)**
   - **Déclenchement** : Si aucun mot-clé spécial n'est détecté.
   - **Usage** : Listez simplement vos aliments et quantités (ex: *"100g de riz, 150g de poulet et une pomme"*).
   - **Astuce Recette** : Si vous consommez une recette déjà enregistrée sur Yazio, ajoutez `(recette)` à côté du nom (ex: *"200g de cake aux olives (recette)"*).

2. **Activité Physique & Sport**
   - **Déclenchement** : Commencer le message par un mot-clé de sport (`activité`, `sport`, `footing`, `séance`, `muscu`, `piscine`, etc.) **OU** si le texte décrit implicitement une activité (ex: *"1h30 d'entraînement de tennis"*).
   - **Usage** : Estime de manière ultra-prudente la dépense calorique (basée sur un adulte de 75 kg) et l'enregistre en tant qu'exercice dans Yazio.

3. **Création de Recette**
   - **Déclenchement** : Commencer le message par `recette` ou `nouvelle recette` (ex: *"Nouvelle recette : Tarte aux pommes - 6 portions. Ingrédients : 1 pâte feuilletée, 4 pommes, 50g de beurre"*).
   - **Usage** : Calcule les macronutriments par portion et enregistre la recette dans votre compte Yazio.

4. **Création d'Équivalences de poids**
   - **Déclenchement** : Commencer le message par `équivalence` ou `nouvelle équivalence` (ex: *"Nouvelle équivalence : 1 tranche de jambon blanc 45g"*).
   - **Usage** : Enregistre la correspondance dans `custom_weights.json` pour vos futures saisies rapides.

5. **Estimation Globale**
   - **Déclenchement** : Commencer le message par `estimation` ou `estime` (ex: *"Estimation : Couscous royal au restaurant ce midi"*).
   - **Usage** : Fait une estimation globale du repas entier (sans lister chaque ingrédient individuellement) et suggère des questions d'affinage pour préciser la portion.

---

## 🤖 Fonctionnalités de l'API

- `POST /analyze/text` : Analyse une description textuelle (repas, sport, recette, équivalence ou estimation).
- `POST /analyze/image` : Analyse une photo avec ou sans commentaire.
- `POST /analyze/correction` : Corrige l'analyse précédente (ex: *"C'était en fait 2h d'entraînement"* ou *"Enlève le beurre"*).
- `POST /log` : Envoie les résultats (aliments, exercices, équivalences ou recettes) directement dans votre compte Yazio.

## ⚠️ Avertissement de Sécurité
Ne publiez **JAMAIS** votre fichier `.env` ou vos identifiants Yazio. Ce projet n'est pas affilié à Yazio et utilise leur API interne de manière non-officielle à des fins purement personnelles.
