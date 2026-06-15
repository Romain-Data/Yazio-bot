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

## 🤖 Fonctionnalités de l'API

- `POST /analyze/text` : Analyse une description textuelle d'un repas.
- `POST /analyze/image` : Analyse une photo avec ou sans texte additionnel.
- `POST /analyze/correction` : Permet de corriger une analyse (ex: "J'ai plutôt mangé 200g de pâtes").
- `POST /log` : Envoie les résultats de l'analyse directement dans l'application Yazio de l'utilisateur.
  - *Note : Gère les aliments génériques mais aussi vos recettes personnelles ! Il suffit de rajouter `(recette)` à côté d'un aliment dans la description.*

## ⚠️ Avertissement de Sécurité
Ne publiez **JAMAIS** votre fichier `.env` ou vos identifiants Yazio. Ce projet n'est pas affilié à Yazio et utilise leur API interne de manière non-officielle à des fins purement personnelles.
