//! Fast, dependency-free retrieval core for EveryCli.
//!
//! It deliberately keeps YAML as the source of truth. The current implementation
//! is the deterministic lexical fast path; semantic reranking can be added as a
//! separate stage without changing the corpus or the public result model.

use std::cmp::Ordering;
use std::collections::HashSet;
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs;
use std::path::{Path, PathBuf};

pub mod daemon;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Platform {
    Linux,
    Windows,
    Macos,
}

impl Platform {
    pub fn parse(value: &str) -> Option<Self> {
        match value.to_ascii_lowercase().as_str() {
            "linux" => Some(Self::Linux),
            "windows" | "win" => Some(Self::Windows),
            "macos" | "mac" | "darwin" => Some(Self::Macos),
            _ => None,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Commands {
    pub linux: String,
    pub windows: String,
    pub macos: String,
}

impl Commands {
    pub fn for_platform(&self, platform: Platform) -> &str {
        match platform {
            Platform::Linux => &self.linux,
            Platform::Windows => &self.windows,
            Platform::Macos if !self.macos.is_empty() => &self.macos,
            Platform::Macos => &self.linux,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ErrorHint {
    pub trigger: String,
    pub cause: String,
    pub fix: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Scenario {
    pub id: String,
    pub description: String,
    pub tags: Vec<String>,
    pub commands: Commands,
    pub explanation: String,
    pub warning: String,
    pub error_hints: Vec<ErrorHint>,
    pub namespace: String,
}

/// Find the first hint whose trigger appears in `error_message`
/// (case-insensitive substring match), mirroring
/// `everycli/core/models.py::SearchResult.hint_for_error`.
pub fn find_error_hint<'a>(scenario: &'a Scenario, error_message: &str) -> Option<&'a ErrorHint> {
    let error_lower = error_message.to_lowercase();
    scenario
        .error_hints
        .iter()
        .find(|hint| error_lower.contains(&hint.trigger.to_lowercase()))
}

#[derive(Clone, Debug)]
pub struct SearchHit {
    pub scenario: Scenario,
    pub command: String,
    pub score: f32,
}

#[derive(Debug)]
pub enum CoreError {
    Io(std::io::Error),
    EmptyCorpus(PathBuf),
}

impl Display for CoreError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(error) => write!(formatter, "{error}"),
            Self::EmptyCorpus(path) => {
                write!(formatter, "no scenarios found in {}", path.display())
            }
        }
    }
}

impl Error for CoreError {}

impl From<std::io::Error> for CoreError {
    fn from(error: std::io::Error) -> Self {
        Self::Io(error)
    }
}

#[derive(Default)]
struct ScenarioBuilder {
    id: String,
    description: String,
    tags: Vec<String>,
    linux: String,
    windows: String,
    macos: String,
    explanation: String,
    warning: String,
    error_hints: Vec<ErrorHint>,
    current_hint: Option<ErrorHint>,
    namespace: String,
    base_indent: usize,
    in_commands: bool,
    in_errors: bool,
}

impl ScenarioBuilder {
    fn flush_current_hint(&mut self) {
        if let Some(hint) = self.current_hint.take() {
            self.error_hints.push(hint);
        }
    }
}

impl ScenarioBuilder {
    fn new(id: String, namespace: &str, base_indent: usize) -> Self {
        Self {
            id,
            namespace: namespace.to_owned(),
            base_indent,
            ..Self::default()
        }
    }

    fn finish(mut self) -> Scenario {
        if self.windows.is_empty() {
            self.windows = self.linux.clone();
        }
        self.flush_current_hint();
        Scenario {
            id: self.id,
            description: self.description,
            tags: self.tags,
            commands: Commands {
                linux: self.linux,
                windows: self.windows,
                macos: self.macos,
            },
            explanation: self.explanation,
            warning: self.warning,
            error_hints: self.error_hints,
            namespace: self.namespace,
        }
    }
}

/// Load every YAML file from the existing EveryCli corpus.
///
/// The parser intentionally reads only the scenario fields used for retrieval.
/// Extra YAML keys such as examples and error hints remain forward compatible.
pub fn load_corpus(data_dir: impl AsRef<Path>) -> Result<Vec<Scenario>, CoreError> {
    let data_dir = data_dir.as_ref();
    let mut files = fs::read_dir(data_dir)?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.extension()
                .is_some_and(|extension| extension == "yaml")
        })
        .collect::<Vec<_>>();
    files.sort();

    let mut scenarios = Vec::new();
    for path in files {
        scenarios.extend(parse_corpus_file(&path)?);
    }

    if scenarios.is_empty() {
        return Err(CoreError::EmptyCorpus(data_dir.to_path_buf()));
    }
    Ok(scenarios)
}

