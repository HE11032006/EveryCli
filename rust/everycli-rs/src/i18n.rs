//! Internationalization (i18n) module for EveryCli.
//! Supports English (`Lang::En`) and French (`Lang::Fr`).

use std::env;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Lang {
    En,
    Fr,
}

impl Lang {
    pub fn from_str_opt(s: &str) -> Option<Self> {
        match s.trim().to_lowercase().as_str() {
            "fr" | "french" | "francais" | "français" | "fr_fr" | "fr_ca" | "fr_be" | "fr_ch" => {
                Some(Lang::Fr)
            }
            "en" | "english" | "anglais" | "en_us" | "en_gb" | "en_ca" => Some(Lang::En),
            _ => None,
        }
    }

    /// Detect language: checks env `EVERYCLI_LANG`, then configured language,
    /// then OS locale (`LANG` / `LC_ALL` / `LC_MESSAGES`), fallback is `En`.
    pub fn resolve(configured: Option<&str>) -> Self {
        if let Ok(env_lang) = env::var("EVERYCLI_LANG") {
            if let Some(lang) = Self::from_str_opt(&env_lang) {
                return lang;
            }
        }
        if let Some(cfg) = configured {
            if let Some(lang) = Self::from_str_opt(cfg) {
                return lang;
            }
        }
        // Check system locale
        for var in &["LC_ALL", "LC_MESSAGES", "LANG"] {
            if let Ok(val) = env::var(var) {
                if val.to_lowercase().starts_with("fr") {
                    return Lang::Fr;
                }
            }
        }
        Lang::En
    }

