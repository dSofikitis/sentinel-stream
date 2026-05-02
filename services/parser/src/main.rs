//! Reads `events.raw` JSON lines from stdin, enriches each one, and
//! writes `events.enriched` JSON lines to stdout. The Kafka-backed
//! consumer/producer wrap this same `enrich::enrich` function in a
//! follow-up commit.

use std::io::{self, BufRead, Write};

use sentinel_parser::enrich::enrich;
use sentinel_parser::event::RawEvent;

fn main() -> io::Result<()> {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut stdout = stdout.lock();

    let mut total = 0u64;
    let mut errors = 0u64;

    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        match serde_json::from_str::<RawEvent>(&line) {
            Ok(raw) => match enrich(&raw) {
                Ok(out) => {
                    let bytes = serde_json::to_vec(&out)
                        .expect("serializing EnrichedEvent should not fail");
                    stdout.write_all(&bytes)?;
                    stdout.write_all(b"\n")?;
                    total += 1;
                }
                Err(e) => {
                    eprintln!("enrich error: {e} (event_id={})", raw.event_id);
                    errors += 1;
                }
            },
            Err(e) => {
                eprintln!("decode error: {e}");
                errors += 1;
            }
        }
    }

    eprintln!("sentinel-parser done: enriched={total}, errors={errors}");
    Ok(())
}