/// Load the built-in corpus AND a user-defined corpus (e.g. `~/.everycli/commands`,
/// written by `everycli add`), merged into one list. The user directory is
/// OPTIONAL — missing or empty is not an error (a fresh install has none
/// yet), unlike [`load_corpus`] on the built-in directory which does error
/// on an empty/missing corpus.
pub fn load_corpus_merged(
    builtin_dir: impl AsRef<Path>,
    user_dir: impl AsRef<Path>,
) -> Result<Vec<Scenario>, CoreError> {
    let mut scenarios = load_corpus(builtin_dir)?;
    if user_dir.as_ref().is_dir()
        && let Ok(user_scenarios) = load_corpus(user_dir)
    {
        scenarios.extend(user_scenarios);
    }
    Ok(scenarios)
}

fn parse_corpus_file(path: &Path) -> Result<Vec<Scenario>, CoreError> {
    let namespace = path
        .file_stem()
        .and_then(|stem| stem.to_str())
        .unwrap_or_default();
    let content = fs::read_to_string(path)?;
    let mut scenarios = Vec::new();
    let mut current: Option<ScenarioBuilder> = None;

    for raw_line in content.lines() {
        if let Some((id, indent)) = scenario_start(raw_line) {
            if let Some(builder) = current.take() {
                scenarios.push(builder.finish());
            }
            current = Some(ScenarioBuilder::new(id, namespace, indent));
            continue;
        }

        let Some(builder) = current.as_mut() else {
            continue;
        };
        let indent = raw_line.len() - raw_line.trim_start().len();
        let trimmed = raw_line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }

        if indent == builder.base_indent + 2 {
            builder.in_commands = false;
            if builder.in_errors {
                builder.flush_current_hint();
                builder.in_errors = false;
            }
            if trimmed == "commands:" {
                builder.in_commands = true;
                continue;
            }
            if trimmed == "errors:" {
                builder.in_errors = true;
                continue;
            }
            if let Some(value) = yaml_value(trimmed, "description") {
                builder.description = value;
            } else if let Some(value) = yaml_value(trimmed, "tags") {
                builder.tags = parse_inline_list(&value);
            } else if let Some(value) = yaml_value(trimmed, "command") {
                builder.linux = value.clone();
                builder.windows = value;
            } else if let Some(value) = yaml_value(trimmed, "explanation") {
                builder.explanation = value;
            } else if let Some(value) = yaml_value(trimmed, "warning") {
                builder.warning = value;
            }
            continue;
        }

        if builder.in_commands && indent == builder.base_indent + 4 {
            if let Some(value) = yaml_value(trimmed, "linux") {
                builder.linux = value;
            } else if let Some(value) = yaml_value(trimmed, "windows") {
                builder.windows = value;
            } else if let Some(value) = yaml_value(trimmed, "macos") {
                builder.macos = value;
            }
            continue;
        }

        if builder.in_errors && indent == builder.base_indent + 4 {
            if let Some(value) = trimmed.strip_prefix("- trigger:") {
                builder.flush_current_hint();
                builder.current_hint = Some(ErrorHint {
                    trigger: clean_scalar(value),
                    cause: String::new(),
                    fix: String::new(),
                });
            }
            continue;
        }

        if builder.in_errors
            && indent == builder.base_indent + 6
            && let Some(hint) = builder.current_hint.as_mut()
        {
            if let Some(value) = yaml_value(trimmed, "cause") {
                hint.cause = value;
            } else if let Some(value) = yaml_value(trimmed, "fix") {
                hint.fix = value;
            }
        }
    }

    if let Some(builder) = current {
        scenarios.push(builder.finish());
    }
    Ok(scenarios)
}

fn scenario_start(raw_line: &str) -> Option<(String, usize)> {
    let indent = raw_line.len() - raw_line.trim_start().len();
    let value = raw_line.trim_start().strip_prefix("- id:")?;
    let id = clean_scalar(value);
    (!id.is_empty()).then_some((id, indent))
}

fn yaml_value(line: &str, key: &str) -> Option<String> {
    let value = line.strip_prefix(key)?.strip_prefix(':')?;
    Some(clean_scalar(value))
}

fn clean_scalar(value: &str) -> String {
    let value = value.trim();
    if value.len() >= 2
        && ((value.starts_with('"') && value.ends_with('"'))
            || (value.starts_with('\'') && value.ends_with('\'')))
    {
        value[1..value.len() - 1].to_owned()
    } else {
        value.to_owned()
    }
}

fn parse_inline_list(value: &str) -> Vec<String> {
    let value = value.trim().trim_start_matches('[').trim_end_matches(']');
    value
        .split(',')
        .map(clean_scalar)
        .filter(|tag| !tag.is_empty())
        .collect()
}