    pub fn code(&self) -> &'static str {
        match self {
            Lang::En => "en",
            Lang::Fr => "fr",
        }
    }

    pub fn name(&self) -> &'static str {
        match self {
            Lang::En => "English",
            Lang::Fr => "Français",
        }
    }

    // ─── Help & Global ───────────────────────────────────────────────────────

    pub fn help_text(&self) -> &'static str {
        match self {
            Lang::En => {
                "EveryCli - Natural language CLI command discoverer and assistant\n\n\
Usage: everycli search <query> [options]\n\
       everycli add\n\
       everycli list\n\
       everycli remove [id]\n\
       everycli ask <question>\n\
       everycli config set <key> <value>\n\
       everycli config get <key>\n\
       everycli config show\n\n\
Search options:\n\
  --top N, -t N            Number of results (default 1)\n\
  --platform linux|windows|macos\n\
  --data DIR               Corpus directory override\n\
  --json                   Machine-readable JSON output\n\
  --error MSG, -e MSG      Diagnose an error message against known hints\n\
  --env NAME               Filter results by environment tag (e.g. git, docker)\n\
  --copy, -c               Copy the resolved command to clipboard\n\
  --run, -r                Confirm and execute the resolved command\n\
  --interactive, -i        Pick a result using keyboard arrow keys\n\
  --shell, -s              Print only the raw resolved command to stdout\n\
  --no-daemon              Skip daemon and search local corpus directly\n\
  --debug                  Show similarity scores\n\n\
Config keys: language (en|fr), api_key, api_url, api_model, provider\n\
  Supported providers: openai, groq, gemini, mistral, openrouter, claude, deepseek, cloudflare\n\n\
'add'       Interactively adds a custom command scenario into ~/.everycli/commands.\n\
'list'      Displays all custom commands saved in your personal corpus.\n\
'remove'    Removes a custom command (interactive selection if no id provided).\n\
'ask'       Queries an external LLM API and optionally saves the command locally.\n"
            }
            Lang::Fr => {
                "EveryCli - Découvreur et assistant de commandes en langage naturel\n\n\
Usage: everycli search <requête> [options]\n\
       everycli add\n\
       everycli list\n\
       everycli remove [id]\n\
       everycli ask <question>\n\
       everycli config set <clé> <valeur>\n\
       everycli config get <clé>\n\
       everycli config show\n\n\
Options de recherche :\n\
  --top N, -t N            Nombre de résultats (défaut 1)\n\
  --platform linux|windows|macos\n\
  --data DIR               Dossier personnalisé du corpus\n\
  --json                   Sortie JSON pour scripts\n\
  --error MSG, -e MSG      Diagnostique un message d'erreur avec les indices connus\n\
  --env NAME               Filtre par tag d'environnement (ex: git, docker)\n\
  --copy, -c               Copie la commande résolue dans le presse-papier\n\
  --run, -r                Demande confirmation et exécute la commande\n\
  --interactive, -i        Choisit un résultat au clavier avec les flèches\n\
  --shell, -s              Affiche uniquement la commande brute sur stdout\n\
  --no-daemon              Ignore le daemon et cherche dans le corpus local\n\
  --debug                  Affiche les scores de similarité\n\n\
Clés de configuration : language (en|fr), api_key, api_url, api_model, provider\n\
  Providers supportés : openai, groq, gemini, mistral, openrouter, claude, deepseek, cloudflare\n\n\
'add'       Ajoute interactivement une commande personnalisée dans ~/.everycli/commands.\n\
'list'      Affiche toutes les commandes personnalisées de votre corpus.\n\
'remove'    Supprime une commande personnalisée (sélection au clavier si id omis).\n\
'ask'       Interroge un LLM et propose d'enregistrer la commande localement.\n"
            }
        }
    }

    // ─── Clipboard & Execution ───────────────────────────────────────────────

    pub fn copied_to_clipboard(&self) -> &'static str {
        match self {
            Lang::En => "Command copied to clipboard (Ctrl+V to paste)",
            Lang::Fr => "Commande copiée dans le presse-papier (Ctrl+V pour coller)",
        }
    }

    pub fn ambiguous_action_target(&self, id: &str, command: &str) -> String {
        match self {
            Lang::En => format!(
                "Multiple results: using the first result for the requested action — {id} ({command})"
            ),
            Lang::Fr => format!(
                "Plusieurs résultats : action appliquée au premier résultat — {id} ({command})"
            ),
        }
    }

    pub fn clipboard_failed(&self) -> &'static str {
        match self {
            Lang::En => "Unable to copy command to clipboard.",
            Lang::Fr => "Impossible de copier dans le presse-papier.",
        }
    }

    pub fn run_confirm_prompt(&self, cmd: &str) -> String {
        match self {
            Lang::En => format!("Execute `{cmd}` ? [y/N] "),
            Lang::Fr => format!("Exécuter `{cmd}` ? [o/N] "),
        }
    }

    pub fn exec_failed(&self, err: &str) -> String {
        match self {
            Lang::En => format!("Execution failed: {err}"),
            Lang::Fr => format!("Échec de l'exécution : {err}"),
        }
    }

    pub fn exec_exit_code(&self, code: i32) -> String {
        match self {
            Lang::En => format!("Command exited with code {code}."),
            Lang::Fr => format!("Commande terminée avec le code {code}."),
        }
    }

    // ─── Search Diagnostics & Results ────────────────────────────────────────

    pub fn search_results_header(&self, count: usize, query: &str) -> String {
        match self {
            Lang::En => format!("{count} results for \"{query}\""),
            Lang::Fr => format!("{count} résultats pour \"{query}\""),
        }
    }

    pub fn pick_interactive_prompt(&self) -> &'static str {
        match self {
            Lang::En => "Choose a command:",
            Lang::Fr => "Choisis une commande :",
        }
    }

    pub fn no_match_found(&self) -> &'static str {
        match self {
            Lang::En => "no command matched this query",
            Lang::Fr => "aucune commande ne correspond à cette requête",
        }
    }

    pub fn daemon_fallback_warn(&self, reason: &str) -> String {
        match self {
            Lang::En => format!("daemon fallback ({reason}), using local search"),
            Lang::Fr => format!("daemon non joignable ({reason}), bascule sur la recherche locale"),
        }
    }

    // ─── Add Command ─────────────────────────────────────────────────────────

    pub fn add_title(&self) -> &'static str {
        match self {
            Lang::En => "=== Add a custom command to EveryCli ===",
            Lang::Fr => "=== Ajouter une commande à EveryCli ===",
        }
    }

    pub fn add_category_prompt(&self) -> &'static str {
        match self {
            Lang::En => "Category / file name (e.g. my-scripts): ",
            Lang::Fr => "Catégorie / nom de fichier (ex: mes-scripts) : ",
        }
    }

    pub fn add_category_empty(&self) -> &'static str {
        match self {
            Lang::En => "category cannot be empty",
            Lang::Fr => "la catégorie ne peut pas être vide",
        }
    }

    pub fn add_description_prompt(&self) -> &'static str {
        match self {
            Lang::En => "Description (used for search matching): ",
            Lang::Fr => "Description (utilisée pour la recherche) : ",
        }
    }

    pub fn add_description_empty(&self) -> &'static str {
        match self {
            Lang::En => "description cannot be empty",
            Lang::Fr => "la description ne peut pas être vide",
        }
    }

    pub fn add_command_prompt(&self) -> &'static str {
        match self {
            Lang::En => "Command: ",
            Lang::Fr => "Commande : ",
        }
    }

    pub fn add_command_empty(&self) -> &'static str {
        match self {
            Lang::En => "command cannot be empty",
            Lang::Fr => "la commande ne peut pas être vide",
        }
    }

    pub fn add_explanation_prompt(&self) -> &'static str {
        match self {
            Lang::En => "Explanation (displayed with results): ",
            Lang::Fr => "Explication (affichée avec le résultat) : ",
        }
    }

    pub fn add_tags_prompt(&self) -> &'static str {
        match self {
            Lang::En => "Tags, comma-separated (optional): ",
            Lang::Fr => "Tags, séparés par des virgules (optionnel) : ",
        }
    }

    pub fn add_warning_prompt(&self) -> &'static str {
        match self {
            Lang::En => "Safety warning if dangerous (optional, Enter to skip): ",
            Lang::Fr => "Avertissement si commande risquée (optionnel, Entrée pour ignorer) : ",
        }
    }

    pub fn add_success(&self, id: &str, file: &str) -> String {
        match self {
            Lang::En => format!("Command added: {id}\n  File: {file}"),
            Lang::Fr => format!("Commande ajoutée : {id}\n  Fichier : {file}"),
        }
    }

    pub fn daemon_reloaded(&self) -> &'static str {
        match self {
            Lang::En => "Daemon reloaded — available immediately.",
            Lang::Fr => "Daemon rechargé — disponible immédiatement.",
        }
    }

    pub fn daemon_reload_failed(&self, reason: &str) -> String {
        match self {
            Lang::En => format!(
                "Command saved, but daemon reload was not confirmed: {reason}"
            ),
            Lang::Fr => format!(
                "Commande enregistrée, mais le rechargement du daemon n'a pas été confirmé : {reason}"
            ),
        }
    }

    // ─── List & Remove ───────────────────────────────────────────────────────

    pub fn list_empty(&self) -> &'static str {
        match self {
            Lang::En => "No custom commands found. Use `everycli add` to create one.",
            Lang::Fr => "Aucune commande personnalisée pour l'instant. Utilise `everycli add` pour en ajouter une.",
        }
    }

    pub fn list_header(&self, count: usize) -> String {
        match self {
            Lang::En => format!("{count} custom command(s)"),
            Lang::Fr => format!("{count} commande(s) personnalisée(s)"),
        }
    }

    pub fn remove_empty(&self) -> &'static str {
        match self {
            Lang::En => "No custom commands to remove.",
            Lang::Fr => "Aucune commande personnalisée à supprimer.",
        }
    }

    pub fn remove_pick_prompt(&self) -> &'static str {
        match self {
            Lang::En => "Which command to remove?",
            Lang::Fr => "Quelle commande supprimer ?",
        }
    }

    pub fn remove_not_found(&self, id: &str) -> String {
        match self {
            Lang::En => format!("no custom command found with id '{id}'"),
            Lang::Fr => format!("aucune commande personnalisée avec l'id '{id}'"),
        }
    }

    pub fn remove_confirm_prompt(&self, id: &str, cmd: &str) -> String {
        match self {
            Lang::En => format!("Delete '{id}' ({cmd}) ?"),
            Lang::Fr => format!("Supprimer '{id}' ({cmd}) ?"),
        }
    }

    pub fn remove_canceled(&self) -> &'static str {
        match self {
            Lang::En => "Canceled.",
            Lang::Fr => "Annulé.",
        }
    }

    pub fn remove_success(&self, id: &str) -> String {
        match self {
            Lang::En => format!("Command '{id}' deleted."),
            Lang::Fr => format!("Commande '{id}' supprimée."),
        }
    }

    // ─── Ask ─────────────────────────────────────────────────────────────────

    pub fn ask_querying(&self, model: &str) -> String {
        match self {
            Lang::En => format!("Querying AI provider ({model})…"),
            Lang::Fr => format!("Interrogation de l'API ({model})…"),
        }
    }

    pub fn ask_save_prompt(&self) -> &'static str {
        match self {
            Lang::En => "Save this command to your local corpus? [y/N] ",
            Lang::Fr => "Sauvegarder cette commande dans votre corpus ? [o/N] ",
        }
    }

    pub fn no_api_key_error(&self) -> &'static str {
        match self {
            Lang::En => "No API key configured.\n  Set it via: everycli config set api_key <your-key>\n  Or via environment variable: EVERYCLI_API_KEY",
            Lang::Fr => "Aucune clé API configurée.\n  Définir via : everycli config set api_key <votre-clé>\n  Ou via variable d'environnement : EVERYCLI_API_KEY",
        }
    }
}
