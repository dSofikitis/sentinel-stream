package main

import "fmt"

// Version is bumped per release; the real ingest implementation lands
// in phase 4 (HTTP + syslog -> Redpanda).
const Version = "0.1.0"

func main() {
	fmt.Printf("sentinel-ingest %s: scaffolded; implementation lands in phase 4.\n", Version)
}