/// Filter the corpus down to scenarios eligible for `query`/`platform`
/// (explicit namespace routing + platform command availability), *without*
/// requiring a positive lexical score. Exposed so a semantic reranking layer
/// (see `everycli-daemon`) can score candidates that a pure lexical match
/// would otherwise drop entirely — e.g. a paraphrase with zero token
/// overlap with the corpus, which is exactly the case semantic search is
/// meant to catch. [`search`] uses this internally too.
///
/// This is a HARD filter — scenarios outside the detected namespace are
/// excluded entirely, with no way for a later scoring stage to reconsider
/// them. That's appropriate for [`search`] (pure lexical, no semantic
/// signal to safely relax the filter), but NOT for a hybrid lexical+semantic
/// daemon: it would permanently hide any scenario whose namespace doesn't
/// match a detected keyword — including user-added scenarios filed under a
/// generic namespace (e.g. `everycli add`). For that case, use
/// [`candidates_for_platform`] plus [`explicit_namespace`] as a soft scoring
/// bonus instead of a hard filter.
pub fn filter_candidates<'a>(
    corpus: &'a [Scenario],
    query: &str,
    platform: Platform,
) -> Vec<&'a Scenario> {
    let namespace = explicit_namespace(query);
    corpus
        .iter()
        .filter(|scenario| {
            namespace
                .as_deref()
                .is_none_or(|scope| scenario.namespace == scope)
        })
        .filter(|scenario| !scenario.commands.for_platform(platform).is_empty())
        .collect()
}

/// Same as [`filter_candidates`] but WITHOUT namespace routing — only
/// platform command availability. Meant for callers (like `everycli-daemon`)
/// that want to score the full corpus and use [`explicit_namespace`] as a
/// soft bonus rather than a hard exclusion, so scenarios in unexpected or
/// user-defined namespaces (e.g. `everycli add`) stay reachable.
pub fn candidates_for_platform<'a>(corpus: &'a [Scenario], platform: Platform) -> Vec<&'a Scenario> {
    corpus
        .iter()
        .filter(|scenario| !scenario.commands.for_platform(platform).is_empty())
        .collect()
}

/// Lexical score for a single scenario against `query` (0.0 when there is no
/// overlap at all). Exposed alongside [`filter_candidates`] for the same
/// reason — a semantic reranking layer needs the raw lexical component to
/// build a hybrid score, not just the truncated top-k from [`search`].
pub fn score(scenario: &Scenario, query: &str) -> f32 {
    lexical_score(scenario, &tokens(query), query)
}

/// Retrieve the most relevant commands using a deterministic lexical score.
/// A namespace explicitly mentioned in the query is a hard route, matching the
/// Python engine's protection against cross-ecosystem confusion.
pub fn search(
    corpus: &[Scenario],
    query: &str,
    top_k: usize,
    platform: Platform,
) -> Vec<SearchHit> {
    let query_tokens = tokens(query);
    if query_tokens.is_empty() || top_k == 0 {
        return Vec::new();
    }

    let mut hits = filter_candidates(corpus, query, platform)
        .into_iter()
        .filter_map(|scenario| {
            let score = lexical_score(scenario, &query_tokens, query);
            (score > 0.0).then(|| SearchHit {
                scenario: scenario.clone(),
                command: scenario.commands.for_platform(platform).to_owned(),
                score,
            })
        })
        .collect::<Vec<_>>();

    hits.sort_by(|left, right| {
        right
            .score
            .partial_cmp(&left.score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| left.scenario.id.cmp(&right.scenario.id))
    });
    hits.truncate(top_k);
    hits
}

fn lexical_score(scenario: &Scenario, query_tokens: &HashSet<String>, query: &str) -> f32 {
    let description = tokens(&scenario.description);
    let tags = scenario
        .tags
        .iter()
        .flat_map(|tag| tokens(tag))
        .collect::<HashSet<_>>();
    let id = tokens(&scenario.id);
    let command = tokens(&scenario.commands.linux);
    let namespace = tokens(&scenario.namespace);
    let mut raw_score = 0.0;

    for token in query_tokens {
        if namespace.contains(token) {
            raw_score += 0.0;
        }
        if tags.contains(token) {
            raw_score += 2.0;
        }
        if description.contains(token) {
            raw_score += 2.0;
        }
        if id.contains(token) {
            raw_score += 6.0;
        }
        if command.contains(token) {
            raw_score += 6.0;
        }
    }

    let normalized_query = scope_text(query);
    if normalized_query.len() > 3 && scope_text(&scenario.description).contains(&normalized_query) {
        raw_score += 8.0;
    }
    raw_score / (raw_score + query_tokens.len() as f32 * 10.0)
}

