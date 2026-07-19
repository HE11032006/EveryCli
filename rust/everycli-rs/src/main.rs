use everycli_core::{Platform, load_corpus, search};
use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

fn main() -> ExitCode {
    match run(env::args().skip(1).collect()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("everycli-rs: {message}");
            ExitCode::from(2)
        }
    }
}

fn run(mut arguments: Vec<String>) -> Result<(), String> {
    if arguments.is_empty() || arguments[0] == "--help" || arguments[0] == "-h" {
        print_help();
        return Ok(());
    }
    if arguments.remove(0) != "search" {
        return Err("expected the `search` command; run `everycli-rs --help`".to_owned());
    }

    let mut query = Vec::new();
    let mut data_dir = None;
    let mut top_k = 1usize;
    let mut platform = default_platform();
    let mut json = false;
    let mut index = 0;

    while index < arguments.len() {
        match arguments[index].as_str() {
            "--data" => {
                index += 1;
                data_dir = Some(PathBuf::from(required_value(&arguments, index, "--data")?));
            }
            "--top" | "-t" => {
                index += 1;
                top_k = required_value(&arguments, index, "--top")?
                    .parse()
                    .map_err(|_| "--top must be a positive integer".to_owned())?;
                if top_k == 0 {
                    return Err("--top must be at least 1".to_owned());
                }
            }
            "--platform" => {
                index += 1;
                platform = Platform::parse(required_value(&arguments, index, "--platform")?)
                    .ok_or_else(|| "--platform must be linux, windows, or macos".to_owned())?;
            }
            "--json" => json = true,
            "--help" | "-h" => {
                print_help();
                return Ok(());
            }
            value if value.starts_with('-') => return Err(format!("unknown option: {value}")),
            value => query.push(value.to_owned()),
        }
        index += 1;
    }

    if query.is_empty() {
        return Err("provide a natural-language query".to_owned());
    }
    let query = query.join(" ");
    let corpus = load_corpus(data_dir.unwrap_or_else(default_data_dir))
        .map_err(|error| error.to_string())?;
    let results = search(&corpus, &query, top_k, platform);
    if results.is_empty() {
        return Err("no command matched this query".to_owned());
    }

    if json {
        print_json(&results);
    } else {
        for (index, result) in results.iter().enumerate() {
            if index > 0 {
                println!();
            }
            println!("{} | {}", result.scenario.namespace, result.scenario.id);
            println!("> {}", result.command);
            println!("  {}", result.scenario.explanation);
            println!("  score {:.2}", result.score);
        }
    }
    Ok(())
}

fn required_value<'a>(
    arguments: &'a [String],
    index: usize,
    option: &str,
) -> Result<&'a str, String> {
    arguments
        .get(index)
        .map(String::as_str)
        .ok_or_else(|| format!("{option} requires a value"))
}

fn default_platform() -> Platform {
    if cfg!(target_os = "windows") {
        Platform::Windows
    } else if cfg!(target_os = "macos") {
        Platform::Macos
    } else {
        Platform::Linux
    }
}

fn default_data_dir() -> PathBuf {
    if let Ok(path) = env::var("EVERYCLI_DATA_DIR") {
        return PathBuf::from(path);
    }
    let cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let local = cwd.join("everycli").join("data").join("commands");
    if local.exists() {
        return local;
    }
    cwd.join("..")
        .join("everycli")
        .join("data")
        .join("commands")
}

fn print_help() {
    println!("EveryCli Rust fast path");
    println!(
        "Usage: everycli-rs search <query> [--top N] [--platform linux|windows|macos] [--data DIR] [--json]"
    );
}

fn print_json(results: &[everycli_core::SearchHit]) {
    print!("[");
    for (index, result) in results.iter().enumerate() {
        if index > 0 {
            print!(",");
        }
        print!(
            "{{\"id\":\"{}\",\"namespace\":\"{}\",\"command\":\"{}\",\"explanation\":\"{}\",\"score\":{:.4}}}",
            json_escape(&result.scenario.id),
            json_escape(&result.scenario.namespace),
            json_escape(&result.command),
            json_escape(&result.scenario.explanation),
            result.score,
        );
    }
    println!("]");
}

fn json_escape(value: &str) -> String {
    value
        .chars()
        .flat_map(|character| match character {
            '"' => "\\\"".chars().collect::<Vec<_>>(),
            '\\' => "\\\\".chars().collect::<Vec<_>>(),
            '\n' => "\\n".chars().collect::<Vec<_>>(),
            '\r' => "\\r".chars().collect::<Vec<_>>(),
            '\t' => "\\t".chars().collect::<Vec<_>>(),
            control if control.is_control() => {
                format!("\\u{:04x}", control as u32).chars().collect()
            }
            regular => vec![regular],
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn escapes_json_control_characters() {
        assert_eq!(json_escape("a\"b\n"), "a\\\"b\\n");
    }
}
