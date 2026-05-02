/// Bumped per release; the real parser implementation lands in phase 5
/// (Redpanda consumer -> enrichment -> Redpanda producer).
pub const VERSION: &str = "0.1.0";

fn main() {
    println!(
        "sentinel-parser {}: scaffolded; implementation lands in phase 5.",
        VERSION
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_is_set() {
        assert_eq!(VERSION, "0.1.0");
    }
}