/// Detect an explicit ecosystem keyword in `query` (e.g. "docker", "git",
/// "npm") as a hard-route hint. Exposed as a public, standalone signal —
/// callers decide whether to use it as a hard filter ([`filter_candidates`])
/// or a soft scoring bonus (recommended for any hybrid lexical+semantic
/// search, see `everycli-daemon`).
pub fn explicit_namespace(query: &str) -> Option<String> {
    // Volontairement : seuls les alias fixes explicites font office de route
    // stricte. Un fallback par tags (retiré ici) filtrait des candidats
    // AVANT le scoring hybride, empêchant le reranking sémantique de voir
    // des scénarios pertinents pour des paraphrases sans mot-clé explicite
    // (ex: "annuler mon dernier commit" sans le mot "git") — exactement le
    // cas d'usage que le sémantique est censé couvrir. Le laisser au
    // sémantique plutôt qu'à une heuristique de sous-chaîne bruitée.
    const ALIASES: &[(&str, &[&str])] = &[
        ("composer", &["composer", "php"]),
        ("docker_compose", &["docker compose", "docker-compose", "compose"]),
        ("docker", &["docker", "container", "containers", "image", "images"]),
        ("python", &["python", "pip", "pytest", "virtualenv", "venv", "powershell", "py"]),
        ("npm", &["npm", "nodejs", "node", "package.json"]),
        ("ssh", &["ssh", "scp", "sftp", "remote", "forward"]),
        ("git", &["git"]),
        ("bash_command", &["bash", "shell script", "shell"]),
        ("linux", &["linux", "systemctl", "systemd"]),
    ];

    let normalized = scope_text(query);
    ALIASES
        .iter()
        .find(|(_, aliases)| {
            aliases
                .iter()
                .any(|alias| normalized.contains(&scope_text(alias)))
        })
        .map(|(namespace, _)| (*namespace).to_owned())
}




fn scope_text(value: &str) -> String {
    value
        .chars()
        .map(|character| {
            if character == '-' || character == '_' {
                ' '
            } else {
                character
            }
        })
        .collect::<String>()
        .to_lowercase()
}

fn tokens(value: &str) -> HashSet<String> {
    value
        .split(|character: char| !character.is_alphanumeric())
        .filter(|token| !token.is_empty())
        .map(|token| token.to_lowercase())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn corpus() -> Vec<Scenario> {
        let data_dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../everycli/data/commands");
        load_corpus(data_dir).expect("the checked-in corpus must load")
    }

    #[test]
    fn loads_the_real_corpus() {
        let corpus = corpus();
        assert!(corpus.len() >= 400, "expected the full command corpus");
        assert!(
            corpus
                .iter()
                .any(|scenario| scenario.id == "docker_build_image")
        );
        assert!(
            corpus
                .iter()
                .any(|scenario| scenario.id == "docker_compose_start")
        );
    }

    #[test]
    fn routes_explicit_docker_queries_to_the_docker_namespace() {
        let results = search(&corpus(), "docker build an image", 1, Platform::Linux);
        assert_eq!(results[0].scenario.namespace, "docker");
        assert_eq!(results[0].scenario.id, "docker_build_image");
    }

    #[test]
    fn routes_compose_before_docker() {
        let results = search(
            &corpus(),
            "docker compose start services",
            1,
            Platform::Linux,
        );
        assert_eq!(results[0].scenario.namespace, "docker_compose");
        assert_eq!(results[0].scenario.id, "docker_compose_start");
    }

    #[test]
    fn resolves_the_platform_specific_command() {
        let results = search(&corpus(), "pip install package", 1, Platform::Windows);
        assert_eq!(results[0].scenario.namespace, "python");
        assert!(!results[0].command.is_empty());
    }

    #[test]
    fn parses_error_hints_from_the_real_corpus() {
        let scenario = corpus()
            .into_iter()
            .find(|scenario| scenario.id == "git_replace_in_commits")
            .expect("fixture scenario must exist in the checked-in corpus");
        assert_eq!(
            scenario.error_hints,
            vec![ErrorHint {
                trigger: "fatal: bad revision".to_owned(),
                cause: "Tu n'es pas dans un dépôt Git".to_owned(),
                fix: "Vérifie avec : git status".to_owned(),
            }]
        );
    }

    #[test]
    fn find_error_hint_matches_case_insensitively() {
        let scenario = corpus()
            .into_iter()
            .find(|scenario| scenario.id == "git_replace_in_commits")
            .unwrap();
        let hint = find_error_hint(&scenario, "ERROR: Fatal: Bad Revision 'HEAD'")
            .expect("trigger should match case-insensitively");
        assert_eq!(hint.fix, "Vérifie avec : git status");
    }

    #[test]
    fn find_error_hint_returns_none_when_nothing_matches() {
        let scenario = corpus()
            .into_iter()
            .find(|scenario| scenario.id == "git_replace_in_commits")
            .unwrap();
        assert!(find_error_hint(&scenario, "permission denied").is_none());
    }
}
